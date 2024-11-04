from typing import Union
from app.core.responses import MoePagination
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_group
from app.exceptions import NoPermissionError
from app.models.team import Team
from app.models.project import Project
from app.validators.role import RoleSchema


class RoleListAPI(MoeAPIView):
    @token_required
    @fetch_group
    def get(self, group: Union[Team, Project]):
        """
        @api {get} /v1/<group_type>/<group_id>/roles 获取自定义角色
        @apiVersion 1.0.0
        @apiName get_team_role
        @apiGroup Role
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiParam {String} team_id 团队id

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        p = MoePagination()
        if not self.current_user.can(group, group.permission_cls.ACCESS):
            raise NoPermissionError
        objects = group.roles(skip=p.skip, limit=p.limit)
        return p.set_objects(objects)

    @token_required
    @fetch_group
    def post(self, group):
        """
        @api {post} /v1/<group_type>/<group_id>/roles 创建自定义角色
        @apiVersion 1.0.0
        @apiName create_team_role
        @apiGroup Role
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiParam {String} set_id 项目集id

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(group, group.permission_cls.CREATE_ROLE):
            raise NoPermissionError
        data = self.get_json(
            RoleSchema(),
            context={"current_user_role": self.current_user.get_role(group)},
        )
        group.create_role(
            name=data["name"],
            level=data["level"],
            permissions=data["permissions"],
            intro=data["intro"],
            operator=self.current_user,
        )


class RoleAPI(MoeAPIView):
    @token_required
    @fetch_group
    def put(self, group: Union[Team, Project], role_id: str):
        """
        @api {put} /v1/<group_type>/<group_id>/roles/<role_id> 修改自定义角色
        @apiVersion 1.0.0
        @apiName create_team_role
        @apiGroup Role
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiParam {String} role_id 角色id

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(group, group.permission_cls.CREATE_ROLE):
            raise NoPermissionError
        data = self.get_json(
            RoleSchema(),
            context={"current_user_role": self.current_user.get_role(group)},
        )
        group.edit_role(
            id=role_id,
            name=data["name"],
            level=data["level"],
            permissions=data["permissions"],
            intro=data["intro"],
            operator=self.current_user,
        )

    @token_required
    @fetch_group
    def delete(self, group, role_id):
        """
        @api {delete} /v1/<group_type>/<group_id>/roles/<role_id> 删除自定义角色
        @apiVersion 1.0.0
        @apiName delete_team_role
        @apiGroup Role
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiParam {String} role_id 角色id

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(group, group.permission_cls.DELETE_ROLE):
            raise NoPermissionError
        group.delete_role(id=role_id)
