from app.exceptions.project import TargetNotExistError
from app.exceptions import TargetAndSourceLanguageSameError
import datetime

from mongoengine import (
    CASCADE,
    DENY,
    DateTimeField,
    Document,
    IntField,
    ReferenceField,
    StringField,
)

from app.models.language import Language
from app.models.output import Output
from typing import TYPE_CHECKING
from app.exceptions import SameTargetLanguageError

if TYPE_CHECKING:
    from app.models.project import Project


class Target(Document):
    """项目的目标语言，用于储存语言相关的Cache和其他信息"""

    project = ReferenceField("Project", db_field="t", required=True)
    language = ReferenceField(
        Language, required=True, db_field="l", reverse_delete_rule=DENY
    )
    translated_source_count = IntField(db_field="tsc", default=0)  # 已翻译的原文数量
    checked_source_count = IntField(db_field="csc", default=0)  # 已校对的原文数量
    create_time = DateTimeField(db_field="ct", default=datetime.datetime.utcnow)
    edit_time = DateTimeField(
        db_field="et", default=datetime.datetime.utcnow
    )  # 修改时间
    intro = StringField(db_field="i", default="")  # 目标介绍

    @classmethod
    def create(
        cls, project: "Project", language: Language, intro: str = ""
    ) -> "Target":
        """创建项目目标"""
        # 这个语言已存在则报错
        old_target = project.targets(language=language)
        if old_target:
            raise SameTargetLanguageError
        # 不能和源语言相同
        if language == project.source_language:
            raise TargetAndSourceLanguageSameError
        # 创建新的目标语言
        target = Target(project=project, language=language, intro=intro).save()
        project.update(inc__target_count=1)
        project.reload()
        # 对已有文件创建FileTargetCache
        from app.models.file import File

        for file in File.objects(project=project):
            file.create_target_cache(target)
        return target

    def outputs(self) -> list[Output]:
        """所有导出"""
        outputs = Output.objects(project=self.project, target=self).order_by(
            "-create_time"
        )
        return outputs

    def clear(self):
        # 清理 output 文件
        Output.delete_real_files(self.outputs())
        # 减少project的计数
        self.project.update(dec__target_count=1)
        self.delete()

    @classmethod
    def by_id(cls, id):
        file = cls.objects(id=id).first()
        if file is None:
            raise TargetNotExistError
        return file

    def to_api(self):
        return {
            "id": str(self.id),
            "language": self.language.to_api(),
            "translated_source_count": self.translated_source_count,
            "checked_source_count": self.checked_source_count,
            "create_time": self.create_time.isoformat(),
            "edit_time": self.edit_time.isoformat(),
            "intro": self.intro,
        }


Target.register_delete_rule(Output, "target", CASCADE)
