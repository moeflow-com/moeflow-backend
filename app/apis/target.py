from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_model
from app.models.target import Target
from app.models.project import ProjectPermission
from app.exceptions import NoPermissionError
from flask_babel import gettext


class TargetAPI(MoeAPIView):
    @token_required
    @fetch_model(Target)
    def delete(self, target: Target):
        """
        @api {get} /v1/targets/<target_id> 删除翻译目标
        @apiVersion 1.0.0
        @apiName deleteTargetAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(target.project, ProjectPermission.DELETE_TARGET):
            raise NoPermissionError
        target.clear()
        return {
            "message": gettext("删除成功"),
        }
