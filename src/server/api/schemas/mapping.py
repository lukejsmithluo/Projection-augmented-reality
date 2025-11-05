from pydantic import BaseModel


class MappingStartRequest(BaseModel):
    """开始映射请求参数"""

    build_mesh: bool = True
    save_texture: bool = True


class MappingStopResponse(BaseModel):
    """停止映射响应"""

    saved_files: list[str] = []
