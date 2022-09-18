from flask_babel import lazy_gettext

from app.constants.base import StrType


class Locale(StrType):
    """站点可选语言"""

    AUTO = "auto"
    ZH_CN = "zh_CN"
    ZH_TW = "zh_TW"
    EN = "en"

    details = {
        "AUTO": {"name": lazy_gettext("自动"), "intro": lazy_gettext("遵循浏览器设置")},
        "ZH_CN": {"name": lazy_gettext("中文（简体）")},
        "ZH_TW": {"name": lazy_gettext("中文（繁体）")},
        "EN": {"name": lazy_gettext("英文")},
    }
