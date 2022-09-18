from app.exceptions import MoeError, self_vars
from tests import MoeTestCase


class ErrorCodeTestCase(MoeTestCase):
    def test_error_code(self):
        """测试错误码是否重复"""
        error_codes = []
        # 取出所有MoeError的子类
        for k, v in self_vars.items():
            if type(v) == type:
                if issubclass(v, MoeError):
                    error_codes.append(v.code)
        # 找出重复的错误代码
        not_unique_error_codes = []
        for code in error_codes:
            if error_codes.count(code) > 1:
                if code not in not_unique_error_codes:
                    not_unique_error_codes.append(code)
        # 发现重复的错误代码,则抛出警告
        if len(not_unique_error_codes) > 0:
            raise UserWarning(
                "MoeError code not unique: {}".format(not_unique_error_codes)
            )
