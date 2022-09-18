import datetime
from app.core.views import MoeAPIView
from app.decorators.auth import token_required
from app.decorators.url import fetch_model
from app.exceptions import NoPermissionError
from app.models.file import Source, Translation
from app.models.project import ProjectPermission
from app.validators.translation import (
    CreateTranslationSchema,
    EditTranslationSchema,
)


class SourceTranslationListAPI(MoeAPIView):
    @token_required
    @fetch_model(Source)
    def post(self, source):
        """
        @api {post} /v1/sources/<source_id>/translations 新建/修改我的翻译
        @apiVersion 1.0.0
        @apiName add_translation
        @apiGroup Translation
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} content 翻译内容，当内容为空时，删除我的翻译并返回204
        @apiParam {String} target_id 目标语言ID

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if not self.current_user.can(source.file.project, ProjectPermission.ADD_TRA):
            raise NoPermissionError
        data = self.get_json(CreateTranslationSchema())
        target = source.file.project.target_by_id(data["target_id"])
        translation = source.create_translation(
            data["content"], target=target, user=self.current_user
        )
        if translation:
            return translation.to_api()


class TranslationAPI(MoeAPIView):
    @token_required
    @fetch_model(Translation)
    def put(self, translation):
        """
        @api {put} /v1/translations/<translation_id> 修改、校对、选定翻译
        @apiVersion 1.0.0
        @apiName edit_translation
        @apiGroup Translation
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiParam {String} [content] 翻译内容
        @apiParam {String} [proofread_content] 校对内容
        @apiParam {Boolean} [selected] 是否选定

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        data = self.get_json(EditTranslationSchema())
        if "selected" in data:  # 检查是否有校对权限
            if not self.current_user.can(
                translation.source.file.project, ProjectPermission.CHECK_TRA
            ):
                raise NoPermissionError
            if data["selected"] is True:
                translation.select(user=self.current_user)
            else:
                translation.unselect()
            translation.reload()
        if "content" in data:  # 仅可以修改自己的翻译
            # ！这个前端未用的，目前修改/新增自己的翻译都是调用新增翻译接口，未来可能用于修改他人翻译
            if translation.user != self.current_user:
                raise NoPermissionError
            if data["content"] == "" and translation.proofread_content == "":
                translation.clear()
                return
            translation.content = data["content"]
            translation.update_cache("edit_time", datetime.datetime.utcnow())
        if "proofread_content" in data:  # 检查是否有校对权限
            if not self.current_user.can(
                translation.source.file.project, ProjectPermission.PROOFREAD_TRA,
            ):
                raise NoPermissionError
            if data["proofread_content"] == "" and translation.content == "":
                translation.clear()
                return
            translation.proofread_content = data["proofread_content"]
            if data["proofread_content"] == "":
                translation.proofreader = None
            else:
                translation.proofreader = self.current_user
            translation.update_cache("edit_time", datetime.datetime.utcnow())
        translation.save()
        return translation.to_api()

    @token_required
    @fetch_model(Translation)
    def delete(self, translation):
        """
        @api {delete} /v1/translations/<translation_id> 删除翻译
        @apiVersion 1.0.0
        @apiName delete_translation
        @apiGroup Translation
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        if translation.user != self.current_user and not self.current_user.can(
            translation.source.file.project, ProjectPermission.DELETE_TRA
        ):
            raise NoPermissionError
        translation.clear()
