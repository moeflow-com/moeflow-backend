from typing import Union
from flask import request

from app.core.responses import MoePagination
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_model, fetch_group
from app.exceptions import NoPermissionError
from app.models.project import Project
from app.models.team import Team
from app.models.user import User
from app.validators.member import ChangeMemberSchema


class MemberListAPI(MoeAPIView):
    @token_required
    @fetch_group
    def get(self, group):
        """
        @api {get} /v1/<group_type>/<group_id>/users 获取团体的成员
        @apiVersion 1.0.0
        @apiName get_group_user
        @apiGroup Member
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiSuccessExample {json} 返回示例
        [
            {
                name: ""
                ...
            }
        ]
        """
        if not self.current_user.can(group, group.permission_cls.ACCESS):
            raise NoPermissionError
        # 获取查询参数
        word = request.args.get("word")
        # 分页
        p = MoePagination()
        users = group.users(skip=p.skip, limit=p.limit, word=word)
        # 获取用户关系
        relations = group.relation_cls.objects(group=group, user__in=users)
        # 构建字典用于快速匹配
        user_roles_data = {}
        for relation in relations:
            user_roles_data[str(relation.user.id)] = relation.role.to_api()
        # 构建数据
        data = []
        for user in users:
            user_data = user.to_api()
            user_role_data = user_roles_data.get(str(user.id))
            if user_role_data:
                user_data["role"] = user_role_data
            else:
                user_data["role"] = None
            data.append(user_data)
        return p.set_data(data=data, count=users.count())


class MemberAPI(MoeAPIView):
    @token_required
    @fetch_group
    @fetch_model(User)
    def put(self, group: Union[Project, Team], user: User):
        """
        @api {put} /v1/<group_type>/<group_id>/users/<user_id> 修改团体的成员
        @apiVersion 1.0.0
        @apiName edit_group_user
        @apiGroup Member
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiParam {String} role 角色 ID
        @apiParamExample {json} 请求示例
        {
            "role": "roleID"
        }

        @apiSuccessExample {json} 返回示例
        {
            "message": "修改成功"
        }
        """
        # 处理请求数据
        data = self.get_json(ChangeMemberSchema())
        role = group.change_user_role(user, data["role"], operator=self.current_user)
        return {"message": "设置成功", "role": role.to_api()}

    @token_required
    @fetch_group
    @fetch_model(User)
    def delete(self, group: Union[Project, Team], user: User):
        """
        @api {delete} /v1/<group_type>/<group_id>/users/<user_id> 删除团体的成员
        @apiVersion 1.0.0
        @apiName delete_group_user
        @apiGroup Member
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiSuccessExample {json} 返回示例
        {
            "message": "删除成功"
        }
        """
        return group.delete_uesr(user, operator=self.current_user)
