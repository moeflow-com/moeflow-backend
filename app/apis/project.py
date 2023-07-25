from app.constants.file import FileType, ParseStatus
from app.constants.output import OutputTypes
from app.tasks.ocr import ocr
from app.models.team import TeamPermission
import datetime
from app.exceptions.project import ProjectFinishedError, TargetNotExistError
from flask import current_app
from flask_babel import gettext

from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_model
from app.exceptions import (
    NoPermissionError,
    ProjectNotFinishedError,
    RequestDataEmptyError,
)
from app.models.project import Project, ProjectPermission
from app.models.target import Target
from app.models.output import Output
from app.constants.project import ProjectStatus
from app.validators.project import (
    EditProjectSchema,
    CreateProjectTargetSchema,
    CreateOutputSchema,
)
from app.core.responses import MoePagination
from app.tasks.output_project import output_project
from app.exceptions.output import OutputTooFastError


class ProjectAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    def get(self, project: Project):
        """
        @api {get} /v1/projects/<project_id> 获取项目信息
        @apiVersion 1.0.0
        @apiName getProjectAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查用户权限
        if not self.current_user.can(
            project, ProjectPermission.ACCESS
        ) and not self.current_user.can(project.team, TeamPermission.ACCESS):
            raise NoPermissionError(gettext("您没有此项目的访问权限"))
        return project.to_api(user=self.current_user)

    @token_required
    @fetch_model(Project)
    def put(self, project: Project):
        """
        @api {put} /v1/projects/<project_id> 修改项目
        @apiVersion 1.0.0
        @apiName putProjectAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} project_id 项目id
        @apiParamExample {json} 请求示例
        {
            "name":"123123"
        }

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "修改成功"
        }

        @apiUse ValidateError
        """
        # 检查项目是否已完成
        if project.status != ProjectStatus.WORKING:
            raise ProjectFinishedError
        # 检查是否有访问权限
        if not self.current_user.can(project, ProjectPermission.CHANGE):
            raise NoPermissionError
        data = self.get_json(EditProjectSchema(), context={"project": project})
        if not data:
            raise RequestDataEmptyError
        project.update(**data)
        project.reload()
        return {
            "message": gettext("修改成功"),
            "project": project.to_api(user=self.current_user),
        }

    @token_required
    @fetch_model(Project)
    def delete(self, project: Project):
        """
        @api {put} /v1/projects/<project_id> 完结项目
        @apiVersion 1.0.0
        @apiName deleteProjectAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} project_id 项目id

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "完结项目成功"
        }

        @apiUse ValidateError
        """
        # 检查项目是否已完成
        if project.status != ProjectStatus.WORKING:
            raise ProjectFinishedError
        # 检查权限
        if not self.current_user.can(project, ProjectPermission.FINISH):
            raise NoPermissionError
        project.finish()
        return {"message": gettext("完结项目成功")}


class ProjectResumeAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    def post(self, project: Project):
        """
        @api {post} /v1/projects/<project_id>/resume 恢复已完结的项目
        @apiVersion 1.0.0
        @apiName postProjectResumeAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "取消成功"
        }

        @apiUse ValidateError
        """
        # 检查项目是否已完成
        if project.status != ProjectStatus.FINISHED:
            raise ProjectNotFinishedError(gettext("操作无效"))
        # 检查是否有权限
        if not self.current_user.can(project, ProjectPermission.FINISH):
            raise NoPermissionError
        project.resume()
        return {"message": gettext("恢复项目成功")}


class ProjectTargetListAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    def get(self, project: Project):
        """
        @api {get} /v1/projects/<project_id>/targets 获取翻译目标列表
        @apiVersion 1.0.0
        @apiName getProjectTargetListAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(project, ProjectPermission.ACCESS):
            raise NoPermissionError
        # query = self.get_query({}, TargetSearchSchema())
        # TODO: 支持通过名字筛选语言，不过因为查询的名字是i18n的，所以比如用日文搜索English就搜不到
        p = MoePagination(max_limit=0)
        objects = project.targets().skip(p.skip).limit(p.limit)
        return p.set_objects(objects)

    @token_required
    @fetch_model(Project)
    def post(self, project: Project):
        """
        @api {get} /v1/projects/<project_id>/targets 新增翻译目标
        @apiVersion 1.0.0
        @apiName postProjectTargetListAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(project, ProjectPermission.ADD_TARGET):
            raise NoPermissionError
        data = self.get_json(CreateProjectTargetSchema())
        target = Target.create(project=project, language=data["language"])
        return {"message": gettext("添加目标语言成功"), "target": target.to_api()}


class ProjectOutputListAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    def post(self, project: Project):
        if not self.current_user.can(project, ProjectPermission.OUTPUT_TRA):
            raise NoPermissionError
        outputs_json = []
        for target in project.targets():
            # 等待一定时间后允许再次导出
            last_output = target.outputs().first()
            if last_output and (
                datetime.datetime.utcnow() - last_output.create_time
                < datetime.timedelta(
                    seconds=current_app.config.get("OUTPUT_WAIT_SECONDS", 60 * 5)
                )
            ):
                continue
            # 删除三个导出之前的
            old_targets = target.outputs().skip(2)
            Output.delete_real_files(old_targets)
            old_targets.delete()
            # 创建新target
            output = Output.create(
                project=project,
                target=target,
                user=self.current_user,
                type=OutputTypes.ALL,
            )
            output_project(str(output.id))
            outputs_json.append(output.to_api())
        return outputs_json


class ProjectTargetOutputListAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    @fetch_model(Target)
    def get(self, project: Project, target: Target):
        """
        @api {get} /v1/projects/<project_id>/targets/<target_id>/outputs 获取项目导出
        @apiVersion 1.0.0
        @apiName getProjectLabelplusAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {string} target 翻译目标

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(project, ProjectPermission.OUTPUT_TRA):
            raise NoPermissionError
        if target.project != project:
            raise TargetNotExistError
        return [output.to_api() for output in target.outputs()]

    @token_required
    @fetch_model(Project)
    @fetch_model(Target)
    def post(self, project: Project, target: Target):
        """
        @api {post} /v1/projects/<project_id>/targets/<target_id>/outputs 新增项目导出
        @apiVersion 1.0.0
        @apiName postProjectLabelplusAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {string} target 翻译目标

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(project, ProjectPermission.OUTPUT_TRA):
            raise NoPermissionError
        if target.project != project:
            raise TargetNotExistError
        # 等待一定时间后允许再次导出
        last_output = target.outputs().first()
        if last_output and (
            datetime.datetime.utcnow() - last_output.create_time
            < datetime.timedelta(
                seconds=current_app.config.get("OUTPUT_WAIT_SECONDS", 60 * 5)
            )
        ):
            raise OutputTooFastError
        data = self.get_json(CreateOutputSchema())
        # 删除三个导出之前的
        old_targets = target.outputs().skip(2)
        Output.delete_real_files(old_targets)
        old_targets.delete()
        # 创建新target
        output = Output.create(
            project=project,
            target=target,
            user=self.current_user,
            type=data["type"],
            file_ids_include=data["file_ids_include"],
            file_ids_exclude=data["file_ids_exclude"],
        )
        output_project(str(output.id))
        return output.to_api()


# 暂未启用此接口
class ProjectLabelplusAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    @fetch_model(Target)
    def get(self, project: Project, target: Target):
        """
        @api {get} /v1/projects/<project_id>/targets/<target_id>/labelplus
            获取labelplus翻译内容
        @apiVersion 1.0.0
        @apiName getProjectLabelplusAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {string} target 翻译目标

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(project, ProjectPermission.OUTPUT_TRA):
            raise NoPermissionError
        if target.project != project:
            raise TargetNotExistError
        return project.to_labelplus(target=target)


class ProjectOCRAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    def post(self, project: Project):
        """
        @api {post} /v1/projects/<project_id>/ocr 为项目 OCR
        @apiVersion 1.0.0
        @apiName postProjectOCRAPI
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {Project} project 项目

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查用户权限
        if not self.current_user.can(project.team, TeamPermission.USE_OCR_QUOTA):
            raise NoPermissionError(gettext("您没有此项目所在团队使用自动标记限额的权限"))
        if not project.source_language.g_ocr_code:
            raise NoPermissionError(gettext("源语言不支持自动标记"))
        if project.ocring:
            raise NoPermissionError(gettext("自动标记进行中"))
        images = project.files(type_only=FileType.IMAGE).filter(
            parse_status__in=[ParseStatus.NOT_START, ParseStatus.PARSE_FAILED]
        )
        if images.count() == 0:
            raise NoPermissionError(gettext("未发现需要标记的图片"))
        if project.team.ocr_quota_left < images.count():
            raise NoPermissionError(gettext("团队限额不足"))
        images.update(parse_status=ParseStatus.QUEUING)
        ocr("project", str(project.id))
        return {"message": gettext("已开始自动标记")}


# TODO： 准备删掉这个 api
class ProjectDeletePlanAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    def post(self, project: Project):
        """
        @api {post} /v1/projects/<project_id>/delete-plan 创建销毁计划
        @apiVersion 1.0.0
        @apiName project_create_delete_plan
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "销毁计划创建成功"
        }

        @apiUse ValidateError
        """
        if not current_app.config["TESTING"]:
            return
        # 检查权限
        if not self.current_user.can(project, ProjectPermission.DELETE):
            raise NoPermissionError
        project.plan_delete()
        return {"message": gettext("销毁计划创建成功")}

    @token_required
    @fetch_model(Project)
    def delete(self, project: Project):
        """
        @api {delete} /v1/projects/<project_id>/delete-plan 取消销毁计划
        @apiVersion 1.0.0
        @apiName project_delete_delete_plan
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "销毁计划取消成功"
        }

        @apiUse ValidateError
        """
        if not current_app.config["TESTING"]:
            return
        # 检查权限
        if not self.current_user.can(project, ProjectPermission.DELETE):
            raise NoPermissionError
        project.cancel_delete_plan()
        return {"message": gettext("销毁计划取消成功")}


# TODO：准备删掉这个 api
class ProjectFinishPlanAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    def post(self, project: Project):
        """
        @api {post} /v1/projects/<project_id>/finish-plan 创建完结计划
        @apiVersion 1.0.0
        @apiName project_create_finish_plan
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "完结计划创建成功"
        }

        @apiUse ValidateError
        """
        if not current_app.config["TESTING"]:
            return
        # 检查权限
        if not self.current_user.can(project, ProjectPermission.FINISH):
            raise NoPermissionError
        project.plan_finish()
        return {"message": gettext("完结计划创建成功")}

    @token_required
    @fetch_model(Project)
    def delete(self, project: Project):
        """
        @api {delete} /v1/projects/<project_id>/finish-plan 取消完结计划
        @apiVersion 1.0.0
        @apiName project_delete_finish_plan
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "完结计划取消成功"
        }

        @apiUse ValidateError
        """
        if not current_app.config["TESTING"]:
            return
        # 检查权限
        if not self.current_user.can(project, ProjectPermission.FINISH):
            raise NoPermissionError
        project.cancel_finish_plan()
        return {"message": gettext("完结计划取消成功")}
