from flask_babel import gettext

from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_model
from app.exceptions import NoPermissionError
from app.models.project import ProjectSet
from app.models.team import TeamPermission
from app.validators.project import ProjectSetsSchema


class ProjectSetAPI(MoeAPIView):
    @token_required
    @fetch_model(ProjectSet)
    def get(self, project_set):
        """
        @api {get} /v1/project-sets/<project_set_id> 获取项目集
        @apiVersion 1.0.0
        @apiName get_project_set
        @apiGroup ProjectSet
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} team_id 团队id
        @apiParam {String} [word] 模糊查询的名称

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查是否有访问团队权限
        if not self.current_user.can(project_set.team, TeamPermission.ACCESS):
            raise NoPermissionError
        return project_set.to_api()

    @token_required
    @fetch_model(ProjectSet)
    def put(self, project_set):
        """
        @api {put} /v1/project-sets/<project_set_id> 修改项目集
        @apiVersion 1.0.0
        @apiName edit_team_project_set
        @apiGroup ProjectSet
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} project_set_id 项目集id
        @apiParamExample {json} 请求示例
        {
           "name": "name"
        }

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查是否有权限
        if not self.current_user.can(
            project_set.team, TeamPermission.CHANGE_PROJECT_SET
        ):
            raise NoPermissionError
        # 默认项目集不能编辑
        if project_set.default:
            raise NoPermissionError(gettext("默认项目集不能进行设置"))
        # 获取data
        data = self.get_json(ProjectSetsSchema())
        project_set.name = data["name"]
        project_set.save()
        return {"message": gettext("修改成功"), "project_set": project_set.to_api()}

    @token_required
    @fetch_model(ProjectSet)
    def delete(self, project_set):
        """
        @api {delete} /v1/project-sets/<project_set_id> 删除项目集
        @apiDescription
            此时所有项目将被移动到未归类项目，需要给用户一个确认删除提示，如“删除后此项目集的所有内容将移动到‘未分类项目’中”
        @apiVersion 1.0.0
        @apiName delete_team_project_set
        @apiGroup ProjectSet
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} project_set_id 项目集id

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查是否有权限
        if not self.current_user.can(
            project_set.team, TeamPermission.DELETE_PROJECT_SET
        ):
            raise NoPermissionError
        # 默认项目集不能删除
        if project_set.default:
            raise NoPermissionError(gettext("默认项目集不能删除"))
        project_set.clear()
        return {"message": gettext("删除成功")}
