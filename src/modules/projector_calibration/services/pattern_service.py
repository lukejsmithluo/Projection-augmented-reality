import os

import cv2
import numpy as np


class PatternService:
    def generate_graycode_patterns(
        self,
        width: int,
        height: int,
        step: int = 1,
        output_dir: str = "./graycode_pattern",
    ) -> list[str]:
        """
        Generate graycode pattern images.
        Returns a list of generated file paths.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        gc_height = int((height - 1) / step) + 1
        gc_width = int((width - 1) / step) + 1

        graycode = cv2.structured_light_GrayCodePattern.create(gc_width, gc_height)
        patterns = graycode.generate()[1]

        # expand image size
        exp_patterns = []
        for pat in patterns:
            img = np.zeros((height, width), np.uint8)
            # Vectorized implementation for better performance
            # Create coordinate grids
            y_coords, x_coords = np.mgrid[0:height, 0:width]
            # Map to smaller graycode pattern coordinates
            y_mapped = (y_coords / step).astype(int)
            x_mapped = (x_coords / step).astype(int)

            # Use advanced indexing to fill the image
            # Note: pat is (gc_height, gc_width)
            # We need to ensure indices are within bounds
            y_mapped = np.clip(y_mapped, 0, gc_height - 1)
            x_mapped = np.clip(x_mapped, 0, gc_width - 1)

            img = pat[y_mapped, x_mapped]
            exp_patterns.append(img)

        # Add white and black patterns
        exp_patterns.append(255 * np.ones((height, width), np.uint8))  # white
        exp_patterns.append(np.zeros((height, width), np.uint8))  # black

        generated_files = []
        for i, pat in enumerate(exp_patterns):
            filename = f"pattern_{str(i).zfill(2)}.png"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, pat)
            generated_files.append(filepath)

        return generated_files
