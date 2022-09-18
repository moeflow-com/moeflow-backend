import time

from app.exceptions import (
    VCodeExpiredError,
    VCodeNotExistError,
    VCodeWrongError,
)
from app.models.v_code import Captcha, VCode, VCodeContentType, VCodeType
from tests import MoeTestCase


class VCodeTestCase(MoeTestCase):
    def test_captcha(self):
        """人机验证码模型"""
        # == 自定义长度 ==
        c1 = Captcha.create(content_len=4)
        self.assertEqual(len(c1.content), 4)
        # == 设置失效时间 ==
        c4 = Captcha.create(expires=1)
        time.sleep(1)
        with self.assertRaises(VCodeExpiredError):
            Captcha.verify(c4.info, c4.content)
        # 进行验证
        self.assertTrue(Captcha.verify(c1.info, c1.content))
        # == 验证过人机验证码就被删除了 ==
        with self.assertRaises(VCodeNotExistError):
            Captcha.verify(c1.info, c1.content)
        # == 错误超过5次验证码被删除 ==
        # 验证码错误
        c3 = Captcha.create()
        for i in range(5):
            with self.assertRaises(VCodeWrongError):
                self.assertFalse(Captcha.verify(c3.info, "123"))
        # 错误超过五次,人机验证码被删除
        with self.assertRaises(VCodeNotExistError):
            Captcha.verify(c3.info, c3.content)

    def test_v_code(self):
        """验证码模型"""
        # == 自定义长度 ==
        v1 = VCode.create(VCodeType.CONFIRM_EMAIL, "1", content_len=4)
        self.assertEqual(len(v1.content), 4)
        # == 可以自定义内容类型 ==
        v2 = VCode.create(
            VCodeType.CONFIRM_EMAIL, "2", content_type=VCodeContentType.NUMBER
        )
        self.assertTrue(v2.content.isdigit())  # 全都是数字
        # == 设置失效时间 ==
        v3 = VCode.create(VCodeType.CONFIRM_EMAIL, "3", expires=1)
        time.sleep(1)
        with self.assertRaises(VCodeExpiredError):
            VCode.verify(VCodeType.CONFIRM_EMAIL, v3.info, v3.content)
        # == 设置大小写不敏感 ==
        v4 = VCode.create(VCodeType.CONFIRM_EMAIL, "4", content_len=4)
        self.assertTrue(
            VCode.verify(
                VCodeType.CONFIRM_EMAIL,
                "4",
                v4.content,
                case_sensitive=True,
                delete_after_verified=False,
            )
        )
        self.assertTrue(
            VCode.verify(
                VCodeType.CONFIRM_EMAIL,
                "4",
                v4.content.lower(),
                case_sensitive=False,
                delete_after_verified=False,
            )
            and VCode.verify(
                VCodeType.CONFIRM_EMAIL,
                "4",
                v4.content.upper(),
                case_sensitive=False,
                delete_after_verified=False,
            )
        )
        # == 设置验证后删除 ==
        v5 = VCode.create(VCodeType.CONFIRM_EMAIL, "5", content_len=4)
        # 验证两次未删除
        self.assertTrue(
            VCode.verify(
                VCodeType.CONFIRM_EMAIL, "5", v5.content, delete_after_verified=False,
            )
        )
        self.assertTrue(
            VCode.verify(
                VCodeType.CONFIRM_EMAIL, "5", v5.content, delete_after_verified=False,
            )
        )
        # 设置删除
        self.assertTrue(VCode.verify(VCodeType.CONFIRM_EMAIL, "5", v5.content))
        with self.assertRaises(VCodeNotExistError):
            self.assertTrue(VCode.verify(VCodeType.CONFIRM_EMAIL, "5", v5.content))
        # == 错误超过5次验证码被删除 ==
        v6 = VCode.create(VCodeType.CONFIRM_EMAIL, "6", content_len=4)
        for i in range(5):
            with self.assertRaises(VCodeWrongError):
                VCode.verify(VCodeType.CONFIRM_EMAIL, "6", "123")
        with self.assertRaises(VCodeNotExistError):
            VCode.verify(VCodeType.CONFIRM_EMAIL, "6", v6.content)
        # == 对于相同的info会更新验证码 ==
        v7 = VCode.create(VCodeType.CONFIRM_EMAIL, "7")
        v7_1 = VCode.create(VCodeType.CONFIRM_EMAIL, "7")
        self.assertEqual(v7.id, v7_1.id)
        self.assertEqual(v7.info, v7_1.info)
        self.assertNotEqual(v7.content, v7_1.content)
        # == 验证码类别不同不能验证成功 ==
        v8 = VCode.create(VCodeType.CONFIRM_EMAIL, "8")
        with self.assertRaises(VCodeNotExistError):
            VCode.verify(VCodeType.RESET_EMAIL, "8", v8.content)
        # == 验证码验证信息不同不能验证成功
        v9 = VCode.create(VCodeType.CONFIRM_EMAIL, "9")
        with self.assertRaises(VCodeNotExistError):
            VCode.verify(VCodeType.RESET_EMAIL, "99", v9.content)
