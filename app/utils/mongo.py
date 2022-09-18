def mongo_order(objects, order_by, default_order_by):
    """处理排序"""
    # 设置排序默认值
    if order_by is None or order_by == []:
        order_by = default_order_by
    # 如果是字符串的话，则转为数组
    if isinstance(order_by, str):
        order_by = [order_by]
    # 排序
    if order_by:
        objects = objects.order_by(*order_by)
    return objects


def mongo_slice(objects, skip, limit):
    """切片处理"""
    if skip:
        objects = objects.skip(skip)
    if limit:
        objects = objects.limit(limit)
    return objects
