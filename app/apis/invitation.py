from flask_babel import gettext

from app.core.responses import MoePagination
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_model, fetch_group
from app.exceptions import NoPermissionError, RoleNotExistError
from app.models.invitation import Invitation
from app.validators.join_process import (
    ChangeInvitationSchema,
    CheckInvitationSchema,
    CreateInvitationSchema,
    SearchInvitationSchema,
)
from flask_apikit.utils import QueryParser


class InvitationListAPI(MoeAPIView):
    @token_required
    @fetch_group
    def get(self, group):
        """
        @api {get} /v1/<group_type>/<group_id>/invitations 获取发出的邀请
        @apiVersion 1.0.0
        @apiName team_invitations
        @apiGroup JoinProcess
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiParam {Number} page 页数
        @apiParam {Number} limit 限制的数量(最大100)
        @apiParam {Number} [status] 状态,可以使用逗号分割查询多种状态,如status=1,2 ,没有则返回所有状态

        @apiUse InvitationInfoModel
        @apiSuccessExample {json} 返回示例
        [
            {
                "create_time": "2017-07-28T07:43:54+00:00",
                "id": "597aeb3a7e4b0378c3e9e502",
                "operator": {
                    "avatar": "",
                    "id": "5911930d7e4b036e2df3a910",
                    "name": "112313",
                    "signature": "1"
                },
                "status": 1,
                "group": {
                    "avatar": "",
                    "id": "594102dc7e4b03031e3cd766",
                    "name": "11231213"
                },
                "group_type": "team",
                "user": {
                    "avatar": "",
                    "id": "5912887e7e4b0379123dd57a",
                    "name": "打的",
                    "signature": ""
                }
            }
        ]

        @apiUse ValidateError
        @apiUse TeamNotExistError
        @apiUse ProjectNotExistError
        @apiUse GroupTypeNotSupportError
        """
        if not self.current_user.can(group, group.permission_cls.INVITE_USER):
            raise NoPermissionError
        data = self.get_query({"status": [QueryParser.int]}, SearchInvitationSchema())
        p = MoePagination()
        objects = group.invitations(status=data["status"], skip=p.skip, limit=p.limit)
        return p.set_objects(objects)

    @token_required
    @fetch_group
    def post(self, group):
        """
        @api {post} /v1/<group_type>/<group_id>/invitations 邀请加入团队
        @apiVersion 1.0.0
        @apiName add_invitation
        @apiGroup JoinProcess
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiParam {String} user_id 用户id
        @apiParam {String} role_id 角色id
        @apiParam {String} message 邀请信息
        @apiParamExample {json} 请求示例
        {
            "user_id":"4321930d7e4b036e2df3a911",
            "role_id":"30",
            "message":"快进来"
        }

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "邀请成功"
        }

        @apiUse NeedTokenError
        @apiUse BadTokenError
        @apiUse NoPermissionError
        @apiUse InvitationAlreadyExistError
        @apiUse GroupTypeNotSupportError
        @apiUse TeamNotExistError
        @apiUse ProjectNotExistError
        @apiUse RoleNotExistError
        @apiUse UserNotExistError
        @apiUse ValidateError
        """
        data = self.get_json(CreateInvitationSchema(), context={"group": group})
        return self.current_user.invite(
            data["user"], group, data["role"], data["message"]
        )


class InvitationAPI(MoeAPIView):
    @token_required
    @fetch_model(Invitation)
    def put(self, invitation):
        """
        @api {put} /v1/invitations/<id> 修改邀请
        @apiVersion 1.0.0
        @apiName change_invitation_role
        @apiGroup JoinProcess
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} id 邀请id
        @apiParam {String} role_id 角色id
        @apiParamExample {json} 请求示例
        {
            "role_id":"30"
        }

        @apiUse NeedTokenError
        @apiUse BadTokenError
        @apiUse NoPermissionError
        @apiUse InvitationNotExistError
        """
        invitation.can_change_status()
        data = self.get_json(ChangeInvitationSchema())
        # 当前用户没有权限
        if not self.current_user.can(
            invitation.group, invitation.group.permission_cls.INVITE_USER
        ):
            raise NoPermissionError
        self_role = self.current_user.get_role(invitation.group)
        # 用户当前的等级小于或等于将要邀请进来的用户,说明是更高级用户邀请的，当前用户不能编辑
        if self_role.level <= invitation.role.level:
            raise NoPermissionError(gettext("只能修改邀请角色等级比您低的邀请"))
        # 获取将要设置的Role
        role = invitation.group.role_cls.objects(id=data["role_id"]).first()
        if role is None:
            raise RoleNotExistError
        # 设置的角色，等级大于当前角色
        if self_role.level <= role.level:
            raise NoPermissionError(gettext("邀请的角色等级需要比您低"))
        invitation.role = role
        invitation.save()
        return {"message": gettext("修改成功")}

    @token_required
    @fetch_model(Invitation)
    def patch(self, invitation: Invitation):
        """
        @api {patch} /v1/invitations/<id> 接受/拒绝邀请
        @apiDescription 只有被邀请人才能接受/拒绝邀请
        @apiVersion 1.0.0
        @apiName check_invitation
        @apiGroup JoinProcess
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} id 申请id
        @apiParam {Boolean} allow 是否接受
        @apiParamExample {json} 请求示例
        {
            "allow": true
        }

        @apiUse 204

        @apiUse NeedTokenError
        @apiUse BadTokenError
        @apiUse NoPermissionError
        @apiUse InvitationNotExistError
        """
        data = self.get_json(CheckInvitationSchema())
        if self.current_user != invitation.user:
            raise NoPermissionError
        if data["allow"]:
            invitation.allow()
            return {
                "message": gettext("已接受"),
                "group": invitation.group.to_api(user=self.current_user),
            }
        else:
            invitation.deny()
            return {"message": gettext("已拒绝")}

    @token_required
    @fetch_model(Invitation)
    def delete(self, invitation: Invitation):
        """
        @api {delete} /v1/invitations/<id> 删除邀请
        @apiDescription 只有团体管理人员才能删除邀请
        @apiVersion 1.0.0
        @apiName delete_invitation
        @apiGroup JoinProcess
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} id 邀请id

        @apiUse NeedTokenError
        @apiUse BadTokenError
        @apiUse NoPermissionError
        @apiUse InvitationNotExistError
        """
        # 当前用户没有权限
        if not self.current_user.can(
            invitation.group, invitation.group.permission_cls.INVITE_USER
        ):
            raise NoPermissionError
        self_role = self.current_user.get_role(invitation.group)
        # 用户当前的等级小于或等于将要邀请进来的用户,说明是更高级用户邀请的，当前用户不能编辑
        if self_role.level <= invitation.role.level:
            raise NoPermissionError(gettext("只能删除邀请角色等级比您低的邀请"))
        invitation.delete()
        return {"message": gettext("删除成功")}
