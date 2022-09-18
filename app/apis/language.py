from app.models.language import Language
from app.core.views import MoeAPIView


class LanguageListAPI(MoeAPIView):
    def get(self):
        """
        @api {get} /v1/languages 获取所有语言
        @apiVersion 1.0.0
        @apiName get_language_list
        @apiGroup Language
        @apiUse APIHeader
        @apiUse TokenHeader

        @apiSuccessExample {json} 返回示例
        {

        }
        """
        languages = Language.get()
        return [language.to_api() for language in languages]
