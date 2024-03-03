# ruff: noqa: F403
"""
所有API异常定义在此
"""
from .base import *  # 100-999
from .auth import *  # 1xxx
from .v_code import *  # 2xxx
from .team import *  # 3xxx
from .project import *  # 4xxx
from .join_process import *  # 5xxx
from .language import *  # 6xxx
from .term import *  # 7xxx
from .file import *  # 8xxx
from .output import *  # 9xxx

self_vars = vars()
