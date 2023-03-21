import time

from app.exceptions import NeedTokenError, VCodeCoolingError
from app.models.v_code import VCode, VCodeType
from flask_apikit.exceptions import ValidateError
from tests import MoeAPITestCase


class VCodeTestCase(MoeAPITestCase):
    def test_captcha_api(self):
        """人机验证码API"""
        # 每次申请的验证码都不同
        captcha_info1, captcha1 = self.get_captcha()
        captcha_info2, captcha2 = self.get_captcha()
        self.assertNotEqual(captcha_info1, captcha_info2)
        self.assertNotEqual(captcha1, captcha2)

    def test_confirm_email_api(self):
        """确认邮件API"""
        # 创建用户
        self.create_user("11", "222@1.com", "111111").generate_token()
        # 已注册的邮箱无法获取
        data = self.post("/v1/confirm-email-codes", json={"email": "222@1.com"})
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("email"))
        # 获取验证码
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "1@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content = VCode.objects(type=VCodeType.CONFIRM_EMAIL, info="1@1.com").first()[
            "content"
        ]
        # 再次申请则冷却中
        captcha_info, captcha = self.get_captcha()
        data2 = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "1@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data2, VCodeCoolingError)
        content2 = VCode.objects(type=VCodeType.CONFIRM_EMAIL, info="1@1.com").first()[
            "content"
        ]
        # 前后申请的验证码未变化
        self.assertEqual(content, content2)
        # 其他邮箱不受冷却限制
        captcha_info, captcha = self.get_captcha()
        data3 = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "2@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data3)
        # 等待wait时间
        time.sleep(data.json["wait"] + 0.1)
        # 冷却后又可以使用
        captcha_info, captcha = self.get_captcha()
        data4 = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "1@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data4)
        content4 = VCode.objects(type=VCodeType.CONFIRM_EMAIL, info="1@1.com").first()[
            "content"
        ]
        # 前后申请的验证码已变化
        self.assertNotEqual(content, content4)

    def test_reset_email_api(self):
        """重置邮件API"""
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        token2 = self.create_user("22", "2@1.com", "111111").generate_token()
        # 未登录，无法使用
        data = self.post("/v1/reset-email-codes")
        self.assertErrorEqual(data, NeedTokenError)
        # 需要登录
        data = self.post("/v1/reset-email-codes", token=token)
        self.assertErrorEqual(data)
        content = VCode.objects(type=VCodeType.RESET_EMAIL, info="1@1.com").first()[
            "content"
        ]
        # 再次申请则冷却中
        data2 = self.post("/v1/reset-email-codes", token=token)
        self.assertErrorEqual(data2, VCodeCoolingError)
        content2 = VCode.objects(type=VCodeType.RESET_EMAIL, info="1@1.com").first()[
            "content"
        ]
        # 前后申请的验证码未变化
        self.assertEqual(content, content2)
        # 其他用户不受冷却限制
        data3 = self.post("/v1/reset-email-codes", token=token2)
        self.assertErrorEqual(data3)
        # 等待wait时间
        time.sleep(data.json["wait"] + 0.1)
        # 冷却后又可以使用
        data4 = self.post("/v1/reset-email-codes", token=token)
        self.assertErrorEqual(data4)
        content4 = VCode.objects(type=VCodeType.RESET_EMAIL, info="1@1.com").first()[
            "content"
        ]
        # 前后申请的验证码已变化
        self.assertNotEqual(content, content4)

    def test_reset_password_api(self):
        """重置密码邮件API"""
        # 创建用户
        self.create_user("11", "1@1.com", "111111").generate_token()
        self.create_user("22", "2@1.com", "111111").generate_token()
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 申请重置密码邮件
        data = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "1@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content = VCode.objects(type=VCodeType.RESET_PASSWORD, info="1@1.com").first()[
            "content"
        ]
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 再次申请则冷却中
        data2 = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "1@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data2, VCodeCoolingError)
        content2 = VCode.objects(type=VCodeType.RESET_PASSWORD, info="1@1.com").first()[
            "content"
        ]
        # 前后申请的验证码未变化
        self.assertEqual(content, content2)
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 其他邮箱不受冷却限制
        data3 = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "2@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data3)
        # 等待wait时间
        time.sleep(data.json["wait"] + 0.1)
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 冷却后又可以使用
        data4 = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "1@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data4)
        content4 = VCode.objects(type=VCodeType.RESET_PASSWORD, info="1@1.com").first()[
            "content"
        ]
        # 前后申请的验证码已变化
        self.assertNotEqual(content, content4)
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 未注册的邮箱无法申请
        data5 = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "3@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data5, ValidateError)
        self.assertIn("email", data5.json["message"])
