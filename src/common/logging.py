import logging


def setup_logging(level: int = logging.INFO) -> None:
    """初始化日志配置"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
