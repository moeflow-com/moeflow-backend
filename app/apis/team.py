import datetime
import zipfile
from marshmallow import ValidationError
from app.constants.output import OutputTypes
from app.exceptions.auth import UserNotExistError
from app.exceptions.project import ProjectNotExistError
from typing import List
from app.exceptions.team import OnlyAllowAdminCreateTeamError
from app.models.output import Output
from app.models.site_setting import SiteSetting
from app.models.user import User
from app.models.language import Language
from flask import json, request, current_app
from flask_babel import gettext

from app.core.responses import MoePagination
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_model
from app.exceptions import NoPermissionError, RequestDataEmptyError
from app.models.project import Project
from app.models.team import Team, TeamPermission
from app.constants.project import ProjectStatus
from app.tasks.output_team_projects import output_team_projects
from app.validators.project import (
    CreateProjectSchema,
    ImportProjectSchema,
    SearchTeamProjectSchema,
    TeamInsightProjectListSchema,
    TeamInsightUserListSchema,
)
from app.validators.team import CreateTeamSchema, EditTeamSchema
from flask_apikit.utils import QueryParser
from app.models.project import ProjectRole, ProjectSet, ProjectUserRelation
from app.validators.project import ProjectSetsSchema
from flask_apikit.exceptions import ValidateError


def getLanguageByCode(code):
    lang = Language.by_code(code)
    return lang.id


class TeamListAPI(MoeAPIView):
    @token_required
    def get(self):
        """
        @api {get} /v1/teams?word=<word> 获取团队列表
        @apiVersion 1.0.0
        @apiName get_team_list
        @apiGroup Team
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam word 搜索关键词

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 暂时不开放此接口，只能通过 ID 加入申请某个团队
        if not current_app.config["TESTING"]:
            return
        query = self.get_query()
        # word 不可为空
        if "word" not in query or query["word"] == "":
            raise RequestDataEmptyError
        p = MoePagination()
        objects = (
            Team.objects(name__icontains=query["word"]).skip(p.skip).limit(p.limit)
        )
        # 检测自己是否加入了这个团队，并返回 joined 值
        data = []
        my_teams = self.current_user.teams()
        for o in objects:
            item = o.to_api()
            if o in my_teams:
                item["joined"] = True
            else:
                item["joined"] = False
            data.append(item)
        p.set_data(data=data, count=objects.count())
        return p

    @token_required
    def post(self):
        """
        @api {post} /v1/teams 新建团队
        @apiVersion 1.0.0
        @apiName post_team_list
        @apiGroup Team
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} name 团队名
        @apiParam {String} intro 团队介绍
        @apiParam {String} allow_apply_type 允许谁申请加入（通过/types接口获取）
        @apiParam {String} application_check_type 如何处理加入申请（通过/types接口获取）
        @apiParam {String} default_role 加入后默认角色（通过/types接口获取）
        @apiParamExample {json} 请求示例
        {
            "name":"123123"
        }

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "创建成功",
            "team": {}
        }

        @apiUse ValidateError
        """
        if (
            SiteSetting.get().only_allow_admin_create_team
            and not self.current_user.admin
        ):
            raise OnlyAllowAdminCreateTeamError
        # 处理请求数据
        data = self.get_json(CreateTeamSchema())
        # 创建团队
        team = Team.create(
            data["name"],
            creator=self.current_user,
            default_role=data["default_role"],
            allow_apply_type=data["allow_apply_type"],
            application_check_type=data["application_check_type"],
            intro=data["intro"],
        )
        return {
            "message": gettext("创建成功"),
            "team": team.to_api(user=self.current_user),
        }


class TeamAPI(MoeAPIView):
    @token_required
    @fetch_model(Team)
    def get(self, team):
        """
        @api {get} /v1/teams/<team_id> 获取某个团队的信息
        @apiVersion 1.0.0
        @apiName get_team
        @apiGroup Team
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(team, TeamPermission.ACCESS):
            raise NoPermissionError
        return team.to_api(user=self.current_user)

    @token_required
    @fetch_model(Team)
    def put(self, team):
        """
        @api {put} /v1/teams/<team_id> 修改团队
        @apiVersion 1.0.0
        @apiName put_team
        @apiGroup Team
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} team_id 团队id
        @apiParamExample {json} 请求示例
        {
            "name":"123123"
        }

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "创建成功"
        }

        @apiUse ValidateError
        """
        # 检查是否有访问权限
        if not self.current_user.can(team, TeamPermission.CHANGE):
            raise NoPermissionError
        data = self.get_json(EditTeamSchema(), context={"team": team})
        if data:
            team.update(**data)
            team.reload()
            return {
                "message": gettext("修改成功"),
                "team": team.to_api(user=self.current_user),
            }
        else:
            raise RequestDataEmptyError

    @token_required
    @fetch_model(Team)
    def delete(self, team):
        """
        @api {delete} /v1/teams/<team_id> 解散团队
        @apiVersion 1.0.0
        @apiName delete_team
        @apiGroup Team
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "解散成功"
        }

        @apiUse ValidateError
        """
        # 检查是否有访问权限
        if not self.current_user.can(team, TeamPermission.DELETE):
            raise NoPermissionError
        # 检查是否有未完结的项目
        if team.projects(status=ProjectStatus.WORKING).count() > 0:
            raise NoPermissionError(gettext("此团队含有未完结的项目，不能解散（请先完结或者转移项目）"))
        team.clear()
        return {"message": gettext("解散成功")}


class TeamProjectListAPI(MoeAPIView):
    @token_required
    @fetch_model(Team)
    def get(self, team):
        """
        # noqa: E501
        @api {get} /v1/teams/<team_id>/projects?project_set=<project_set>&word=<word> 获取团队的所有项目
        @apiVersion 1.0.0
        @apiName get_team_project
        @apiGroup Team
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} team_id 团队id

        @apiParam {Number} [status] 项目状态，可以传递多个，不传则为所有的，支持以下参数
            - 0  # 进行中的项目
            - 1  # 完成了的项目
            - 2  # 计划完成
            - 3  # 计划删除
        @apiParam {String} [project_set] 所在项目集id
        @apiParam {String} [word] 模糊查询的名称

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查是否有访问团队权限
        if not self.current_user.can(team, TeamPermission.ACCESS):
            raise NoPermissionError
        # 获取查询参数
        query = self.get_query(
            {"status": [QueryParser.int]},
            SearchTeamProjectSchema(),
            context={"team": team},
        )
        p = MoePagination()
        projects = team.projects(
            project_set=query["project_set"],
            status=query["status"],
            word=query["word"],
            skip=p.skip,
            limit=p.limit,
        )
        data = Project.batch_to_api(
            projects, self.current_user, inherit_admin_team=team
        )
        p.set_data(data, count=projects.count())
        return p

    @token_required
    @fetch_model(Team)
    def post(self, team):
        """
        @api {post} /v1/teams/<team_id>/projects 新建项目
        @apiVersion 1.0.0
        @apiName add_project
        @apiGroup Project
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} name 项目名
        @apiParamExample {json} 请求示例
        {
            "name":"123123",
            "intro": "",
            "allow_apply_type": 2,
            "application_check_type": 1,
            "default_role": "Object ID",
            "project_set": "Object ID"
        }

        @apiSuccess {String} msg 提示消息
        @apiSuccessExample {json} 返回示例
        {
            "message": "创建成功",
            "project": {}
        }

        @apiUse ValidateError
        """
        # 检查用户权限
        if not self.current_user.can(team, TeamPermission.CREATE_PROJECT):
            raise NoPermissionError(gettext("您没有权限在这个团队创建项目"))
        # 处理请求数据
        data = self.get_json(CreateProjectSchema(), context={"team": team})
        # 创建项目
        project = Project.create(
            name=data["name"],
            team=team,
            project_set=data["project_set"],
            creator=self.current_user,
            default_role=data["default_role"],
            allow_apply_type=data["allow_apply_type"],
            application_check_type=data["application_check_type"],
            intro=data["intro"],
            source_language=data["source_language"],
            target_languages=data["target_languages"],
            labelplus_txt=data["labelplus_txt"],
        )
        return {
            "message": gettext("创建成功"),
            "project": project.to_api(user=self.current_user),
        }


class TeamProjectOutputListAPI(MoeAPIView):
    @token_required
    @fetch_model(Team)
    def post(self, team: Team):
        if not self.current_user.can(team, TeamPermission.AUTO_BECOME_PROJECT_ADMIN):
            raise NoPermissionError
        output_team_projects(str(team.id), str(self.current_user.id))
        return {"message": gettext("创建导出任务成功")}


class TeamProjectImportAPI(MoeAPIView):
    @token_required
    @fetch_model(Team)
    @fetch_model(ProjectSet)
    def post(self, team, project_set):
        # 检查用户权限
        if not self.current_user.can(team, TeamPermission.CREATE_PROJECT):
            raise NoPermissionError(gettext("您没有权限在这个团队创建项目"))
        project_json_file = request.files["project"]
        project_json_data = json.load(project_json_file)
        project_json_data["project_set"] = str(project_set.id)
        project_json_data["default_role"] = str(
            ProjectRole.by_system_code(project_json_data["default_role"]).id
        )
        labelplus_file = request.files["labelplus"]
        labelplus_txt = labelplus_file.read().decode("utf-8")

        # 处理请求数据
        schema = ImportProjectSchema()
        schema.context = {"team": team}
        try:
            data = schema.load(project_json_data)
        except ValidationError as e:
            # 合并多个验证器对于同一字段的相同错误
            for key in e.messages.keys():
                e.messages[key] = list(set(e.messages[key]))
            raise ValidateError(e.messages, replace=True)
        # 创建项目
        project = Project.create(
            name=data["name"],
            team=team,
            project_set=data["project_set"],
            creator=self.current_user,
            default_role=data["default_role"],
            allow_apply_type=data["allow_apply_type"],
            application_check_type=data["application_check_type"],
            intro=data["intro"],
            source_language=data["source_language"],
            target_languages=[data["output_language"]],
            labelplus_txt=labelplus_txt,
        )
        return {
            "message": gettext("创建成功"),
            "project": project.to_api(user=self.current_user),
        }


class TeamProjectSetListAPI(MoeAPIView):
    @token_required
    @fetch_model(Team)
    def get(self, team):
        """
        @api {get} /v1/teams/<team_id>/project-sets?word=<word> 获取团队的所有项目集
        @apiVersion 1.0.0
        @apiName get_team_project_sets
        @apiGroup Team
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} team_id 团队id
        @apiParam {String} [word] 模糊查询的名称

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查是否有访问团队权限
        if not self.current_user.can(team, TeamPermission.ACCESS):
            raise NoPermissionError
        # 获取查询参数
        word = request.args.get("word")
        # 分页
        p = MoePagination()
        objects = team.project_sets(skip=p.skip, limit=p.limit, word=word)
        return p.set_objects(objects)

    @token_required
    @fetch_model(Team)
    def post(self, team):
        """
        @api {post} /v1/teams/<team_id>/project-sets 创建项目集
        @apiVersion 1.0.0
        @apiName add_team_project_set
        @apiGroup ProjectSet
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} team_id 团队id
        @apiParamExample {json} 请求示例
        {
           "name": "name"
        }

        @apiSuccessExample {json} 返回示例
        {
            "message": "创建成功",
            "project_set": {}
        }
        """
        # 检查是否有创建项目权限
        if not self.current_user.can(team, TeamPermission.CREATE_PROJECT_SET):
            raise NoPermissionError(gettext("您没有权限在这个团队创建项目集"))
        # 获取data
        data = self.get_json(ProjectSetsSchema())
        project_set = ProjectSet.create(name=data["name"], team=team)
        return {"message": gettext("创建成功"), "project_set": project_set.to_api()}


def get_insight_user_projects_data(
    user: User, team_projects: List[Project], /, *, skip=0, limit=5
):
    relations = (
        ProjectUserRelation.objects(user=user, group__in=team_projects)
        .skip(skip)
        .limit(limit)
    )
    user_projects_data = {
        "projects": [],
        "count": relations.count(),
    }
    for relation in relations:
        user_projects_data["projects"].append(
            {**relation.group.to_api(with_team=False), "role": relation.role.to_api()}
        )
    return user_projects_data


class TeamInsightUserListAPI(MoeAPIView):
    @token_required
    @fetch_model(Team)
    def get(self, team: Team):
        if not self.current_user.can(team, TeamPermission.INSIGHT):
            raise NoPermissionError(gettext("您没有权限查看本团队项目统计"))
        query = self.get_query(None, TeamInsightUserListSchema())
        p = MoePagination(max_limit=10)
        users = team.users(
            skip=p.skip, limit=p.limit, word=query["word"]
        ).no_dereference()
        team_projects = team.projects(status=ProjectStatus.WORKING).no_dereference()
        data = []
        for user in users:
            user_projects_data = get_insight_user_projects_data(user, team_projects)
            data.append({**user_projects_data, "user": user.to_api()})
        return p.set_data(data=data, count=users.count())


class TeamInsightUserProjectListAPI(MoeAPIView):
    @token_required
    @fetch_model(User)
    @fetch_model(Team)
    def get(self, team: Team, user: User):
        if not self.current_user.can(team, TeamPermission.INSIGHT):
            raise NoPermissionError(gettext("您没有权限查看本团队项目统计"))
        if user.get_relation(team) is None:
            raise UserNotExistError
        p = MoePagination()
        team_projects = team.projects(status=ProjectStatus.WORKING).no_dereference()
        user_projects_data = get_insight_user_projects_data(
            user, team_projects, skip=p.skip, limit=p.limit
        )
        return p.set_data(
            data=user_projects_data["projects"], count=user_projects_data["count"]
        )


def get_insight_project_users_data(project: Project, /, *, skip=0, limit=5):
    relations = ProjectUserRelation.objects(group=project).skip(skip).limit(limit)
    project_users_data = {
        "users": [],
        "count": relations.count(),
    }
    for relation in relations:
        project_users_data["users"].append(
            {**relation.user.to_api(), "role": relation.role.to_api()}
        )
    return project_users_data


class TeamInsightProjectListAPI(MoeAPIView):
    @token_required
    @fetch_model(Team)
    def get(self, team: Team):
        if not self.current_user.can(team, TeamPermission.INSIGHT):
            raise NoPermissionError(gettext("您没有权限查看本团队项目统计"))
        query = self.get_query(None, TeamInsightProjectListSchema())
        p = MoePagination(max_limit=10)
        projects = team.projects(
            skip=p.skip, limit=p.limit, status=ProjectStatus.WORKING, word=query["word"]
        )
        data = []
        for project in projects:
            project_users_data = get_insight_project_users_data(project)
            project_data = {
                **project_users_data,
                "project": project.to_api(with_team=False),
            }
            if self.current_user.can(team, TeamPermission.AUTO_BECOME_PROJECT_ADMIN):
                project_data["outputs"] = [
                    output.to_api() for output in project.outputs()
                ]
            data.append(project_data)
        return p.set_data(data=data, count=projects.count())


class TeamInsightProjectUserListAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    @fetch_model(Team)
    def get(self, team: Team, project: Project):
        if not self.current_user.can(team, TeamPermission.INSIGHT):
            raise NoPermissionError(gettext("您没有权限查看本团队项目统计"))
        if project.team != team:
            raise ProjectNotExistError
        p = MoePagination()
        project_users_data = get_insight_project_users_data(
            project, skip=p.skip, limit=p.limit
        )
        return p.set_data(
            data=project_users_data["users"], count=project_users_data["count"]
        )
