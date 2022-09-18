from typing import Dict, List, Union


class Type:
    """用于定义类型，并向api返回介绍"""

    @classmethod
    def get_detail_by_value(
        cls, value: Union[int, str], detail_name: str, default_value: str = ""
    ) -> str:
        """
        获取某个值的详细信息

        :param attr: 类型名称
        :param detail_name: 详细内容名称
        :param default_value: 默认值
        """
        for attr in dir(cls):
            if attr.isupper() and getattr(cls, attr) == value:
                return cls.get_detail(attr, detail_name, default_value=default_value)
        return default_value

    @classmethod
    def get_detail(cls, attr: str, detail_name: str, default_value: str = "") -> str:
        """
        获取某个值的详细信息

        :param attr: 类型名称
        :param detail_name: 详细内容名称
        :param default_value: 默认值
        """
        detail = cls.details.get(attr)
        if detail is None:
            return default_value
        if detail_name not in detail:
            return default_value
        return detail[detail_name]

    @classmethod
    def to_api(
        cls, ids: Union[List[int], List[str]] = None, id: Union[int, str] = None
    ) -> Union[List[Dict], Dict]:
        """转化为前端使用数组，并加上介绍"""
        # 如果指定了id，则返回相应id的类型
        if id:
            for attr in dir(cls):
                if attr.isupper() and getattr(cls, attr) == id:
                    return {
                        "id": getattr(cls, attr),
                        # 没有名称则设置为属性名
                        "name": cls.get_detail(attr, "name", default_value=attr),
                        "intro": cls.get_detail(attr, "intro", default_value=""),
                    }
            raise ValueError(f"{id} 不存在于类 {cls.__name__}")
        else:
            # 需要获取的ids
            if ids is None:
                ids = cls.ids()
            # 获取排序后的列表
            data = sorted(
                [
                    {
                        "id": getattr(cls, attr),
                        # 没有名称则设置为属性名
                        "name": cls.get_detail(attr, "name", default_value=attr),
                        "intro": cls.get_detail(attr, "intro", default_value=""),
                    }
                    for attr in dir(cls)
                    if attr.isupper() and getattr(cls, attr) in ids
                ],
                key=lambda d: d["id"],
            )
            return data

    @classmethod
    def ids(cls):
        """返回所有大写常量的值"""
        ids = [getattr(cls, attr) for attr in dir(cls) if attr.isupper()]
        return ids


class IntType(Type):
    """用于一些整形的类型"""

    @classmethod
    def ids(cls) -> List[int]:
        return super().ids()


class StrType(Type):
    """用于一些字符串的类型"""

    @classmethod
    def ids(cls) -> List[str]:
        return super().ids()
