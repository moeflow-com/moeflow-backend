from app import Locale
from app.exceptions import BadTokenError, NeedTokenError, UserBannedError
from app.exceptions.base import NoPermissionError
from app.models.user import User
from app.models.v_code import VCode, VCodeType
from flask_apikit.exceptions import ValidateError
from tests import DEFAULT_USERS_COUNT, MoeAPITestCase


class AuthAPITestCase(MoeAPITestCase):
    def test_register1(self):
        """测试注册API"""
        # 缺少验证码无法注册
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 申请邮件验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "AAA@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        content2 = VCode.objects(
            type=VCodeType.CONFIRM_EMAIL, info="aaa@a.com"
        ).first()["content"]
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 申请错误的邮件验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "2@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        wrong_content2 = VCode.objects(
            type=VCodeType.CONFIRM_EMAIL, info="2@1.com"
        ).first()["content"]
        # == 使用错误的邮件验证码注册 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "AAA@a.com",
                "name": "12134",
                "password": "111111",
                "age": "123",
                "v_code": wrong_content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 错误的邮箱注册 ==
        # 获取验证码内容
        data = self.post(
            "/v1/users",
            json={
                "email": "2@1.com",
                "name": "12134",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 正确的注册 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "AAA@a.com",
                "name": "12134",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 1)
        # == 注册过的邮箱不能再次注册 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "AAA@a.com",
                "name": "12134",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 1)
        # == 注册了的邮箱,不能申请邮箱确认验证码 ==
        # 申请邮件验证码
        data = self.post("/v1/confirm-email-codes", json={"email": "AAA@a.com"})
        self.assertErrorEqual(data, ValidateError)
        # 用户邮箱记录的是小写
        user = User.get_by_email("AAA@a.com")
        self.assertEqual(user.email, "aaa@a.com")

    def test_register2(self):
        """测试注册API，注册邮箱和名称不能以空格开头"""
        # == 邮箱前加空格 ==
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 申请邮件验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "1@1.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        content2 = VCode.objects(type=VCodeType.CONFIRM_EMAIL, info="1@1.com").first()[
            "content"
        ]
        data = self.post(
            "/v1/users",
            json={
                "email": " 1@1.com",
                "name": "12134",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 邮箱后加空格 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "1@1.com ",
                "name": "12134",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 邮箱中间加空格 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "1 1@11.com",
                "name": "12134",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 名称前加空格 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "1@1.com",
                "name": " 12134",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 名称后加空格 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "1@1.com",
                "name": "12134 ",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 名称中间加空格 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "1@1.com",
                "name": "121 34",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 名称加符号 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "1@1.com",
                "name": "121,34",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 符合要求的名称 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "1@1.com",
                "name": "中い다Aa1_",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 1)
        # 用户邮箱记录的是小写
        user = User.get_by_email("AAA@a.com")
        self.assertEqual(user.email, "aaa@a.com")

    def test_register2(self):
        """测试注册API（邮件确认验证码使用大写）"""
        # == 邮箱前加空格 ==
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 申请邮件验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "aaa@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        content2 = VCode.objects(
            type=VCodeType.CONFIRM_EMAIL, info="aaa@a.com"
        ).first()["content"]
        data = self.post(
            "/v1/users",
            json={
                "email": " AAA@a.com",
                "name": "12134",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 符合要求的名称 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "aaa@a.com",
                "name": "中い다Aa1_",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 1)

    def test_register3(self):
        """测试注册API（注册请求使用大写）"""
        # == 邮箱前加空格 ==
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 申请邮件验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "aaa@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        content2 = VCode.objects(
            type=VCodeType.CONFIRM_EMAIL, info="aaa@a.com"
        ).first()["content"]
        data = self.post(
            "/v1/users",
            json={
                "email": " aaa@a.com",
                "name": "12134",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 0)
        # == 符合要求的名称 ==
        data = self.post(
            "/v1/users",
            json={
                "email": "AAA@a.com",
                "name": "中い다Aa1_",
                "password": "111111",
                "age": "123",
                "v_code": content2,
            },
        )
        self.assertErrorEqual(data)
        self.assertEqual(User.objects.count(), DEFAULT_USERS_COUNT + 1)
        # 用户邮箱记录的是小写
        user = User.get_by_email("AAA@a.com")
        self.assertEqual(user.email, "aaa@a.com")

    def test_login(self):
        """测试登录API"""
        # == 正确的注册一个账号 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        # == 用错误的人机验证码登录api ==
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "1@1.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": "bbbkbb",
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("captcha"))  # 会有captcha
        self.assertIsNone(data.json["message"].get("email"))  # 不会有email
        self.assertIsNone(data.json["message"].get("password"))  # 不会有password
        # == 用错误的人机验证码和错误的密码登录api ==
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "1@1.com",
                "password": "1111112222222",
                "captcha_info": captcha_info,
                "captcha": "bbbkbb",
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("captcha"))  # 会有captcha
        self.assertIsNone(data.json["message"].get("email"))  # 不会有email
        self.assertIsNone(data.json["message"].get("password"))  # 不会有password
        # == 用不存在的账号密码登录api ==
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "2@1.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNone(data.json["message"].get("captcha"))  # 不会有captcha
        self.assertIsNotNone(data.json["message"].get("email"))  # 会有email字段
        self.assertIsNone(data.json["message"].get("password"))  # 不会有password
        # == 用错误的密码登录api ==
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "1@1.com",
                "password": "1111112222222",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNone(data.json["message"].get("captcha"))  # 不会有captcha
        self.assertIsNone(data.json["message"].get("email"))  # 不会有email
        self.assertIsNotNone(data.json["message"].get("password"))  # 会有password字段
        # == 用正确的账号密码登录api ==
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "1@1.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))

    def test_token_when_password_changed(self):
        """测试修改密码使"""
        # == 正确的注册一个账号 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        # == 用正确的账号密码登录api ==
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "1@1.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        token = data.json.get("token")
        # 获取个人资料
        data = self.get("/v1/user/info", token=token)
        self.assertErrorEqual(data)
        self.assertEqual(data.json["name"], "11")
        # 修改密码
        data = self.put(
            "/v1/user/password",
            json={"old_password": "111111", "new_password": "222222"},
            token=token,
        )
        self.assertErrorEqual(data)
        # 无法获取个人资料
        data = self.get("/v1/user/info", token=token)
        self.assertErrorEqual(data, BadTokenError)

    def test_info(self):
        """测试获取与修改用户资料"""
        token1 = self.create_user("11", "1@1.com", "111111").generate_token()
        token2 = self.create_user("22", "2@1.com", "111111").generate_token()
        # 获取他人资料
        data = self.get("/v1/users/11")
        self.assertErrorEqual(data)
        self.assertEqual(data.json["name"], "11")
        self.assertNotEqual(data.json["signature"], None)  # 签名不会为空
        # 获取他人资料
        data = self.get("/v1/users/22")
        self.assertErrorEqual(data)
        self.assertEqual(data.json["name"], "22")
        self.assertNotEqual(data.json["signature"], None)  # 签名不会为空
        # 获取个人资料
        data = self.get("/v1/user/info", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual(data.json["name"], "11")
        # 获取个人资料
        data = self.get("/v1/user/info", token=token2)
        self.assertErrorEqual(data)
        self.assertEqual(data.json["name"], "22")
        # locale只能设置成可选值
        data = self.put(
            "/v1/user/info",
            json={"name": "11", "signature": "222", "locale": "balabala"},
            token=token1,
        )
        self.assertErrorEqual(data, ValidateError)
        # 仅修改签名
        data = self.put(
            "/v1/user/info",
            json={"name": "11", "signature": "222", "locale": Locale.AUTO},
            token=token1,
        )
        self.assertErrorEqual(data)
        # 获取个人资料进行对比
        data = self.get("/v1/user/info", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual(data.json["name"], "11")
        self.assertEqual(data.json["signature"], "222")
        self.assertEqual(
            data.json["locale"],
            {"id": "auto", "name": "自动", "intro": "遵循浏览器设置"},
        )
        # 设置资料
        data = self.put(
            "/v1/user/info",
            json={"name": "111", "signature": "111", "locale": Locale.ZH_CN},
            token=token1,
        )
        self.assertErrorEqual(data)
        # 获取个人资料进行对比
        data = self.get("/v1/user/info", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual(data.json["name"], "111")
        self.assertEqual(data.json["signature"], "111")
        self.assertEqual(
            data.json["locale"], {"id": "zh_CN", "name": "中文（简体）", "intro": ""}
        )
        # 再次设置资料，将一些值设为空
        data = self.put(
            "/v1/user/info",
            json={"name": "111", "signature": "", "locale": Locale.ZH_CN},
            token=token1,
        )
        self.assertErrorEqual(data)
        # 获取个人资料进行对比
        data = self.get("/v1/user/info", token=token1)
        self.assertErrorEqual(data)
        self.assertEqual(data.json["name"], "111")
        self.assertEqual(data.json["signature"], "")
        self.assertEqual(
            data.json["locale"], {"id": "zh_CN", "name": "中文（简体）", "intro": ""}
        )
        # 设置成已经存在的名称，出错
        data = self.put(
            "/v1/user/info",
            json={"name": "22", "signature": "", "locale": Locale.ZH_CN},
            token=token1,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("name"))
        # 设置成不合法的名称
        data = self.put(
            "/v1/user/info",
            json={"name": "2 2", "signature": "", "locale": Locale.ZH_CN},
            token=token1,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("name"))

    def test_change_password(self):
        """测试修改密码"""
        # 创建用户
        token = self.create_user("11", "1@1.com", "111111").generate_token()
        # 测试登录
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "1@1.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        # 需要登录后才能修改
        data = self.put(
            "/v1/user/password",
            json={"old_password": "000000", "new_password": "222222"},
        )
        self.assertErrorEqual(data, NeedTokenError)
        # 用错误的原密码
        data = self.put(
            "/v1/user/password",
            json={"old_password": "000000", "new_password": "222222"},
            token=token,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("old_password"))
        self.assertIsNone(data.json["message"].get("new_password"))
        # 用正确的原密码
        data = self.put(
            "/v1/user/password",
            json={"old_password": "111111", "new_password": "222222"},
            token=token,
        )
        self.assertErrorEqual(data)
        # 测试登录，只能用222222登录了
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "1@1.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        captcha_info, captcha = self.get_captcha()
        self.assertErrorEqual(data, ValidateError)
        data = self.post(
            "/v1/user/token",
            json={
                "email": "1@1.com",
                "password": "222222",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))

    def test_reset_password1(self):
        """测试重置密码"""
        # 创建用户
        self.create_user("11", "AAA@a.com", "111111").generate_token()
        # 测试登录
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "AAA@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        # 尝试重置不存在的邮箱
        data = self.delete(
            "/v1/user/password",
            json={"email": "2@1.com", "v_code": "1", "password": "111111"},
        )
        self.assertErrorEqual(data, ValidateError)
        # 获取人机验证码
        captcha_info, captcha = self.get_captcha()
        # 获取重置密码邮件
        data = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "AAA@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content = VCode.objects(
            type=VCodeType.RESET_PASSWORD, info="aaa@a.com"
        ).first()["content"]
        # 使用错误的vCode
        data = self.delete(
            "/v1/user/password",
            json={"email": "AAA@a.com", "v_code": "1", "password": "222222"},
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("v_code"))
        # 使用错误的密码格式
        data = self.delete(
            "/v1/user/password",
            json={"email": "AAA@a.com", "v_code": content, "password": "2"},
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("password"))
        # 正确的修改
        data = self.delete(
            "/v1/user/password",
            json={"email": "AAA@a.com", "v_code": content, "password": "222222"},
        )
        self.assertErrorEqual(data)
        # 测试登录，只能用222222登录了
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "AAA@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        captcha_info, captcha = self.get_captcha()
        self.assertErrorEqual(data, ValidateError)
        data = self.post(
            "/v1/user/token",
            json={
                "email": "AAA@a.com",
                "password": "222222",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))

    def test_reset_password2(self):
        """测试重置密码（重置密码邮件使用大写）"""
        # 创建用户
        self.create_user("11", "aaa@a.com", "111111").generate_token()
        # 测试登录
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "aaa@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        # 尝试重置不存在的邮箱
        data = self.delete(
            "/v1/user/password",
            json={"email": "2@1.com", "v_code": "1", "password": "111111"},
        )
        self.assertErrorEqual(data, ValidateError)
        # 获取人机验证码
        captcha_info, captcha = self.get_captcha()
        # 获取重置密码邮件
        data = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "AAA@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content = VCode.objects(
            type=VCodeType.RESET_PASSWORD, info="aaa@a.com"
        ).first()["content"]
        # 正确的修改
        data = self.delete(
            "/v1/user/password",
            json={"email": "aaa@a.com", "v_code": content, "password": "222222"},
        )
        self.assertErrorEqual(data)
        # 测试登录，只能用222222登录了
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "aaa@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        captcha_info, captcha = self.get_captcha()
        self.assertErrorEqual(data, ValidateError)
        data = self.post(
            "/v1/user/token",
            json={
                "email": "aaa@a.com",
                "password": "222222",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))

    def test_reset_password3(self):
        """测试重置密码（重置请求使用大写）"""
        # 创建用户
        self.create_user("11", "aaa@a.com", "111111").generate_token()
        # 测试登录
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "aaa@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        # 尝试重置不存在的邮箱
        data = self.delete(
            "/v1/user/password",
            json={"email": "2@1.com", "v_code": "1", "password": "111111"},
        )
        self.assertErrorEqual(data, ValidateError)
        # 获取人机验证码
        captcha_info, captcha = self.get_captcha()
        # 获取重置密码邮件
        data = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "aaa@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content = VCode.objects(
            type=VCodeType.RESET_PASSWORD, info="aaa@a.com"
        ).first()["content"]
        # 正确的修改
        data = self.delete(
            "/v1/user/password",
            json={"email": "AAA@a.com", "v_code": content, "password": "222222"},
        )
        self.assertErrorEqual(data)
        # 测试登录，只能用222222登录了
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "aaa@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        captcha_info, captcha = self.get_captcha()
        self.assertErrorEqual(data, ValidateError)
        data = self.post(
            "/v1/user/token",
            json={
                "email": "aaa@a.com",
                "password": "222222",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))

    def test_change_email1(self):
        """测试修改邮箱"""
        # 创建用户
        token = self.create_user("11", "AAA@a.com", "111111").generate_token()
        token2 = self.create_user("22", "BBB@b.com", "111111").generate_token()
        # 测试登录
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "AAA@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        # 不登录修改邮箱
        data = self.put(
            "/v1/user/email",
            json={
                "old_email_v_code": "A21KLk",
                "new_email": "CCC@c.com",
                "new_email_v_code": "kK12YI",
            },
        )
        self.assertErrorEqual(data, NeedTokenError)
        # 错误的邮箱格式
        data = self.put(
            "/v1/user/email",
            json={
                "old_email_v_code": "A21KLk",
                "new_email": "2@1.1",
                "new_email_v_code": "kK12YI",
            },
            token=token,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("new_email"))
        # 和自己旧邮箱相同
        data = self.put(
            "/v1/user/email",
            json={
                "old_email_v_code": "A21KLk",
                "new_email": "AAA@a.com",
                "new_email_v_code": "kK12YI",
            },
            token=token,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("new_email"))
        # 使用已注册的邮箱
        data = self.put(
            "/v1/user/email",
            json={
                "old_email_v_code": "A21KLk",
                "new_email": "BBB@b.com",
                "new_email_v_code": "kK12YI",
            },
            token=token,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("new_email"))
        # 申请重置邮箱邮件验证码
        data = self.post("/v1/reset-email-codes", token=token)
        self.assertErrorEqual(data)
        content = VCode.objects(type=VCodeType.RESET_EMAIL, info="aaa@a.com").first()[
            "content"
        ]
        captcha_info, captcha = self.get_captcha()
        # 申请确认邮箱邮件验证码
        data = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "CCC@c.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content2 = VCode.objects(
            type=VCodeType.CONFIRM_EMAIL, info="ccc@c.com"
        ).first()["content"]
        # 使用错误的验证码
        data = self.put(
            "/v1/user/email",
            json={
                "old_email_v_code": "A21KLk.",
                "new_email": "CCC@c.com",
                "new_email_v_code": "kK12YI.",
            },
            token=token,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("old_email_v_code"))
        self.assertIsNotNone(data.json["message"].get("new_email_v_code"))
        # 使用错误的邮箱
        data = self.put(
            "/v1/user/email",
            json={
                "old_email_v_code": content,
                "new_email": "3@1.com",
                "new_email_v_code": content2,
            },
            token=token,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("new_email_v_code"))
        # 他人使用正确的验证码
        data = self.put(
            "/v1/user/email",
            json={
                "old_email_v_code": content,
                "new_email": "CCC@c.com",
                "new_email_v_code": content2,
            },
            token=token2,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json["message"].get("old_email_v_code"))
        # 正确的修改
        data = self.put(
            "/v1/user/email",
            json={
                "old_email_v_code": content,
                "new_email": "CCC@c.com",
                "new_email_v_code": content2,
            },
            token=token,
        )
        self.assertErrorEqual(data)
        # 测试登录，只能用CCC@c.com登录了
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "AAA@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        captcha_info, captcha = self.get_captcha()
        self.assertErrorEqual(data, ValidateError)
        data = self.post(
            "/v1/user/token",
            json={
                "email": "CCC@c.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        # 用户邮箱记录的是小写
        user = User.get_by_email("CCC@c.com")
        self.assertEqual(user.email, "ccc@c.com")

    def test_change_email2(self):
        """测试修改邮箱（申请重置邮箱邮件验证码使用大写）"""
        # 创建用户
        token = self.create_user("11", "AAA@a.com", "111111").generate_token()
        # 测试登录
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "AAA@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        # 申请重置邮箱邮件验证码
        data = self.post("/v1/reset-email-codes", token=token)
        self.assertErrorEqual(data)
        content = VCode.objects(type=VCodeType.RESET_EMAIL, info="aaa@a.com").first()[
            "content"
        ]
        captcha_info, captcha = self.get_captcha()
        # 申请确认邮箱邮件验证码
        data = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "CCC@c.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content2 = VCode.objects(
            type=VCodeType.CONFIRM_EMAIL, info="ccc@c.com"
        ).first()["content"]
        # 正确的修改
        data = self.put(
            "/v1/user/email",
            json={
                "old_email_v_code": content,
                "new_email": "ccc@c.com",
                "new_email_v_code": content2,
            },
            token=token,
        )
        self.assertErrorEqual(data)
        # 测试登录，只能用CCC@c.com登录了
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "AAA@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        captcha_info, captcha = self.get_captcha()
        self.assertErrorEqual(data, ValidateError)
        data = self.post(
            "/v1/user/token",
            json={
                "email": "CCC@c.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        # 用户邮箱记录的是小写
        user = User.get_by_email("CCC@c.com")
        self.assertEqual(user.email, "ccc@c.com")

    def test_change_email3(self):
        """测试修改邮箱（申请重置请求使用大写）"""
        # 创建用户
        token = self.create_user("11", "AAA@a.com", "111111").generate_token()
        # 测试登录
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "AAA@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        # 申请重置邮箱邮件验证码
        data = self.post("/v1/reset-email-codes", token=token)
        self.assertErrorEqual(data)
        content = VCode.objects(type=VCodeType.RESET_EMAIL, info="aaa@a.com").first()[
            "content"
        ]
        captcha_info, captcha = self.get_captcha()
        # 申请确认邮箱邮件验证码
        data = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "ccc@c.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content2 = VCode.objects(
            type=VCodeType.CONFIRM_EMAIL, info="ccc@c.com"
        ).first()["content"]
        # 正确的修改
        data = self.put(
            "/v1/user/email",
            json={
                "old_email_v_code": content,
                "new_email": "CCC@c.com",
                "new_email_v_code": content2,
            },
            token=token,
        )
        self.assertErrorEqual(data)
        # 测试登录，只能用CCC@c.com登录了
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "AAA@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        captcha_info, captcha = self.get_captcha()
        self.assertErrorEqual(data, ValidateError)
        data = self.post(
            "/v1/user/token",
            json={
                "email": "CCC@c.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
        # 用户邮箱记录的是小写
        user = User.get_by_email("CCC@c.com")
        self.assertEqual(user.email, "ccc@c.com")

    def test_repetition(self):
        """测试重复用户名/邮箱"""
        email = "1@1.com"
        name = "11"
        password = "123123"
        self.create_user(name, email, password).generate_token()
        # == 正确的注册一个账号 ==
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 申请邮件验证码，直接报错，邮箱已注册
        v2 = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": email,
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(v2, ValidateError)
        self.assertIn("email", v2.json["message"])
        # 也报错邮箱已注册
        data = self.post(
            "/v1/users",
            json={
                "email": email,
                "name": name,
                "password": password,
                "v_code": "123",
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIn("email", data.json["message"])
        self.assertIn("name", data.json["message"])

    def test_repetition_capital1(self):
        """测试重复用户名/邮箱(大小写)"""
        email = "A@A.com"
        name = "aa"
        password = "123123"
        self.create_user(name, email, password).generate_token()
        # == 正确的注册一个账号 ==
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 申请邮件验证码，直接报错，邮箱已注册
        v2 = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": email.upper(),
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(v2, ValidateError)
        self.assertIn("email", v2.json["message"])
        # 也报错邮箱已注册
        data = self.post(
            "/v1/users",
            json={
                "email": email.upper(),
                "name": name,
                "password": password,
                "v_code": "123",
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIn("email", data.json["message"])
        self.assertIn("name", data.json["message"])

    def test_repetition_capital2(self):
        """测试重复用户名/邮箱(大小写)"""
        email = "A@A.com"
        name = "aa"
        password = "123123"
        self.create_user(name, email, password).generate_token()
        # == 正确的注册一个账号 ==
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 申请邮件验证码，直接报错，邮箱已注册
        v2 = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": email.lower(),
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(v2, ValidateError)
        self.assertIn("email", v2.json["message"])
        # 也报错邮箱已注册
        data = self.post(
            "/v1/users",
            json={
                "email": email.lower(),
                "name": name,
                "password": password,
                "v_code": "123",
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIn("email", data.json["message"])
        self.assertIn("name", data.json["message"])

    def test_repetition_capital3(self):
        """测试重复用户名/邮箱(大小写)"""
        email = "a@a.com"
        name = "aa"
        password = "123123"
        self.create_user(name, email, password).generate_token()
        # == 正确的注册一个账号 ==
        # 申请人机验证码
        captcha_info, captcha = self.get_captcha()
        # 申请邮件验证码，直接报错，邮箱已注册
        v2 = self.post(
            "/v1/confirm-email-codes",
            json={
                "email": email.upper(),
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(v2, ValidateError)
        self.assertIn("email", v2.json["message"])
        # 也报错邮箱已注册
        data = self.post(
            "/v1/users",
            json={
                "email": email.upper(),
                "name": name,
                "password": password,
                "v_code": "123",
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIn("email", data.json["message"])
        self.assertIn("name", data.json["message"])

    def test_banned(self):
        """测试用户被封禁"""
        token = self.create_user("11", "1@1.com", "123123").generate_token()
        user = User.objects(email="1@1.com").first()
        user.banned = True
        user.save()
        # 尝试访问需要登录的接口，报错
        data = self.get("/v1/user/info", token=token)
        self.assertErrorEqual(data, UserBannedError)

    def test_register_and_login1(self):
        """测试注册的可以登陆"""
        captcha_info, captcha = self.get_captcha()
        # 申请验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "aaa@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        v_code = VCode.objects(type=VCodeType.CONFIRM_EMAIL, info="aaa@a.com").first()[
            "content"
        ]
        # 注册
        data = self.post(
            "/v1/users",
            json={
                "email": "aaa@a.com",
                "name": "aaa",
                "password": "111111",
                "v_code": v_code,
            },
        )
        self.assertErrorEqual(data)
        # 登陆
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "aaa@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)

    def test_register_and_login2(self):
        """测试注册的可以登陆"""
        captcha_info, captcha = self.get_captcha()
        # 申请验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "AAA@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        v_code = VCode.objects(type=VCodeType.CONFIRM_EMAIL, info="aaa@a.com").first()[
            "content"
        ]
        # 注册
        data = self.post(
            "/v1/users",
            json={
                "email": "AAA@a.com",
                "name": "aaa",
                "password": "111111",
                "v_code": v_code,
            },
        )
        self.assertErrorEqual(data)
        # 登陆
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "AAA@a.com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)

    def test_register_and_login3(self):
        """测试注册的可以登陆（大小写不同）"""
        captcha_info, captcha = self.get_captcha()
        # 申请验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "AAA@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        v_code = VCode.objects(type=VCodeType.CONFIRM_EMAIL, info="aaa@a.com").first()[
            "content"
        ]
        # 注册
        data = self.post(
            "/v1/users",
            json={
                "email": "AAA@a.com",
                "name": "aaa",
                "password": "111111",
                "v_code": v_code,
            },
        )
        self.assertErrorEqual(data)
        # 登陆
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": "Aaa@A.Com",
                "password": "111111",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)

    def test_register_and_reset_password1(self):
        """测试注册的可以修改密码"""
        captcha_info, captcha = self.get_captcha()
        # 申请验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "aaa@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        v_code = VCode.objects(type=VCodeType.CONFIRM_EMAIL, info="aaa@a.com").first()[
            "content"
        ]
        # 注册
        data = self.post(
            "/v1/users",
            json={
                "email": "aaa@a.com",
                "name": "aaa",
                "password": "111111",
                "v_code": v_code,
            },
        )
        self.assertErrorEqual(data)
        # 获取人机验证码
        captcha_info, captcha = self.get_captcha()
        # 获取重置密码邮件
        data = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "aaa@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content = VCode.objects(
            type=VCodeType.RESET_PASSWORD, info="aaa@a.com"
        ).first()["content"]
        data = self.delete(
            "/v1/user/password",
            json={"email": "aaa@a.com", "v_code": content, "password": "222222"},
        )
        self.assertErrorEqual(data)

    def test_register_and_reset_password2(self):
        """测试注册的可以修改密码"""
        captcha_info, captcha = self.get_captcha()
        # 申请验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "AAA@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        v_code = VCode.objects(type=VCodeType.CONFIRM_EMAIL, info="aaa@a.com").first()[
            "content"
        ]
        # 注册
        data = self.post(
            "/v1/users",
            json={
                "email": "AAA@a.com",
                "name": "aaa",
                "password": "111111",
                "v_code": v_code,
            },
        )
        self.assertErrorEqual(data)
        # 获取人机验证码
        captcha_info, captcha = self.get_captcha()
        # 获取重置密码邮件
        data = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "AAA@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content = VCode.objects(
            type=VCodeType.RESET_PASSWORD, info="aaa@a.com"
        ).first()["content"]
        data = self.delete(
            "/v1/user/password",
            json={"email": "AAA@a.com", "v_code": content, "password": "222222"},
        )
        self.assertErrorEqual(data)

    def test_register_and_reset_password3(self):
        """测试注册的可以修改密码（大小写不同）"""
        captcha_info, captcha = self.get_captcha()
        # 申请验证码
        self.post(
            "/v1/confirm-email-codes",
            json={
                "email": "AAA@a.com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        # 获取验证码内容
        v_code = VCode.objects(type=VCodeType.CONFIRM_EMAIL, info="aaa@a.com").first()[
            "content"
        ]
        # 注册
        data = self.post(
            "/v1/users",
            json={
                "email": "AAA@a.com",
                "name": "aaa",
                "password": "111111",
                "v_code": v_code,
            },
        )
        self.assertErrorEqual(data)
        # 获取人机验证码
        captcha_info, captcha = self.get_captcha()
        # 获取重置密码邮件
        data = self.post(
            "/v1/reset-password-codes",
            json={
                "email": "Aaa@A.Com",
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        content = VCode.objects(
            type=VCodeType.RESET_PASSWORD, info="aaa@a.com"
        ).first()["content"]
        data = self.delete(
            "/v1/user/password",
            json={"email": "Aaa@A.Com", "v_code": content, "password": "222222"},
        )
        self.assertErrorEqual(data)

    def test_admin_register(self):
        """测试管理后台注册API"""
        test_default_users_count = DEFAULT_USERS_COUNT + 2
        admin_user = self.create_user("admin")
        admin_user.admin = True
        admin_user.save()
        admin_token = admin_user.generate_token()
        user = self.create_user("user")
        user_token = user.generate_token()
        self.assertEqual(User.objects.count(), test_default_users_count + 0)
        # == 非管理员无法注册 ==
        data = self.post(
            "/v1/admin/users",
            json={
                "email": "AAA@a.com",
                "name": "12134",
                "password": "111111",
            },
            token=user_token,
        )
        self.assertErrorEqual(data, NoPermissionError)
        self.assertEqual(User.objects.count(), test_default_users_count + 0)
        # == 正确的注册 ==
        data = self.post(
            "/v1/admin/users",
            json={
                "email": "AAA@a.com",
                "name": "12134",
                "password": "111111",
            },
            token=admin_token,
        )
        self.assertErrorEqual(data)
        self.assertEqual(User.objects.count(), test_default_users_count + 1)
        # == 注册过的邮箱不能再次注册 ==
        data = self.post(
            "/v1/admin/users",
            json={
                "email": "AAA@a.com",
                "name": "12134a",
                "password": "111111",
            },
            token=admin_token,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), test_default_users_count + 1)
        # == 注册过的昵称不能再次注册 ==
        data = self.post(
            "/v1/admin/users",
            json={
                "email": "AAA1@a.com",
                "name": "12134",
                "password": "111111",
            },
            token=admin_token,
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertEqual(User.objects.count(), test_default_users_count + 1)
        # 用户邮箱记录的是小写
        user = User.get_by_email("AAA@a.com")
        self.assertEqual(user.email, "aaa@a.com")

    def test_admin_edit_user_password(self):
        """测试管理后台修改用户密码"""
        admin_user = self.create_user("admin")
        admin_user.admin = True
        admin_user.save()
        admin_token = admin_user.generate_token()
        user = self.create_user("user")
        user_token = user.generate_token()
        new_password = "new_password111111"
        # == 非管理员无法修改 ==
        data = self.put(
            "/v1/admin/users/" + str(user.id),
            json={
                "password": new_password,
            },
            token=user_token,
        )
        self.assertErrorEqual(data, NoPermissionError)
        # 使用新密码无法登陆
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": user.email,
                "password": new_password,
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data, ValidateError)
        self.assertIsNotNone(data.json.get("message").get("password"))
        # == 管理员可以修改 ==
        data = self.put(
            "/v1/admin/users/" + str(user.id),
            json={
                "password": new_password,
            },
            token=admin_token,
        )
        self.assertErrorEqual(data)
        # 使用新密码可以登陆
        captcha_info, captcha = self.get_captcha()
        data = self.post(
            "/v1/user/token",
            json={
                "email": user.email,
                "password": new_password,
                "captcha_info": captcha_info,
                "captcha": captcha,
            },
        )
        self.assertErrorEqual(data)
        self.assertIsNotNone(data.json.get("token"))
