from flask_babel import gettext

from app.core.responses import MoePagination
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_model, fetch_group
from app.exceptions import NoPermissionError
from app.models.application import Application
from app.validators.join_process import (
    CheckApplicationSchema,
    CreateApplicationSchema,
    SearchApplicationSchema,
)
from flask_apikit.utils import QueryParser


class ApplicationListAPI(MoeAPIView):
    @token_required
    @fetch_group
    def get(self, group):
        """
        @api {get} /v1/<group_type>/<group_id>/applications 获取团体收到的申请
        @apiVersion 1.0.0
        @apiName team_applications
        @apiGroup JoinProcess
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiParam {Number} page 当前的页数
        @apiParam {Number} limit 限制的数量
        @apiParam {Number} [status] 状态,可以使用逗号分割查询多种状态,如status=1,2 ,没有则返回所有状态下的

        @apiUse ApplicationInfoModel
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
        if not self.current_user.can(group, group.permission_cls.CHECK_USER):
            raise NoPermissionError
        data = self.get_query({"status": [QueryParser.int]}, SearchApplicationSchema())
        p = MoePagination()
        objects = group.applications(status=data["status"], skip=p.skip, limit=p.limit)
        return p.set_objects(objects)

    @token_required
    @fetch_group
    def post(self, group):
        """
        @api {post} /v1/<group_type>/<group_id>/applications 申请加入团队
        @apiVersion 1.0.0
        @apiName add_application
        @apiGroup JoinProcess
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} message 申请信息
        @apiParamExample {json} 请求示例
        {
            "message":"快加我"
        }

        @apiParam {String} group_type 团体类型，支持 “team”、“project”
        @apiParam {String} group_id 团队 ID
        @apiSuccess {String} message 提示消息
        @apiSuccess {Dict} group 加入的团体的信息
        @apiSuccessExample {json} 返回示例
        {
            "message": "申请成功",
            "group": {}
        }

        @apiUse ValidateError
        @apiUse GroupTypeNotSupportError
        @apiUse TeamNotExistError
        @apiUse ProjectNotExistError
        """
        data = self.get_json(CreateApplicationSchema())
        return self.current_user.apply(group, data["message"])


class ApplicationAPI(MoeAPIView):
    @token_required
    @fetch_model(Application)
    def patch(self, application: Application):
        """
        @api {patch} /v1/applications/<id> 接受/拒绝申请
        @apiDescription 只有团体管理员可以接受/拒绝申请
        @apiVersion 1.0.0
        @apiName check_applications
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
        @apiUse ApplicationNotExistError
        """
        data = self.get_json(CheckApplicationSchema())
        if not self.current_user.can(
            application.group, application.group.permission_cls.CHECK_USER
        ):
            raise NoPermissionError
        if data["allow"]:
            application.allow(operator=self.current_user)
            application.reload()
            return {
                "message": gettext("已接受"),
                "application": application.to_api(user=self.current_user),
            }
        else:
            application.deny(operator=self.current_user)
            application.reload()
            return {
                "message": gettext("已拒绝"),
                "application": application.to_api(user=self.current_user),
            }

    @token_required
    @fetch_model(Application)
    def delete(self, application: Application):
        """
        @api {delete} /v1/applications/<id> 删除申请
        @apiDescription 只有自己可以删除自己的申请
        @apiVersion 1.0.0
        @apiName delete_applications
        @apiGroup JoinProcess
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} id 申请id

        @apiUse NeedTokenError
        @apiUse BadTokenError
        @apiUse NoPermissionError
        @apiUse ApplicationNotExistError
        """
        # 已完成的申请不能编辑
        application.can_change_status()
        # 只有自己才能删除申请
        if self.current_user != application.user:
            raise NoPermissionError(gettext("只有申请人可以删除申请"))
        application.delete()
        return {"message": gettext("删除成功")}
