import os

from app import oss
from app.constants.file import FileNotExistReason, FileSafeStatus, FileType
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


class FileAPITestCase(MoeAPITestCase):
    def test_get_project_file(self):
        """测试获取项目下文件"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            token2 = self.create_user("22", "2@2.com", "111111").generate_token()
            token3 = self.create_user("33", "3@3.com", "111111").generate_token()
            user3 = User.objects(email="3@3.com").first()
            team = Team.create("t1", creator=user)
            user3.join(team)
            # 创建一个项目用于测试
            project = Project.create("p1", team=team, creator=user)
            # 文件结构
            # file1
            # file2
            # dir1
            # |- file3
            # |- file4
            # |- dir2
            # +- dir3
            #    |- file5
            #    |- file6
            #    +- dir4
            dir1 = project.create_folder("dir1")
            project.create_folder("dir2", parent=dir1)
            dir3 = project.create_folder("dir3", parent=dir1)
            dir4 = project.create_folder("dir4", parent=dir3)
            project.create_file("file1.txt")
            project.create_file("file2.txt")
            project.create_file("file3.txt", parent=dir1)
            project.create_file("file4.txt", parent=dir1)
            project.create_file("file5.txt", parent=dir3)
            project.create_file("file6.txt", parent=dir3)
            # === 权限测试 ===
            # 没登录不能获取
            data = self.get("/v1/projects/{}/files".format(project.id))
            self.assertErrorEqual(data, NeedTokenError)
            # 非项目用户且非团队用户不能获取
            data = self.get("/v1/projects/{}/files".format(project.id), token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # 非项目用户但是是团队用户可以获取
            data = self.get("/v1/projects/{}/files".format(project.id), token=token3)
            self.assertErrorEqual(data)
            # === 测试每个目录下的数量 ===
            # 根目录下有3个
            data = self.get("/v1/projects/{}/files".format(project.id), token=token)
            self.assertErrorEqual(data)
            self.assertEqual(len(data.json), 3)
            # dir1下有4个
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"parent_id": str(dir1.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(len(data.json), 4)
            # dir3下有3个
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"parent_id": str(dir3.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(len(data.json), 3)
            # dir4下有0个
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"parent_id": str(dir4.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(len(data.json), 0)

            # === 测试只搜索文件夹、文件 ===
            # 同时only_folder、only_file会报错
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"only_folder": True, "only_file": True},
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)

            # 只搜索文件夹、文件，根目录下文件夹有1个，文件有2个
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"only_folder": True},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(len(data.json), 1)
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"only_file": True},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(len(data.json), 2)

            # 只搜索文件夹、文件，dir1下文件夹有2个，文件有2个
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"only_folder": True, "parent_id": str(dir1.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(len(data.json), 2)
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"only_file": True, "parent_id": str(dir1.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(len(data.json), 2)

            # 测试order_by
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"order_by": ["-type", "-sort_name"]},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(data.json[0]["name"], "file2.txt")
            self.assertEqual(data.json[0]["type"], FileType.TEXT)
            self.assertEqual(data.json[1]["name"], "file1.txt")
            self.assertEqual(data.json[1]["type"], FileType.TEXT)
            self.assertEqual(data.json[2]["name"], "dir1")
            self.assertEqual(data.json[2]["type"], FileType.FOLDER)

            # 测试order_by
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"order_by": ["-type", "sort_name"]},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(data.json[0]["name"], "file1.txt")
            self.assertEqual(data.json[0]["type"], FileType.TEXT)
            self.assertEqual(data.json[1]["name"], "file2.txt")
            self.assertEqual(data.json[1]["type"], FileType.TEXT)
            self.assertEqual(data.json[2]["name"], "dir1")
            self.assertEqual(data.json[2]["type"], FileType.FOLDER)

            # 测试order_by
            data = self.get(
                "/v1/projects/{}/files".format(project.id),
                query_string={"order_by": ["-s"]},
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)

    def test_upload_project_file(self):
        """测试上传文件"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            token2 = self.create_user("22", "2@2.com", "111111").generate_token()
            User.objects(email="2@2.com").first()
            team = Team.create("t1", creator=user)
            # 创建一个项目用于测试
            project = Project.create("p1", team=team, creator=user)
            dir1 = project.create_folder("dir")
            # 文件结构
            # dir1
            # == 没登录没有权限 ==
            data = self.post("/v1/projects/{}/files".format(project.id))
            self.assertErrorEqual(data, NeedTokenError)
            # == user2没有权限 ==
            data = self.post("/v1/projects/{}/files".format(project.id), token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # == 缺少上传文件 ==
            data = self.post("/v1/projects/{}/files".format(project.id), token=token)
            self.assertErrorEqual(data, UploadFileNotFoundError)
            # == 向根目录上传文件 ==
            with open(os.path.join(TEST_FILE_PATH, "term.txt"), "rb") as file:
                data = self.post(
                    "/v1/projects/{}/files".format(project.id),
                    data={"file": (file, "1.txt")},
                    token=token,
                    content_type="multipart/form-data",
                )
                self.assertErrorEqual(data)
                f1 = project.files(parent=None, type_exclude=FileType.FOLDER).first()
                self.assertEqual("1.txt", f1.name)
                self.assertEqual(None, f1.parent)
                self.assertEqual(2, project.files().count())
            # == 向dir文件夹上传文件 ==
            with open(os.path.join(TEST_FILE_PATH, "term.txt"), "rb") as file:
                data = self.post(
                    "/v1/projects/{}/files".format(project.id),
                    data={"file": (file, "2.txt"), "parent_id": str(dir1.id)},
                    token=token,
                )
                self.assertErrorEqual(data)
                f2 = project.files(parent=dir1, type_exclude=FileType.FOLDER).first()
                self.assertEqual("2.txt", f2.name)
                self.assertEqual(dir1, f2.parent)
                self.assertEqual(3, project.files().count())

    def test_edit_file_name(self):
        """测试修改文件名"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            token2 = self.create_user("22", "2@2.com", "111111").generate_token()
            User.objects(email="2@2.com").first()
            team = Team.create("t1", creator=user)
            # 创建一个项目用于测试
            project = Project.create("p1", team=team, creator=user)
            file1 = project.create_file("1.txt")
            project.create_folder("dir1")
            self.assertEqual("1.txt", file1.name)
            # == 没登录没有权限 ==
            data = self.put("/v1/files/{}".format(file1.id), json={"name": "error"})
            self.assertErrorEqual(data, NeedTokenError)
            # == user2没有权限 ==
            data = self.put(
                "/v1/files/{}".format(file1.id),
                json={"name": "error"},
                token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 缺少filename ==
            data = self.put("/v1/files/{}".format(file1.id), json={}, token=token)
            self.assertErrorEqual(data, ValidateError)
            # == 错误的名字 ==
            data = self.put(
                "/v1/files/{}".format(file1.id),
                json={"name": "erro/r.txt"},
                token=token,
            )
            self.assertErrorEqual(data, FilenameIllegalError)
            file1.reload()
            self.assertEqual("1.txt", file1.name)
            # == 不同的后缀 ==
            data = self.put(
                "/v1/files/{}".format(file1.id),
                json={"name": "1.jpg"},
                token=token,
            )
            self.assertErrorEqual(data, SuffixNotInFileTypeError)
            file1.reload()
            self.assertEqual("1.txt", file1.name)
            # == 正确修改 ==
            data = self.put(
                "/v1/files/{}".format(file1.id),
                json={"name": "2.txt"},
                token=token,
            )
            self.assertErrorEqual(data)
            file1.reload()
            self.assertEqual("2.txt", file1.name)

    def test_move_file(self):
        """测试移动文件"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            token2 = self.create_user("22", "2@2.com", "111111").generate_token()
            User.objects(email="2@2.com").first()
            team = Team.create("t1", creator=user)
            # 创建一个项目用于测试
            project = Project.create("p1", team=team, creator=user)
            file1 = project.create_file("1.txt")
            dir1 = project.create_folder("dir1")
            dir2 = project.create_folder("dir2")
            self.assertEqual(None, file1.parent)
            self.assertEqual(None, dir2.parent)
            # == 没登录没有权限 ==
            data = self.put(
                "/v1/files/{}".format(file1.id), json={"parent_id": "error"}
            )
            self.assertErrorEqual(data, NeedTokenError)
            # == user2没有权限 ==
            data = self.put(
                "/v1/files/{}".format(file1.id),
                json={"parent_id": "error"},
                token=token2,
            )
            self.assertErrorEqual(data, NoPermissionError)
            # == 缺少parent_id ==
            data = self.put("/v1/files/{}".format(file1.id), json={}, token=token)
            self.assertErrorEqual(data, ValidateError)
            # == 缺少parent_id，null等同于缺少 ==
            data = self.put(
                "/v1/files/{}".format(file1.id),
                json={"parent_id": None},
                token=token,
            )
            self.assertErrorEqual(data, ValidateError)
            file1.reload()
            self.assertEqual(None, file1.parent)
            # == 错误的parent_id ==
            data = self.put(
                "/v1/files/{}".format(file1.id),
                json={"parent_id": "5c6687beff036b2811111111"},
                token=token,
            )
            self.assertErrorEqual(data, FolderNotExistError)
            file1.reload()
            self.assertEqual(None, file1.parent)
            # == file1移动到dir1 ==
            data = self.put(
                "/v1/files/{}".format(file1.id),
                json={"parent_id": str(dir1.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            file1.reload()
            self.assertEqual(dir1, file1.parent)
            # == file1移动到回根目录 ==
            data = self.put(
                "/v1/files/{}".format(file1.id),
                json={"parent_id": "root"},
                token=token,
            )
            self.assertErrorEqual(data)
            file1.reload()
            self.assertEqual(None, file1.parent)
            # == dir2移动到dir1 ==
            data = self.put(
                "/v1/files/{}".format(dir2.id),
                json={"parent_id": str(dir1.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            dir2.reload()
            self.assertEqual(dir1, dir2.parent)
            # == dir2移动到回根目录 ==
            data = self.put(
                "/v1/files/{}".format(dir2.id),
                json={"parent_id": "root"},
                token=token,
            )
            self.assertErrorEqual(data)
            dir2.reload()
            self.assertEqual(None, dir2.parent)

    def test_delete_file(self):
        """测试删除文件"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            token2 = self.create_user("22", "2@2.com", "111111").generate_token()
            User.objects(email="2@2.com").first()
            team = Team.create("t1", creator=user)
            # 创建一个项目用于测试
            project = Project.create("p1", team=team, creator=user)
            file1 = project.create_file("1.txt")
            dir1 = project.create_folder("dir1")
            project.create_file("2.txt", parent=dir1)
            self.assertEqual(3, project.files().count())
            # == 没登录没有权限 ==
            data = self.delete("/v1/files/{}".format(file1.id))
            self.assertErrorEqual(data, NeedTokenError)
            # == user2没有权限 ==
            data = self.delete("/v1/files/{}".format(file1.id), token=token2)
            self.assertErrorEqual(data, NoPermissionError)
            # == 删除file1 ==
            data = self.delete(
                "/v1/files/{}".format(file1.id),
                json={"parent_id": str(dir1.id)},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(2, project.files().count())
            # == 删除dir1 ==
            data = self.delete(
                "/v1/files/{}".format(dir1.id),
                json={"parent_id": "root"},
                token=token,
            )
            self.assertErrorEqual(data)
            self.assertEqual(0, project.files().count())

    def test_get_project_files_permission1(self):
        """非项目用户且非团队用户不能获取文件列表"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            team = Team.create("t1")
            project = Project.create("p1", team=team)
            # 没登录不能获取
            data = self.get("/v1/projects/{}/files".format(project.id))
            self.assertErrorEqual(data, NeedTokenError)
            # 非项目用户且非团队用户不能获取
            data = self.get("/v1/projects/{}/files".format(project.id), token=token)
            self.assertErrorEqual(data, NoPermissionError)

    def test_get_project_files_permission2(self):
        """团队用户可以获取文件列表"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            team = Team.create("t1")
            project = Project.create("p1", team=team)
            user.join(team)
            data = self.get("/v1/projects/{}/files".format(project.id), token=token)
            self.assertErrorEqual(data)

    def test_get_project_files_permission3(self):
        """项目用户可以获取文件列表"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            team = Team.create("t1")
            project = Project.create("p1", team=team)
            user.join(project)
            data = self.get("/v1/projects/{}/files".format(project.id), token=token)
            self.assertErrorEqual(data)

    def test_get_project_files_permission4(self):
        """团队且项目用户可以获取文件列表"""
        with self.app.test_request_context():
            token = self.create_user("11", "1@1.com", "111111").generate_token()
            user = User.objects(email="1@1.com").first()
            team = Team.create("t1")
            project = Project.create("p1", team=team)
            user.join(team)
            user.join(project)
            data = self.get("/v1/projects/{}/files".format(project.id), token=token)
            self.assertErrorEqual(data)

    def test_upload_file_to_finished_project(self):
        """测试向已完结的项目上传文件"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        token = self.get_creator(project).generate_token()
        project.finish()
        with open(os.path.join(TEST_FILE_PATH, "term.txt"), "rb") as file:
            data = self.post(
                f"/v1/projects/{str(project.id)}/files",
                data={"file": (file, "1.txt")},
                token=token,
                content_type="multipart/form-data",
            )
            self.assertErrorEqual(data, ProjectFinishedError)

    def test_get_files_to_finished_project(self):
        """测试向已完结的项目上传文件"""
        project = self.create_project("p", target_languages=Language.by_code("en"))
        token = self.get_creator(project).generate_token()
        project.finish()
        data = self.get(f"/v1/projects/{str(project.id)}/files", token=token)
        self.assertErrorEqual(data, ProjectFinishedError)

    def test_admin_file_safe_check1(self):
        """测试管理员审核文件"""
        with self.app.test_request_context():
            project = self.create_project("p", target_languages=Language.by_code("en"))
            user = self.get_creator(project)
            user.admin = True
            user.save()
            token = user.generate_token()
            with open(os.path.join(TEST_FILE_PATH, "2kb.png"), "rb") as file:
                file1 = project.upload("1.jpg", file)
                file1_save_name = file1.save_name
                file2 = project.upload("2.jpg", file)
                file2_save_name = file2.save_name
                file3 = project.upload("3.jpg", file)
                file3_save_name = file3.save_name
                file4 = project.upload("4.jpg", file)
                file4_save_name = file4.save_name
                self.assertTrue(
                    oss.is_exist(self.app.config["OSS_FILE_PREFIX"], file1_save_name)
                )
                self.assertTrue(
                    oss.is_exist(self.app.config["OSS_FILE_PREFIX"], file2_save_name)
                )
                self.assertTrue(
                    oss.is_exist(self.app.config["OSS_FILE_PREFIX"], file3_save_name)
                )
                self.assertTrue(
                    oss.is_exist(self.app.config["OSS_FILE_PREFIX"], file4_save_name)
                )
                self.assertEqual(file1.safe_status, FileSafeStatus.NEED_MACHINE_CHECK)
                self.assertEqual(
                    file1.file_not_exist_reason, FileNotExistReason.UNKNOWN
                )
                self.assertEqual(file3.safe_status, FileSafeStatus.NEED_MACHINE_CHECK)
                self.assertEqual(
                    file3.file_not_exist_reason, FileNotExistReason.UNKNOWN
                )
                data = self.put(
                    "/v1/admin/files/safe-status",
                    json={
                        "safe_files": [str(file1.id), str(file2.id)],
                        "unsafe_files": [str(file3.id), str(file4.id)],
                    },
                    token=token,
                )
                self.assertErrorEqual(data)
                self.assertTrue(
                    oss.is_exist(self.app.config["OSS_FILE_PREFIX"], file1_save_name)
                )
                self.assertTrue(
                    oss.is_exist(self.app.config["OSS_FILE_PREFIX"], file2_save_name)
                )
                self.assertFalse(
                    oss.is_exist(self.app.config["OSS_FILE_PREFIX"], file3_save_name)
                )
                self.assertFalse(
                    oss.is_exist(self.app.config["OSS_FILE_PREFIX"], file4_save_name)
                )
                file1.reload()
                file3.reload()
                self.assertEqual(file1.safe_status, FileSafeStatus.SAFE)
                self.assertEqual(
                    file1.file_not_exist_reason, FileNotExistReason.UNKNOWN
                )
                self.assertEqual(file3.safe_status, FileSafeStatus.BLOCK)
                self.assertEqual(file3.file_not_exist_reason, FileNotExistReason.BLOCK)
