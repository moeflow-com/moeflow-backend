"""正则表达式"""

USER_NAME_REGEX = r"^[\u2E80-\u2FDF\u3040-\u318F\u31A0-\u31BF\u31F0-\u31FF\u3400-\u4DB5\u4E00-\u9FFF\uA960-\uA97F\uAC00-\uD7FFa-zA-Z0-9_]+$"  # noqa: E501
TEAM_NAME_REGEX = r"^[\u2E80-\u2FDF\u3040-\u318F\u31A0-\u31BF\u31F0-\u31FF\u3400-\u4DB5\u4E00-\u9FFF\uA960-\uA97F\uAC00-\uD7FFa-zA-Z0-9_]+$"  # noqa: E501
EMAIL_REGEX = r"^[^@ ]+@[^.@ ]+(\.[^.@ ]+)*(\.[^.@ ]{2,})$"
