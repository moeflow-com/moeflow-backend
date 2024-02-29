"""
关于用户个人的API
"""
from bson import ObjectId
from flask import current_app, request

from app import oss
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.exceptions import UploadFileNotFoundError
from app.models.team import Team, TeamPermission
from flask_babel import gettext, lazy_gettext
from app.utils.logging import logger
import oss2
from app.exceptions.base import NoPermissionError, RequestDataWrongError


class AvatarAPI(MoeAPIView):
    @token_required
    def put(self):
        """@apiDeprecated
        @api {put} /v1/avatar 修改头像
        @apiVersion 1.0.0
        @apiName change_avatar
        @apiGroup Me
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {File} file 头像文件
        @apiParam {string} type 类型
        @apiParam {ObjectId} id ID

        @apiSuccess {String} avatar 头像地址
        @apiSuccessExample {json} 返回示例
        {
            "avatar": "http://moeflow.com/avatar/AbcDEF123.jpg"
        }

        @apiUse ValidateError
        """
        file = request.files.get("file")
        owner_type = request.form.get("type")
        owner_id = request.form.get("id")
        if not file:
            raise UploadFileNotFoundError("请选择图片")
        if owner_type == "user":
            avatar_prefix = current_app.config["OSS_USER_AVATAR_PREFIX"]
            avatar_owner = self.current_user
        elif owner_type == "team":
            avatar_prefix = current_app.config["OSS_TEAM_AVATAR_PREFIX"]
            avatar_owner = Team.by_id(owner_id)
            if not self.current_user.can(avatar_owner, TeamPermission.CHANGE):
                raise NoPermissionError
        else:
            raise RequestDataWrongError(lazy_gettext("不支持的头像类型"))
        if owner_type != "user" and owner_id is None:
            raise RequestDataWrongError(lazy_gettext("缺少id"))
        filename = str(ObjectId()) + ".jpg"
        oss.upload(avatar_prefix, filename, file)
        # 删除旧的头像
        if avatar_owner.has_avatar():
            try:
                oss.delete(
                    avatar_prefix,
                    avatar_owner._avatar,
                )
            except oss2.exceptions.NoSuchKey as e:
                logger.error(e)
            except Exception as e:
                logger.error(e)
        # 设置新的头像
        avatar_owner.avatar = filename
        avatar_owner.save()
        return {"message": gettext("修改成功"), "avatar": avatar_owner.avatar}
