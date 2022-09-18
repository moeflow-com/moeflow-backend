def is_number(string: str):
    """判断字符串是否是纯数字"""
    try:
        int(string)
    except Exception:
        return False
    else:
        return True
