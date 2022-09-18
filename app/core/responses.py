from flask_apikit.responses import Pagination


class MoePagination(Pagination):
    def set_objects(
        self, objects, /, *, func: str = "to_api", func_kwargs: dict = None
    ) -> "MoePagination":
        """传入 MongoEngine 的 Query，使用 func 同名方法自动解析数据，获取总个数后 set_data 到分页对象"""
        if func_kwargs is None:
            func_kwargs = {}
        data = [getattr(o, func)(**func_kwargs) for o in objects]
        return self.set_data(data=data, count=objects.count())
