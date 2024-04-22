"""
关于用户个人的API
"""

from flask import request

from app.core.responses import MoePagination
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.models.user import User
from app.models.team import TeamUserRelation
from app.validators import ChangeInfoSchema
from app.validators.auth import (
    ChangeEmailSchema,
    ChangePasswordSchema,
    LoginSchema,
    ResetPasswordSchema,
)
from app.validators.join_process import (
    SearchInvitationSchema,
    SearchRelatedApplicationSchema,
)
from flask_apikit.utils import QueryParser
from flask_babel import gettext
from app.validators.project import SearchUserProjectSchema
from app.models.project import Project
from app.models.application import Application


class MeTokenAPI(MoeAPIView):
    def post(self):
        """
        @api {post} /v1/user/token 创建用户令牌
        @apiVersion 1.0.0
        @apiName get_token
        @apiGroup Me
        @apiUse APIHeader

        @apiParam {String}      email        邮箱
        @apiParam {String}      password     密码
        @apiParam {String}      captcha_info 验证码签名
        @apiParam {String}      captcha      验证码

        @apiParamExample {json} 请求示例
        {
            "email":"123@123.com",
            "password":"123123",
            "captcha_info":"dafkaldjfl2183u21903kljlkjds",
            "captcha":"989989"
        }

        @apiSuccess {String} token
            身份验证token,附加到 `Authorization` Header中,访问需要登录的API
        @apiSuccessExample {json} 返回示例
        {
            "token": "eyJhbGciOiJIUzI...IV3kUw2_MF2zyvfjAxc"
        }

        @apiUse ValidateError
        """
        data = self.get_json(LoginSchema())
        # 计算token
        user = User.by_email(data["email"])
        token = user.generate_token()
        return {"token": token}


class MeInfoAPI(MoeAPIView):
    @token_required
    def get(self):
        """
        @api {get} /v1/user/info 获取自己资料
        @apiVersion 1.0.0
        @apiName get_user_info
        @apiGroup Me
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiUse UserInfoModel
        @apiSuccessExample {json} 返回示例
        {
            "avatar": null,
            "id": "5911930d7e4b036e2df3a910",
            "name": "123123",
            "signature": "這個用戶還沒有簽名"
        }

        @apiUse NeedTokenError
        @apiUse BadTokenError
        """
        return self.current_user.to_api()

    @token_required
    def put(self):
        """
        @api {put} /v1/user/info 修改自己资料
        @apiVersion 1.0.0
        @apiName set_user_info
        @apiGroup Me
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} name 昵称
        @apiParam {String} signature 签名
        @apiParam {String} locale 语言

        @apiUse UserInfoModel

        @apiUse ValidateError
        """
        data = self.get_json(
            ChangeInfoSchema(), context={"old_name": self.current_user.name}
        )
        self.current_user.update(**data)
        self.current_user.reload()
        return {"message": gettext("修改成功"), "user": self.current_user.to_api()}


class MeEmailAPI(MoeAPIView):
    @token_required
    def put(self):
        """
        @api {put} /v1/user/email 修改自己邮箱
        @apiVersion 1.0.0
        @apiName change_email
        @apiGroup Me
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String}      old_email_v_code   原邮箱验证码
        @apiParam {String}      new_email        新邮箱地址
        @apiParam {String}      new_email_v_code   新邮箱验证码
        @apiParamExample {json} 请求示例
        {
            "old_emailVCode":"A21KLk",
            "new_email":"123@123.com",
            "new_email_v_code":"kK12YI"
        }

        @apiUse 204

        @apiUse ValidateError
        """
        data = self.get_json(
            ChangeEmailSchema(), context={"old_email": self.current_user.email}
        )
        self.current_user.email = data["new_email"].lower()
        self.current_user.save()
        return {"message": gettext("修改成功"), "user": self.current_user.to_api()}


class MePasswordAPI(MoeAPIView):
    @token_required
    def put(self):
        """
        @api {put} /v1/user/password 修改自己密码
        @apiVersion 1.0.0
        @apiName change_password
        @apiGroup Me
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String}      old_password   原密码
        @apiParam {String}      new_password   新密码
        @apiParamExample {json} 请求示例
        {
            "old_password":"123123",
            "new_password":"321321"
        }

        @apiUse 204

        @apiUse ValidateError
        """
        data = self.get_json(
            ChangePasswordSchema(), context={"email": self.current_user.email}
        )
        self.current_user.password = data["new_password"]
        self.current_user.save()
        return {"message": gettext("修改成功，请重新登陆")}

    def delete(self):
        """
        @api {delete} /v1/user/password 重置用户密码
        @apiVersion 1.0.0
        @apiName reset_password
        @apiGroup Me
        @apiUse APIHeader

        @apiParam {String}      email   邮箱
        @apiParam {String}      v_code  验证码
        @apiParam {String}      password  新密码
        @apiParamExample {json} 请求示例
        {
            "email":"123@123.com",
            "v_code":"kJhu12",
            "password":"123123"
        }

        @apiUse 204

        @apiUse ValidateError
        """
        data = self.get_json(ResetPasswordSchema())
        user = User.by_email(data["email"])
        user.password = data["password"]
        user.save()
        # 计算token
        token = user.generate_token()
        return {"token": token}


class MeInvitationListAPI(MoeAPIView):
    @token_required
    def get(self):
        """
        @api {get} /v1/user/invitations?status=<status> 获取对自己的邀请
        @apiVersion 1.0.0
        @apiName get_user_invitation
        @apiGroup Me
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} status 邀请状态，可选 "pending"/"deny"/"allow"

        @apiSuccess {Object[]} data 所有邀请
        @apiSuccess {String} data.id 邀请id
        @apiSuccess {Object} data.user 被邀请人信息
        @apiSuccess {String} data.user.id 被邀请人Id
        @apiSuccess {String} data.user.name 被邀请人用户名
        @apiSuccess {Object} data.operator 邀请人信息
        @apiSuccess {String} data.operator.id 邀请人用户Id
        @apiSuccess {String} data.operator.name 邀请人用户名
        @apiSuccess {String} data.create_time 邀请创建时间（Unix时间戳）
        @apiSuccessExample {json} 返回示例
        {
            "data": "待完成"
        }

        @apiUse NeedTokenError
        @apiUse BadTokenError
        """
        data = self.get_query({"status": [QueryParser.int]}, SearchInvitationSchema())
        p = MoePagination()
        objects = self.current_user.invitations(
            status=data["status"], skip=p.skip, limit=p.limit
        )
        return p.set_objects(objects)


class MeRelatedApplicationListAPI(MoeAPIView):
    @token_required
    def get(self):
        """
        @api {get} /v1/user/related-applications?status=<status> 获取自己可以管理的申请
        @apiVersion 1.0.0
        @apiName getMeRelatedApplicationList
        @apiGroup Me
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} status 邀请状态，可选 "pending"/"deny"/"allow"

        @apiSuccess {Object[]} data 所有邀请
        @apiSuccess {String} data.id 邀请id
        @apiSuccess {Object} data.user 被邀请人信息
        @apiSuccess {String} data.user.id 被邀请人Id
        @apiSuccess {String} data.user.name 被邀请人用户名
        @apiSuccess {Object} data.operator 邀请人信息
        @apiSuccess {String} data.operator.id 邀请人用户Id
        @apiSuccess {String} data.operator.name 邀请人用户名
        @apiSuccess {String} data.create_time 邀请创建时间（Unix时间戳）
        @apiSuccessExample {json} 返回示例
        {
            "data": "待完成"
        }

        @apiUse NeedTokenError
        @apiUse BadTokenError
        """
        data = self.get_query(
            {"status": [QueryParser.int]}, SearchRelatedApplicationSchema()
        )
        p = MoePagination()
        objects = Application.get(
            status=data["status"],
            skip=p.skip,
            limit=p.limit,
            related_user_id=self.current_user.id,
        )
        return p.set_objects(objects, func_kwargs={"user": self.current_user})


class MeTeamListAPI(MoeAPIView):
    @token_required
    def get(self):
        """
        @api {get} /v1/user/teams 获取自己的所有团队
        @apiVersion 1.0.0
        @apiName get_user_team
        @apiGroup Me
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """

        # 获取查询参数
        word = request.args.get("word")
        p = MoePagination()
        teams = self.current_user.teams(skip=p.skip, limit=p.limit, word=word)
        # 获取团队用户关系
        relations = TeamUserRelation.objects(group__in=teams, user=self.current_user)
        # 构建字典用于快速匹配
        team_roles_data = {}
        for relation in relations:
            team_roles_data[str(relation.group.id)] = relation.role.to_api()
        # 构建数据
        data = []
        for team in teams:
            team_data = team.to_api()
            team_role_data = team_roles_data.get(str(team.id))
            if team_role_data:
                team_data["role"] = team_role_data
            else:
                team_data["role"] = None
            data.append(team_data)
        return p.set_data(data, count=teams.count())


class MeProjectListAPI(MoeAPIView):
    @token_required
    def get(self):
        """
        # noqa: E501
        @api {get} /v1/user/projects?word=<word> 获取用户的所有项目
        @apiVersion 1.0.0
        @apiName get_team_project
        @apiGroup Me
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {Number} [status] 项目状态，可以传递多个，不传则为所有的，支持以下参数
            - 0  # 进行中的项目
            - 1  # 完成了的项目
            - 2  # 计划完成
            - 3  # 计划删除
        @apiParam {String} [word] 模糊查询的名称

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 获取查询参数
        query = self.get_query(
            {"status": [QueryParser.int]},
            SearchUserProjectSchema(),
        )
        p = MoePagination()
        projects = self.current_user.projects(
            status=query["status"],
            word=query["word"],
            skip=p.skip,
            limit=p.limit,
        )
        data = Project.batch_to_api(projects, self.current_user)
        p.set_data(data, count=projects.count())
        return p
