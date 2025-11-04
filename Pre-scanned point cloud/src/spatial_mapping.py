########################################################################
#
# Copyright (c) 2022, STEREOLABS.
#
# All rights reserved.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
########################################################################

"""
    This sample shows how to capture a real-time 3D reconstruction      
    of the scene using the Spatial Mapping API. The resulting mesh      
    is displayed as a wireframe on top of the left image using OpenGL.  
    Spatial Mapping can be started and stopped with the Space Bar key
"""

import sys
import time
import os
import argparse
import pyzed.sl as sl
import ogl_viewer.viewer as gl


def main(opt):
    # Init ZED runtime
    init = sl.InitParameters()
    init.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP  # OpenGL coordinate system
    init.depth_maximum_distance = 8.0

    # Depth mode: default to NEURAL for performance; allow NEURAL_PLUS via CLI
    if opt.depth_mode == 'NEURAL_PLUS':
        init.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS
    else:
        init.depth_mode = sl.DEPTH_MODE.NEURAL

    # Units for Unreal integration
    init.coordinate_units = sl.UNIT.CENTIMETER if opt.units == 'CENTIMETER' else sl.UNIT.METER
    parse_args(init, opt)
    print(f"[Sample] Using coordinate units: {opt.units}; depth mode: {opt.depth_mode}")

    # Open camera
    zed = sl.Camera()
    status = zed.open(init)
    if status != sl.ERROR_CODE.SUCCESS:
        print("Camera Open : " + repr(status) + ". Exit program.")
        exit()

    # Enable positional tracking
    positional_tracking_parameters = sl.PositionalTrackingParameters()
    returned_state = zed.enable_positional_tracking(positional_tracking_parameters)
    if returned_state != sl.ERROR_CODE.SUCCESS:
        print("Enable Positional Tracking : " + repr(returned_state) + ". Exit program.")
        zed.close()
        exit()

    # Prepare spatial mapping output type
    if opt.build_mesh:
        pymesh = sl.Mesh()
    else:
        pymesh = sl.FusedPointCloud()

    tracking_state = sl.POSITIONAL_TRACKING_STATE.OFF
    mapping_state = sl.SPATIAL_MAPPING_STATE.NOT_ENABLED

    runtime_parameters = sl.RuntimeParameters()
    runtime_parameters.confidence_threshold = 50

    mapping_activated = False
    image = sl.Mat()
    pose = sl.Pose()

    viewer = gl.GLViewer()
    viewer.init(zed.get_camera_information().camera_configuration.calibration_parameters.left_cam, pymesh, int(opt.build_mesh))
    print("Press 'Space' to enable / disable spatial mapping")
    print("Stop mapping to export an OBJ (and texture if enabled)")

    last_call = time.time()

    while viewer.is_available():
        # Grab an image, a RuntimeParameters object must be given to grab()
        if zed.grab(runtime_parameters) <= sl.ERROR_CODE.SUCCESS:
            # Retrieve left image
            zed.retrieve_image(image, sl.VIEW.LEFT)
            # Update pose data (used for projection of the mesh over the current image)
            tracking_state = zed.get_position(pose)

            if mapping_activated:
                mapping_state = zed.get_spatial_mapping_state()
                # Compute elapsed time since the last call of request_spatial_map_async()
                duration = time.time() - last_call
                # Ask for a mesh update if elapsed time passed and viewer has chunk changes
                if duration > (opt.update_rate_ms / 1000.0) and viewer.chunks_updated():
                    zed.request_spatial_map_async()
                    last_call = time.time()

                if zed.get_spatial_map_request_status_async() == sl.ERROR_CODE.SUCCESS:
                    zed.retrieve_spatial_map_async(pymesh)
                    viewer.update_chunks()

            change_state = viewer.update_view(image, pose.pose_data(), tracking_state, mapping_state)

            if change_state:
                if not mapping_activated:
                    # Start spatial mapping
                    # Ensure positional tracking is enabled
                    if tracking_state == sl.POSITIONAL_TRACKING_STATE.OFF:
                        err_pt = zed.enable_positional_tracking(positional_tracking_parameters)
                        if err_pt != sl.ERROR_CODE.SUCCESS:
                            print(f"Failed to enable positional tracking: {err_pt}")
                            continue

                    # Reset tracking pose to initial transform
                    init_pose = sl.Transform()
                    zed.reset_positional_tracking(init_pose)

                    # Pre-heat: wait up to 3s for tracking to become OK (align with sample expectations)
                    preheat_deadline = time.time() + 3.0
                    while time.time() < preheat_deadline:
                        tracking_state = zed.get_position(pose)
                        if tracking_state == sl.POSITIONAL_TRACKING_STATE.OK:
                            break
                        time.sleep(0.05)
                    if tracking_state != sl.POSITIONAL_TRACKING_STATE.OK:
                        print("Cannot use Spatial mapping: Positional tracking not OK. Skipping enable.")
                        continue

                    # Configure mapping parameters (performance-oriented defaults)
                    spatial_mapping_parameters = make_spatial_mapping_parameters(opt, opt.build_mesh)

                    # Enable spatial mapping
                    err = zed.enable_spatial_mapping(spatial_mapping_parameters)
                    if err != sl.ERROR_CODE.SUCCESS:
                        print(f"Failed to enable spatial mapping: {err}. Tracking state: {tracking_state}")
                        continue

                    # Clear previous mesh data
                    pymesh.clear()
                    viewer.clear_current_mesh()

                    # Start timer
                    last_call = time.time()
                    mapping_activated = True
                    print("Spatial mapping started. Move the camera to scan, then press SPACE to stop and save.")
                else:
                    # Stop spatial mapping and extract mesh
                    print("Stopping spatial mapping and extracting spatial map...")
                    err = zed.extract_whole_spatial_map(pymesh)
                    zed.disable_spatial_mapping()
                    mapping_activated = False

                    if err != sl.ERROR_CODE.SUCCESS:
                        print(f"Failed to extract spatial map: {err}")
                    else:
                        print("Spatial map extracted successfully")

                        # Optional mesh filtering
                        if opt.build_mesh and opt.mesh_filter != 'NONE':
                            filter_params = sl.MeshFilterParameters()
                            if opt.mesh_filter == 'LOW':
                                filter_params.set(sl.MESH_FILTER.LOW)
                            elif opt.mesh_filter == 'MEDIUM':
                                filter_params.set(sl.MESH_FILTER.MEDIUM)
                            elif opt.mesh_filter == 'HIGH':
                                filter_params.set(sl.MESH_FILTER.HIGH)
                            res = pymesh.filter(filter_params, True)
                            # Accept both SDK enum success and boolean True
                            if (isinstance(res, bool) and not res) or (not isinstance(res, bool) and res != sl.ERROR_CODE.SUCCESS):
                                print(f"Mesh filtering failed: {res}")

                        # Apply texture if it was captured during mapping
                        if opt.build_mesh and opt.save_texture:
                            tex_res = pymesh.apply_texture(sl.MESH_TEXTURE_FORMAT.RGBA)
                            if tex_res != sl.ERROR_CODE.SUCCESS:
                                print(f"Texture application failed: {tex_res}")

                        # Save mesh/point cloud to data folder
                        save_spatial_output(pymesh, opt)

                    print("Spatial mapping stopped. Press SPACE to start a new session.")

    # Cleanup
    image.free(memory_type=sl.MEM.CPU)
    pymesh.clear()
    zed.disable_spatial_mapping()
    zed.disable_positional_tracking()
    zed.close()


def make_spatial_mapping_parameters(opt, build_mesh):
    """Build SpatialMappingParameters from CLI options, tuned for performance."""
    # Map CLI to enum
    res_map = {
        'LOW': sl.MAPPING_RESOLUTION.LOW,
        'MEDIUM': sl.MAPPING_RESOLUTION.MEDIUM,
        'HIGH': sl.MAPPING_RESOLUTION.HIGH,
    }
    res_choice = res_map.get(opt.mapping_resolution, sl.MAPPING_RESOLUTION.MEDIUM)

    map_type = sl.SPATIAL_MAP_TYPE.MESH if build_mesh else sl.SPATIAL_MAP_TYPE.FUSED_POINT_CLOUD
    params = sl.SpatialMappingParameters(
        resolution=res_choice,
        mapping_range=sl.MAPPING_RANGE.MEDIUM,
        max_memory_usage=int(opt.max_memory_mb),
        save_texture=bool(opt.save_texture) if build_mesh else False,
        use_chunk_only=True,
        reverse_vertex_order=False,
        map_type=map_type,
    )
    return params


def save_spatial_output(pymesh, opt):
    """Save mesh or point cloud to the project data folder."""
    import datetime

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mesh_{timestamp}.obj" if opt.build_mesh else f"pointcloud_{timestamp}.obj"
    filepath = os.path.join(data_dir, filename)

    print(f"Saving to: {filepath}")
    status = pymesh.save(filepath)

    if status:
        print(f"Successfully saved: {filepath}")
        # Log material/texture presence if applicable
        mtl_file = filepath.replace('.obj', '.mtl')
        png_file = filepath.replace('.obj', '.png')
        if os.path.exists(mtl_file):
            print(f"Material file: {mtl_file}")
        if os.path.exists(png_file):
            print(f"Texture file: {png_file}")
        return True
    else:
        print(f"Failed to save the spatial output to: {filepath}")
        return False


def parse_args(init, opt):
    # Input sources
    if len(opt.input_svo_file) > 0 and opt.input_svo_file.endswith((".svo", ".svo2")):
        init.set_from_svo_file(opt.input_svo_file)
        print("[Sample] Using SVO File input:", opt.input_svo_file)
    elif len(opt.ip_address) > 0:
        ip_str = opt.ip_address
        if ip_str.replace(':', '').replace('.', '').isdigit() and len(ip_str.split('.')) == 4 and len(ip_str.split(':')) == 2:
            init.set_from_stream(ip_str.split(':')[0], int(ip_str.split(':')[1]))
            print("[Sample] Using Stream input, IP:", ip_str)
        elif ip_str.replace(':', '').replace('.', '').isdigit() and len(ip_str.split('.')) == 4:
            init.set_from_stream(ip_str)
            print("[Sample] Using Stream input, IP:", ip_str)
        else:
            print("Invalid IP format. Using live stream")

    # Camera resolution
    if ("HD2K" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.HD2K
        print("[Sample] Using Camera resolution HD2K")
    elif ("HD1200" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.HD1200
        print("[Sample] Using Camera resolution HD1200")
    elif ("HD1080" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.HD1080
        print("[Sample] Using Camera resolution HD1080")
    elif ("HD720" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.HD720
        print("[Sample] Using Camera resolution HD720")
    elif ("SVGA" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.SVGA
        print("[Sample] Using Camera resolution SVGA")
    elif ("VGA" in opt.resolution):
        init.camera_resolution = sl.RESOLUTION.VGA
        print("[Sample] Using Camera resolution VGA")
    elif len(opt.resolution) > 0:
        print("[Sample] No valid resolution entered. Using default")
    else:
        print("[Sample] Using default resolution")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_svo_file', type=str, default='', help='Path to an .svo/.svo2 file for replay')
    parser.add_argument('--ip_address', type=str, default='', help='IP in a.b.c.d:port or a.b.c.d for streaming setup')
    parser.add_argument('--resolution', type=str, default='', help='Camera resolution: HD2K, HD1200, HD1080, HD720, SVGA or VGA')
    parser.add_argument('--build_mesh', action='store_true', help='Build and display mesh instead of fused point cloud')
    parser.add_argument('--mesh_filter', type=str, choices=['NONE', 'LOW', 'MEDIUM', 'HIGH'], default='MEDIUM', help='Mesh filtering level when stopping mapping')
    parser.add_argument('--units', type=str, choices=['METER', 'CENTIMETER'], default='CENTIMETER', help='Coordinate units for exported geometry (Unreal uses CENTIMETER)')
    parser.add_argument('--save_texture', action='store_true', help='Save and export texture/material when building mesh (enable by passing this flag)')
    parser.add_argument('--mapping_resolution', type=str, choices=['LOW', 'MEDIUM', 'HIGH'], default='MEDIUM', help='Spatial mapping resolution preset')
    parser.add_argument('--max_memory_mb', type=int, default=2048, help='Max memory for spatial mapping (in MB)')
    parser.add_argument('--update_rate_ms', type=int, default=700, help='Async update interval for spatial map requests (ms)')
    parser.add_argument('--depth_mode', type=str, choices=['NEURAL', 'NEURAL_PLUS'], default='NEURAL_PLUS', help='Depth mode (default NEURAL_PLUS per user preference)')
    opt = parser.parse_args()

    if len(opt.input_svo_file) > 0 and len(opt.ip_address) > 0:
        print("Specify only input_svo_file or ip_address, not both. Exit program")
        exit()

    main(opt)