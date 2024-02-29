import datetime
from mongoengine import (
    Document,
    StringField,
    ReferenceField,
    DENY,
    CASCADE,
    DateTimeField,
)

from app.exceptions.language import TargetAndSourceLanguageSameError
from app.models.language import Language
from app.utils.mongo import mongo_order, mongo_slice


# TODO: 改名成 Termbase
class TermBank(Document):
    """术语库"""

    team = ReferenceField("Team", db_field="t")  # 不属于某个团队，则为系统术语库
    name = StringField(db_field="n")
    source_language = ReferenceField(
        Language, db_field="sl", required=True, reverse_delete_rule=DENY
    )  # 源语言
    target_language = ReferenceField(
        Language, db_field="tl", required=True, reverse_delete_rule=DENY
    )  # 目标语言
    tip = StringField(db_field="ti", default="")
    user = ReferenceField("User", db_field="u")  # 创建人
    create_time = DateTimeField(
        db_field="c", default=datetime.datetime.utcnow
    )  # 创建时间
    edit_time = DateTimeField(
        db_field="e", default=datetime.datetime.utcnow
    )  # 修改时间

    @classmethod
    def create(cls, name, team, source_language, target_language, user, tip=""):
        if source_language == target_language:
            raise TargetAndSourceLanguageSameError
        # TODO 创建术语组
        term_bank = cls(
            name=name,
            team=team,
            source_language=source_language,
            target_language=target_language,
            user=user,
            tip=tip,
        ).save()
        return term_bank

    def clear(self):
        self.delete()

    def edit(self, name, source_language, target_language, tip):
        if source_language == target_language:
            raise TargetAndSourceLanguageSameError
        self.name = name
        self.source_language = source_language
        self.target_language = target_language
        self.edit_time = datetime.datetime.utcnow()
        self.tip = tip
        self.save()
        return self

    def terms(self, skip=None, limit=None, order_by=None):
        """返回团队所有项目集"""
        terms = Term.objects(term_bank=self)
        terms = mongo_order(terms, order_by, ["-edit_time"])
        terms = mongo_slice(terms, skip, limit)
        return terms

    def to_api(self):
        """
        @apiDefine TermBankInfoModel
        @apiSuccess {String} id ID
        @apiSuccess {String} name 名称
        @apiSuccess {Object} source_language 原语言
        @apiSuccess {Object} target_language 目标语言
        @apiSuccess {String} tip 小提示
        @apiSuccess {Object} user 创建者
        @apiSuccess {String} create_time 创建时间
        @apiSuccess {String} edit_time 修改时间
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "source_language": self.source_language.to_api(),
            "target_language": self.target_language.to_api(),
            "tip": self.tip,
            "user": self.user.to_api(),
            "create_time": self.create_time.isoformat(),
            "edit_time": self.edit_time.isoformat(),
        }


class TermGroup(Document):
    """术语组"""

    # TODO 术语组，可以对术语进行分组


class Term(Document):
    """术语"""

    term_bank = ReferenceField(
        TermBank, db_field="tb", required=True, reverse_delete_rule=CASCADE
    )
    source = StringField(db_field="o", default="")  # 所属原文
    target = StringField(db_field="t", default="")  # 所属目标语言
    tip = StringField(db_field="ti", default="")
    user = ReferenceField("User", db_field="u")
    create_time = DateTimeField(
        db_field="c", default=datetime.datetime.utcnow
    )  # 创建时间
    edit_time = DateTimeField(
        db_field="e", default=datetime.datetime.utcnow
    )  # 修改时间

    @classmethod
    def create(cls, term_bank, source, target, user, tip=""):
        term = cls(
            term_bank=term_bank,
            source=source,
            target=target,
            tip=tip,
            user=user,
        )
        term.edit_time = datetime.datetime.utcnow()
        term.save()
        # 提示使用此术语库的项目，需要刷新术语
        from app.models.project import Project

        Project.objects(_term_banks=term_bank).update(need_find_terms=True)
        return term

    def clear(self):
        self.delete()

    def edit(self, source, target, tip=""):
        # 如果修改了原文，则需要重新寻找术语
        if self.source != source:
            # 提示使用此术语库的项目，需要刷新术语
            from app.models.project import Project

            Project.objects(_term_banks=self.term_bank).update(need_find_terms=True)
        self.source = source
        self.target = target
        self.tip = tip
        self.edit_time = datetime.datetime.utcnow()
        self.save()
        return self

    def to_api(self):
        """
        @apiDefine TermBankInfoModel
        @apiSuccess {String} id ID
        @apiSuccess {Object} source 原文
        @apiSuccess {Object} target 翻译
        @apiSuccess {String} tip 小提示
        @apiSuccess {Object} user 创建者
        @apiSuccess {String} create_time 创建时间
        @apiSuccess {String} edit_time 修改时间
        """
        return {
            "id": str(self.id),
            "source": self.source,
            "target": self.target,
            "tip": self.tip,
            "user": self.user.to_api(),
            "create_time": self.create_time.isoformat(),
            "edit_time": self.edit_time.isoformat(),
        }
