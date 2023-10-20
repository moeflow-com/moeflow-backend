from mongoengine import (
    Document,
    ListField,
    BooleanField,
    StringField,
    ObjectIdField,
)
from app.utils.logging import logger


class SiteSetting(Document):
    """
    This document only have one document, of which the type is 'site'.
    """

    type = StringField(db_field="n", required=True, unique=True)
    enable_whitelist = BooleanField(db_field="ew", default=True)
    whitelist_emails = ListField(StringField(), db_field="we", default=list)
    only_allow_admin_create_team = BooleanField(db_field="oacg", default=True)
    auto_join_team_ids = ListField(ObjectIdField(), db_field="ajt", default=list)
    homepage_html = StringField(db_field="h", default="")
    homepage_css = StringField(db_field="hc", default="")

    meta = {
        "indexes": [
            "type",
        ]
    }

    @classmethod
    def init_site_setting(cls):
        logger.info("-" * 50)
        if cls.objects(type="site").count() > 0:
            logger.info("已有站点设置，跳过初始化")
        else:
            logger.info("初始化站点设置")
            cls(type="site").save()

    @classmethod
    def get(cls) -> "SiteSetting":
        return cls.objects(type="site").first()

    def to_api(self):
        return {
            "enable_whitelist": self.enable_whitelist,
            "whitelist_emails": self.whitelist_emails,
            "only_allow_admin_create_team": self.only_allow_admin_create_team,
            "auto_join_team_ids": [str(id) for id in self.auto_join_team_ids],
            "homepage_html": self.homepage_html,
            "homepage_css": self.homepage_css,
        }
