from enum import Enum


class ModuleState(str, Enum):
    """模块运行状态枚举"""

    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
