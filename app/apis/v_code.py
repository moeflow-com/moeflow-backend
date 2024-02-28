from flask import current_app
from app.constants.v_code import VCodeTypeIntro

from app.core.views import MoeAPIView
from app.decorators.auth import admin_required, token_required
from app.models.v_code import Captcha, VCode, VCodeType
from app.validators import ConfirmEmailVCodeSchema, ResetPasswordVCodeSchema


class CaptchaAPI(MoeAPIView):
    def post(self):
        """
        @api {post} /v1/captchas 获取人机图形验证码
        @apiVersion 1.0.0
        @apiName captcha_v_code
        @apiGroup VCode

        @apiSuccess {String} image base64格式的验证码图片
        @apiSuccess {String} info 验证码标识符
        @apiSuccessExample {json} 返回示例
        {
            "image": "data:image/jpg;base64,/9j/4A...FAH//2Q==",
            "info": "08757f4f06e2191815fa03fbfa133335"
        }
        """
        captcha = Captcha.create()
        return {"info": captcha.info, "image": captcha.to_base64()}


class ConfirmEmailVCodeAPI(MoeAPIView):
    def post(self):
        """
        @api {post} /v1/confirm-email-codes 确认邮箱邮件验证码
        @apiVersion 1.0.0
        @apiName confirm_email_v_code
        @apiGroup VCode

        @apiUse APIHeader
        @apiParam {String} email 邮箱地址
        @apiParam {String} captchaInfo  人机验证码标识符
        @apiParam {String} captcha      人机验证码内容
        @apiParamExample {json} 请求示例
        {
            "email": "your@email.com",
            "captcha_info":"f9ef49a6c9b347e3e8e941e25bcf5092",
            "captcha":"3276"
        }

        @apiSuccess {Number} wait 下次发送等待时间
        @apiSuccessExample {json} 返回示例
        {
            "wait": 60
        }

        @apiUse ValidateError
        @apiUse VCodeCoolingError
        """
        wait = current_app.config.get(
            "CONFIRM_EMAIL_WAIT_SECONDS", 60
        )  # 重新发送等待的秒数
        data = self.get_json(ConfirmEmailVCodeSchema())
        email = data["email"].lower()
        v_code = VCode.create(VCodeType.CONFIRM_EMAIL, email, wait=wait)
        v_code.to_email(email)
        return {"wait": wait}


class ResetEmailVCodeAPI(MoeAPIView):
    @token_required
    def post(self):
        """
        @api {post} /v1/reset-email-codes 重置邮箱邮件验证码
        @apiVersion 1.0.0
        @apiName reset_email_v_code
        @apiGroup VCode

        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccess {Number} wait 下次发送等待时间
        @apiSuccessExample {json} 返回示例
        {
            "wait": 60
        }

        @apiUse VCodeCoolingError
        """
        wait = current_app.config.get(
            "RESET_EMAIL_WAIT_SECONDS", 60
        )  # 重新发送等待的秒数
        email = self.current_user.email.lower()
        v_code = VCode.create(VCodeType.RESET_EMAIL, email, wait=wait)
        v_code.to_email(email)
        return {"wait": wait}


class ResetPasswordVCodeAPI(MoeAPIView):
    def post(self):
        """
        @api {post} /v1/reset-password-codes 重置密码邮件验证码
        @apiVersion 1.0.0
        @apiName reset_password_v_code
        @apiGroup VCode

        @apiUse APIHeader

        @apiParam {String} email 邮箱地址
        @apiParam {String} captchaInfo  人机验证码标识符
        @apiParam {String} captcha      人机验证码内容
        @apiParamExample {json} 请求示例
        {
            "email": "your@email.com",
            "captcha_info":"f9ef49a6c9b347e3e8e941e25bcf5092",
            "captcha":"3276"
        }

        @apiSuccess {Number} wait 下次发送等待时间
        @apiSuccessExample {json} 返回示例
        {
            "wait": 60
        }

        @apiUse VCodeCoolingError
        """
        wait = current_app.config.get(
            "RESET_PASSWORD_WAIT_SECONDS", 60
        )  # 重新发送等待的秒数
        data = self.get_json(ResetPasswordVCodeSchema())
        email = data["email"].lower()
        v_code = VCode.create(VCodeType.RESET_PASSWORD, email, wait=wait)
        v_code.to_email(email)
        return {"wait": wait}


class AdminVCodeListAPI(MoeAPIView):
    @admin_required
    def get(self):
        """返回最新的 100 个验证码"""
        codes = (
            VCode.objects(type__ne=VCodeType.CAPTCHA).limit(100).order_by("-send_time")
        )
        return [
            {
                "id": str(code.id),
                "content": code.content,
                "intro": VCodeTypeIntro[code.type],
                "info": code.info,
                "expires": code.expires.isoformat(),
                "wrong_count": code.wrong_count,
                "send_time": code.send_time.isoformat(),
            }
            for code in codes
        ]
