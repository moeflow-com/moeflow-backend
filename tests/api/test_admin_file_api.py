import os

from app.constants.file import FileType
from app.exceptions import (
    FilenameIllegalError,
    FolderNotExistError,
    NeedTokenError,
    NoPermissionError,
    SuffixNotInFileTypeError,
    UploadFileNotFoundError,
)
from app.exceptions.project import ProjectFinishedError
from app.models.language import Language
from app.models.project import Project
from app.models.team import Team
from app.models.user import User
from flask_apikit.exceptions import ValidateError
from tests import TEST_FILE_PATH, MoeAPITestCase


class AdminFileAPITestCase(MoeAPITestCase):
    def test_get_files1(self):
        """非管理员用户不能访问接口"""
        user = User.create(email="u1", name="u1", password="123123")
        token = user.generate_token()
        data = self.get("/v1/admin/files", token=token)
        self.assertErrorEqual(data, NoPermissionError)

    def test_get_files2(self):
        """管理员用户可以访问接口"""
        user = User.create(email="u1", name="u1", password="123123")
        token = user.generate_token()
        user.admin = True
        user.save()
        data = self.get("/v1/admin/files", token=token)
        self.assertErrorEqual(data)

    def test_get_files3(self):
        """未登录不能访问接口"""
        data = self.get("/v1/admin/files")
        self.assertErrorEqual(data, NeedTokenError)
