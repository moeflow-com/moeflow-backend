from app.constants.base import IntType


class SourcePositionType(IntType):
    """原文（标记）位置类型"""

    IN = 1  # 框内标记
    OUT = 2  # 框外标记
