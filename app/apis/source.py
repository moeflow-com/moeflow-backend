import datetime
from flask_babel import gettext
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_model
from app.exceptions import FileTypeNotSupportError, NoPermissionError
from app.models.file import File, Source
from app.models.project import ProjectPermission
from app.constants.file import FileType
from flask_apikit.exceptions import ValidateError
from app.validators.source import (
    CreateImageSourceSchema,
    EditImageSourceRankSchema,
    EditImageSourceSchema,
    SourceSearchSchema,
    BatchSelectTranslationSchema,
)
from flask_apikit.utils import QueryParser


class FileSourceListAPI(MoeAPIView):
    @token_required
    @fetch_model(File)
    def get(self, file: File):
        """
        @api {get} /v1/files/<file_id>/sources 获取某个文件的原文
        @apiVersion 1.0.0
        @apiName get_file_sources
        @apiGroup Source
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {Boolean} paging 是否分页
        @apiParam {Number} page 页数
        @apiParam {Number} limit 限制的数量(最大100)

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(file.project, ProjectPermission.ACCESS):
            raise NoPermissionError
        data = self.get_query({"paging": QueryParser.bool}, SourceSearchSchema())
        target = file.project.targets().filter(id=data["target_id"]).first()
        if target is None:
            raise ValidateError("need `target`")
        return file.to_translator(
            target=target, paging=data["paging"], user=self.current_user
        )

    @token_required
    @fetch_model(File)
    def patch(self, file: File):
        """
        @api {patch} /v1/files/<file_id>/sources 批量选中翻译
        @apiVersion 1.0.0
        @apiName batch_select_source_translation
        @apiGroup Source
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(file.project, ProjectPermission.CHECK_TRA):
            raise NoPermissionError
        data = self.get_json(BatchSelectTranslationSchema(many=True))
        for source_translation_id_map in data:
            source_id = source_translation_id_map["source_id"]
            translation_id = source_translation_id_map["translation_id"]
            source = file.sources().filter(id=source_id).first()
            if source:
                translation = source.translations().filter(id=translation_id).first()
                if translation:
                    translation.select(user=self.current_user)
        file.update_cache("edit_time", datetime.datetime.utcnow())
        return

    @token_required
    @fetch_model(File)
    def post(self, file: File):
        """
        @api {post} /v1/files/<file_id>/sources 【仅图片可用】新增原文
        @apiVersion 1.0.0
        @apiName add_file_source
        @apiGroup Source
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} [content] 原文内容，默认为''
        @apiParam {Number} [x] x坐标，默认0
        @apiParam {Number} [y] y坐标，默认0
        @apiParam {Number} [position_type] 框内框外，默认1

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if file.type != FileType.IMAGE:
            raise FileTypeNotSupportError(gettext("只有图片文件能添加原文"))
        if not self.current_user.can(file.project, ProjectPermission.ADD_LABEL):
            raise NoPermissionError
        data = self.get_json(CreateImageSourceSchema())
        source = file.create_source(
            data["content"],
            x=data["x"],
            y=data["y"],
            position_type=data["position_type"],
        )
        file.update_cache("edit_time", datetime.datetime.utcnow())
        return source.to_api()


class SourceAPI(MoeAPIView):
    @token_required
    @fetch_model(Source)
    def put(self, source):
        """
        @api {put} /v1/sources/<source_id> 【仅图片可用】修改原文
        @apiVersion 1.0.0
        @apiName edit_source
        @apiGroup Source
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} [content] 原文内容
        @apiParam {Number} [x] x坐标，默认0
        @apiParam {Number} [y] y坐标，默认0
        @apiParam {Number} [position_type] 框内框外，默认1

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if source.file.type != FileType.IMAGE:
            raise FileTypeNotSupportError(gettext("只有图片文件能修改原文"))
        if not self.current_user.can(source.file.project, ProjectPermission.MOVE_LABEL):
            raise NoPermissionError
        data = self.get_json(EditImageSourceSchema())
        source.update(**data)
        source.update_cache("edit_time", datetime.datetime.utcnow())
        source.reload()
        return source.to_api()

    @token_required
    @fetch_model(Source)
    def delete(self, source):
        """
        @api {delete} /v1/sources/<source_id> 【仅图片可用】删除原文
        @apiVersion 1.0.0
        @apiName delete_source
        @apiGroup Source
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if source.file.type != FileType.IMAGE:
            raise FileTypeNotSupportError(gettext("只有图片文件能删除原文"))
        if not self.current_user.can(
            source.file.project, ProjectPermission.DELETE_LABEL
        ):
            raise NoPermissionError
        source.update_cache("edit_time", datetime.datetime.utcnow())
        source.clear()


class SourceRankAPI(MoeAPIView):
    @token_required
    @fetch_model(Source)
    def put(self, source):
        """
        @api {put} /v1/sources/<source_id>/rank 【仅图片可用】修改原文排序
        @apiVersion 1.0.0
        @apiName edit_source_rank
        @apiGroup Source
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} [next_source_id] 移动到某个原文之前，为“end”则移动到最后

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if source.file.type != FileType.IMAGE:
            raise FileTypeNotSupportError(gettext("只有图片文件能修改原文顺序"))
        if not self.current_user.can(source.file.project, ProjectPermission.ADD_LABEL):
            raise NoPermissionError
        data = self.get_json(EditImageSourceRankSchema())
        if data["next_source_id"] == "end":
            source.move_ahead(None)
        else:
            source.move_ahead(data["next_source_id"])
        return {"message": gettext("修改成功")}
