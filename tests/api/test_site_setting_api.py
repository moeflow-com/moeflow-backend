from mongoengine import DoesNotExist

from app.exceptions import NeedTokenError, NoPermissionError, RoleNotExistError
from app.models.site_setting import SiteSetting
from app.models.team import Team, TeamPermission, TeamRole
from app.models.user import User
from app.constants.role import RoleType
from flask_apikit.exceptions import ValidateError
from tests import MoeAPITestCase


class TestSiteSettingAPI(MoeAPITestCase):
    def test_get_site_setting(self):
        admin_user = self.create_user("admin")
        admin_user.admin = True
        admin_user.save()
        admin_token = admin_user.generate_token()
        user = self.create_user("user")
        user_token = user.generate_token()
        # 普通用户, 无权限
        data = self.get(f"/v1/admin/site-setting", token=user_token)
        self.assertErrorEqual(data, NoPermissionError)
        # 管理员, 有权限
        data = self.get(f"/v1/admin/site-setting", token=admin_token)
        self.assertErrorEqual(data)

    def test_put_site_setting(self):
        admin_user = self.create_user("admin")
        admin_user.admin = True
        admin_user.save()
        admin_token = admin_user.generate_token()
        user = self.create_user("user")
        user_token = user.generate_token()
        site_setting = SiteSetting.get()
        site_setting.enable_whitelist = True
        site_setting.save()
        site_setting.reload()
        self.assertEqual(site_setting.enable_whitelist, True)
        self.assertEqual(site_setting.whitelist_emails, [])
        new_setting_json = {
            "enable_whitelist": False,
            "whitelist_emails": ["admin1@moeflow.com", "admin2@moeflow.com"],
        }
        # 普通用户, 无权限
        data = self.put(
            f"/v1/admin/site-setting", json=new_setting_json, token=user_token
        )
        self.assertErrorEqual(data, NoPermissionError)
        # 管理员, 有权限
        data = self.put(
            f"/v1/admin/site-setting", json=new_setting_json, token=admin_token
        )
        self.assertErrorEqual(data)
        site_setting.reload()
        self.assertEqual(
            site_setting.enable_whitelist, new_setting_json["enable_whitelist"]
        )
        self.assertEqual(
            site_setting.whitelist_emails, new_setting_json["whitelist_emails"]
        )
