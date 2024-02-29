from app.exceptions.project import ProjectFinishedError
from flask import request
from flask_babel import gettext

from app.core.responses import MoePagination
from app.core.views import MoeAPIView
from app.decorators.auth import admin_required, token_required
from app.decorators.url import fetch_model
from app.exceptions import NoPermissionError, UploadFileNotFoundError
from app.models.file import File, FileTargetCache
from app.models.project import Project, ProjectPermission
from app.models.team import TeamPermission
from app.constants.project import ProjectStatus
from app.constants.file import FileNotExistReason, FileType
from app.validators.file import (
    AdminFileSearchSchema,
    FileSearchSchema,
    FileUploadSchema,
    FileGetSchema,
)
from app.constants.file import FileSafeStatus
from flask_apikit.exceptions import ValidateError
from flask_apikit.utils import QueryParser


class ProjectFileListAPI(MoeAPIView):
    @token_required
    @fetch_model(Project)
    def get(self, project: Project):
        """
        @api {get} /v1/projects/<project_id>/files 获取项目下的文件
        @apiVersion 1.0.0
        @apiName getProjectFileListAPI
        @apiGroup File
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {Number} [parent_id] 父级文件夹id，留空则为根目录
        @apiParam {Boolean}l [only_folder] 只查询文件夹，默认为false
        @apiParam {Boolean}l [only_file] 只查询文件，默认为false
        @apiParam {Boolean}l [target] 翻译目标，有则提供关于其的翻译数量

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查项目是否已完成
        if project.status != ProjectStatus.WORKING:
            raise ProjectFinishedError
        # 检查用户权限
        # TODO: 当实现原图保护时，为团队用户显示有水印的图片。
        # 禁止未加入团队的用户直接获得图片 URL 和 COVER_URL（这两个都可以直接访问原图）。
        if not self.current_user.can(
            project, ProjectPermission.ACCESS
        ) and not self.current_user.can(project.team, TeamPermission.ACCESS):
            raise NoPermissionError(gettext("您没有此项目的访问权限"))
        query = self.get_query(
            {
                "order_by": [],
                "only_folder": QueryParser.bool,
                "only_file": QueryParser.bool,
            },
            FileSearchSchema(),
        )
        # 只搜索文件夹/文件
        other_query = {}
        # 如果同时使用only_folder和only_file报错
        if query["only_folder"] and query["only_file"]:
            raise ValidateError("can not use `only_file` and `only_folder` at one time")
        if query["only_folder"]:
            other_query = {**other_query, "type_only": FileType.FOLDER}
        if query["only_file"]:
            other_query = {**other_query, "type_exclude": FileType.FOLDER}
        # 进行搜索
        p = MoePagination()
        files = project.files(
            skip=p.skip,
            limit=p.limit,
            parent=query["parent_id"],
            order_by=query["order_by"],
            word=query["word"],
            **other_query,
        )
        data = [file.to_api() for file in files]
        if query["target"]:
            target = project.target_by_id(query["target"])
            file_target_caches = FileTargetCache.objects(
                file__in=files, target=target
            ).no_dereference()
            file_target_caches_map = {
                str(cache.file.id): cache.to_api() for cache in file_target_caches
            }
            for item in data:
                item["file_target_cache"] = file_target_caches_map[item["id"]]
        return p.set_data(data=data, count=files.count())

    @token_required
    @fetch_model(Project)
    def post(self, project: Project):
        """
        @api {post} /v1/projects/<project_id>/files 上传文件
        @apiVersion 1.0.0
        @apiName postProjectFileListAPI
        @apiGroup File
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {File} file 文件

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查项目是否已完成
        if project.status != ProjectStatus.WORKING:
            raise ProjectFinishedError
        # 检查用户权限
        if not self.current_user.can(project, ProjectPermission.ADD_FILE):
            raise NoPermissionError(gettext("您没有此项目的上传文件权限"))
        # 上传
        real_file = request.files.get("file")
        if not real_file:
            raise UploadFileNotFoundError
        data = self.verify_data(request.form, FileUploadSchema())
        # 检查是否有同名文件
        old_file: File = project.get_files(
            name=real_file.filename, parent=data["parent_id"]
        ).first()
        file: File = project.upload(
            real_file.filename, real_file, parent=data["parent_id"]
        )
        data = file.to_api()
        data["upload_overwrite"] = old_file is not None
        return data


class FileAPI(MoeAPIView):
    @token_required
    @fetch_model(File)
    def get(self, file: File):
        """
        @api {get} /v1/files/<file_id> 获取文件信息
        @apiVersion 1.0.0
        @apiName getFileAPI
        @apiGroup File
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {Boolean}l [target] 翻译目标，有则提供关于其的翻译数量

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(file.project, ProjectPermission.ACCESS):
            raise NoPermissionError(gettext("您没有权限移动文件"))
        query = self.get_query({}, FileGetSchema())
        data = file.to_api()
        data["project_id"] = str(file.project.id)
        if query["target"]:
            target = file.project.target_by_id(query["target"])
            file_target_cache = FileTargetCache.objects(
                file=file, target=target
            ).first()
            data["file_target_cache"] = file_target_cache.to_api()
        # 插入前后图片的信息
        if file.type == FileType.IMAGE:
            prev_image = (
                file.project.files(
                    parent=file.parent,
                    type_only=FileType.IMAGE,
                    order_by=["-sort_name"],
                )
                .filter(sort_name__lt=file.sort_name)
                .limit(1)
                .first()
            )
            next_image = (
                file.project.files(
                    parent=file.parent,
                    type_only=FileType.IMAGE,
                    order_by=["sort_name"],
                )
                .filter(sort_name__gt=file.sort_name)
                .limit(1)
                .first()
            )
            if prev_image:
                data["prev_image"] = prev_image.to_api()
            if next_image:
                data["next_image"] = next_image.to_api()
        return data

    @token_required
    @fetch_model(File)
    def put(self, file: File):
        """
        @api {put} /v1/files/<file_id> 修改文件 [一个请求仅可提供一个参数]
        @apiVersion 1.0.0
        @apiName putFileAPI
        @apiGroup File
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} [parent_id] 移动文件，需要提供父级文件夹地址，设为'root'为移动到根目录
        @apiParam {String} [name] 修改文件名，需要提供文件名

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查用户权限
        data = self.get_json()
        if data.get("parent_id"):
            if not self.current_user.can(file.project, ProjectPermission.MOVE_FILE):
                raise NoPermissionError(gettext("您没有权限移动文件"))
            if data["parent_id"] == "root":
                file.move_to(None)
            else:
                file.move_to(data["parent_id"])
            return {"message": gettext("移动成功")}
        elif data.get("name"):
            if not self.current_user.can(file.project, ProjectPermission.RENAME_FILE):
                raise NoPermissionError(gettext("您没有权限修改文件名"))
            file.rename(data["name"])
            return {"message": gettext("改名成功")}
        else:
            raise ValidateError(gettext("需要提供parent_id或name参数"))

    @token_required
    @fetch_model(File)
    def delete(self, file):
        """
        @api {get} /v1/files/<file_id> 修改文件
        @apiVersion 1.0.0
        @apiName edit_file
        @apiGroup File
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查用户权限
        if not self.current_user.can(file.project, ProjectPermission.DELETE_FILE):
            raise NoPermissionError(gettext("您没有权限删除文件"))
        file.clear()
        return {"message": gettext("删除成功")}


class FileOCRAPI(MoeAPIView):
    @token_required
    @fetch_model(File)
    def post(self, file: File):
        """
        @api {post} /v1/files/<file_id>/ocr 为文件 OCR
        @apiVersion 1.0.0
        @apiName postFileOCRAPI
        @apiGroup File
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {File} file 文件

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        # 检查用户权限
        if not self.current_user.can(file.project.team, TeamPermission.USE_OCR_QUOTA):
            raise NoPermissionError(
                gettext("您没有此项目所在团队使用自动标记限额的权限")
            )
        if not file.project.source_language.g_ocr_code:
            raise NoPermissionError(gettext("源语言不支持自动标记"))
        if file.type != FileType.IMAGE:
            raise NoPermissionError(gettext("文件不是图像文件"))
        if file.project.team.ocr_quota_left <= 0:
            raise NoPermissionError(gettext("团队限额不足"))
        file.parse()
        return {"message": gettext("已加入队列"), "file": file.to_api()}


class AdminFileListAPI(MoeAPIView):
    @admin_required
    def get(self):
        query = self.get_query({"safe_status": [int]}, AdminFileSearchSchema())
        p = MoePagination()
        db_query = {}
        if query["safe_status"]:
            db_query["safe_status__in"] = query["safe_status"]
        files = (
            File.objects(**db_query).skip(p.skip).limit(p.limit).order_by("-edit_time")
        )
        return p.set_objects(files)


class AdminFileListSafeCheckAPI(MoeAPIView):
    @admin_required
    def put(self):
        data = self.get_json()
        safe_file_ids = data.get("safe_files", [])
        unsafe_file_ids = data.get("unsafe_files", [])
        File.objects(id__in=safe_file_ids).update(safe_status=FileSafeStatus.SAFE)
        unsafe_files = File.objects(id__in=unsafe_file_ids)
        unsafe_files.update(safe_status=FileSafeStatus.BLOCK)
        for file in unsafe_files:
            file.delete_real_file(file_not_exist_reason=FileNotExistReason.BLOCK)
        return {"message": gettext("处理成功")}
