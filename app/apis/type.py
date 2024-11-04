from app.constants.locale import Locale
from app.core.views import MoeAPIView
from app.models.team import Team
from app.exceptions.base import RequestDataWrongError
from app.models.project import Project
from flask_apikit.utils.query import QueryParser


class TypeAPI(MoeAPIView):
    """
    @api {post} /v1/types/locale 获取语言
    @apiVersion 1.0.0
    @apiName type_local
    @apiGroup Type
    @apiUse APIHeader
    """

    """
    @api {post} /v1/types/permission 获取权限选项
    @apiVersion 1.0.0
    @apiName type_permission
    @apiGroup Type
    @apiUse APIHeader
    @apiParam {String} group_type 团体类型（team/project）
    """
    """
    @api {post} /v1/types/allow-apply-type 获取谁允许申请选项
    @apiVersion 1.0.0
    @apiName type_allow_apply_type
    @apiGroup Type
    @apiUse APIHeader
    @apiParam {String} group_type 团体类型（team/project）
    """
    """
    @api {post} /v1/types/application-check-type 获取如何处理申请选项
    @apiVersion 1.0.0
    @apiName type_application_check_type
    @apiGroup Type
    @apiUse APIHeader
    @apiParam {String} group_type 团体类型（team/project）
    """
    """
    @api {post} /v1/types/system-role 获取系统角色
    @apiVersion 1.0.0
    @apiName type_system_role
    @apiGroup Type
    @apiUse APIHeader
    @apiParam {String} group_type 团体类型（team/project）
    """

    def get(self, type_name):
        """获取各种类型"""
        # TODO: 将locale移动到独立的API中
        if type_name == "locale":
            return Locale.to_api()
        # 区分 team 或 project 类型的
        else:
            query = self.get_query({"with_creator": QueryParser.bool})
            if query.get("group_type") not in ["team", "project"]:
                raise RequestDataWrongError(
                    message="'group_type' not in ['team', 'project']"
                )
            # 获取相应的团体类
            if query["group_type"] == "team":
                group_cls = Team
            else:
                group_cls = Project
            if type_name == "permission":
                # 团队权限
                return group_cls.permission_cls.to_api()
            elif type_name == "allow-apply-type":
                # 团队申请类型
                return group_cls.allow_apply_type_cls.to_api()
            elif type_name == "application-check-type":
                # 团队申请审核类型
                return group_cls.application_check_type_cls.to_api()
            elif type_name == "system-role":
                with_creator = query.get("with_creator", False)
                # 团队系统角色
                return [
                    role.to_api()
                    for role in group_cls.role_cls.system_roles(
                        without_creator=not with_creator
                    )
                ]
