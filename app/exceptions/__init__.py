"""
所有API异常定义在此
"""

from .base import *  # 100-999 # noqa: F403
from .auth import *  # 1xxx # noqa: F403
from .v_code import *  # 2xxx # noqa: F403
from .team import *  # 3xxx # noqa: F403
from .project import *  # 4xxx # noqa: F403
from .join_process import *  # 5xxx # noqa: F403
from .language import *  # 6xxx # noqa: F403
from .term import *  # 7xxx # noqa: F403
from .file import *  # 8xxx # noqa: F403
from .output import *  # 9xxx # noqa: F403

self_vars = vars()
