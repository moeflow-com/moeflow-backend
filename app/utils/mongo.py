from typing import TypeVar, List

T = TypeVar("T")


def mongo_order(
    objects: List[T],
    order_by: None | list[str] | str,
    default_order_by: str | list[str],
) -> List[T]:
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


def mongo_slice(objects: List[T], skip, limit) -> List[T]:
    """切片处理"""
    if skip:
        objects = objects.skip(skip)
    if limit:
        objects = objects.limit(limit)
    return objects
