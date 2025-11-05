from pydantic import BaseModel


class CalibrationRunRequest(BaseModel):
    """运行标定请求参数"""

    proj_height: int
    proj_width: int
    rounds: int = 1
