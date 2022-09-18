def default(val, default_val=None, attr_name=None, func=None):
    """
    如果 val 为 None, 则使用 default_val
    :param val: 值
    :param default_val: 默认值，默认为None
    :param attr_name: 如果有则调用相应的方法/属性
    :param func: 使用一个函数对val进行处理
    :return:
    """
    if val is None:
        val = default_val
    else:
        if attr_name:
            if callable(getattr(val, attr_name)):
                val = getattr(val, attr_name)()
            else:
                val = getattr(val, attr_name)
        if func:
            val = func(val)
    return val
