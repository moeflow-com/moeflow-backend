from app.models.project import Project, ProjectAllowApplyType
from app.core.rbac import AllowApplyType
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_group
from app.exceptions.join_process import GroupNotOpenError


class GroupPublicInfoAPI(MoeAPIView):
    @token_required
    @fetch_group
    def get(self, group):
        """
        @api {get} /v1/<group_type>/<group_id>/public-info 获取收到的申请
        @apiVersion 1.0.0
        @apiName getGroupPublicInfo
        @apiGroup Group
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        """
        relation = self.current_user.get_relation(group)
        if relation is None:
            if group.allow_apply_type == AllowApplyType.NONE:
                raise GroupNotOpenError
            if (
                isinstance(group, Project)
                and group.allow_apply_type == ProjectAllowApplyType.TEAM_USER
            ):
                team_relation = self.current_user.get_relation(group.team)
                if team_relation is None:
                    raise GroupNotOpenError
        return {
            "id": str(group.id),
            "name": group.name,
            "joined": True if relation else False,
            "user_count": group.user_count,
            "application_check_type": group.application_check_type,
        }
