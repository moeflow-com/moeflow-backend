import math
import os

from flask import current_app
from mongoengine import DoesNotExist

from app import oss
from app.exceptions import (
    FilenameDuplicateError,
    FilenameIllegalError,
    FileParentIsSameError,
    FileParentIsSubFolderError,
    FileTypeNotSupportError,
    FolderNotExistError,
    SuffixNotInFileTypeError,
    TargetIsNotFolderError,
)
from app.models.file import File, Filename
from app.models.language import Language
from app.models.project import Project
from app.models.team import Team
from app.models.user import User
from app.constants.file import FileNotExistReason, FileType
from app.utils.file import get_file_size
from app.utils.hash import get_file_md5
from tests import TEST_FILE_PATH, MoeTestCase
from app.constants.file import FileSafeStatus


class FileModelTestCase(MoeTestCase):
    def setUp(self):
        super().setUp()
        team = Team.create("1")
        self.tmp_project = Project.create("1", team)

    def check_sort_name(self, dir_sort_name, sort_name, file):
        """[帮助函数]用于同时检查两个sort_name"""
        self.assertEqual(dir_sort_name, file.dir_sort_name)
        self.assertEqual(sort_name, file.sort_name)

    def check_ancestors(self, ancestors, file):
        """
        检查父级、祖先、排序名以及路径排序名

        :param ancestors: 期望的祖先
        :param file: 文件
        :return:
        """

        def get_sort_name(file):
            """[帮助函数]获取sort_name"""
            return Filename(file.name).sort_name

        def get_dir_sort_name(files):
            """[帮助函数]通过祖先列表获取dir_sort_name"""
            dir_sort_name = ""
            for i, file in enumerate(files, start=1):
                dir_sort_name += Filename(file.name).sort_name + "/"
            return dir_sort_name

        # 期望的父级
        if len(ancestors) > 0:
            parent = ancestors[-1]
        else:
            parent = None

        self.assertEqual(get_sort_name(file), file.sort_name)
        self.assertEqual(parent, file.parent)
        self.assertEqual(ancestors, file.ancestors)  # 祖先
        self.assertEqual(
            get_dir_sort_name(ancestors), file.dir_sort_name
        )  # 文件夹排序名

    def test_image_only(self):
        """测试image_only装饰器"""
        with self.app.test_request_context():
            # IMAGE文件没问题
            file = File(
                name="1",
                save_name="1",
                sort_name="1",
                project=self.tmp_project,
                type=FileType.IMAGE,
            ).save()
            file._create_image_source("1", x=1, y=1)
            # TEXT类型文件会报错
            with self.assertRaises(FileTypeNotSupportError):
                file2 = File(
                    name="1",
                    save_name="1",
                    sort_name="1",
                    project=self.tmp_project,
                    type=FileType.TEXT,
                ).save()
                file2._create_image_source("1", x=1, y=1)

    def test_parent_is_not_dir(self):
        """测试parent不是Folder时报错"""
        dir = File(
            name="d1",
            save_name="d1",
            sort_name="1",
            project=self.tmp_project,
            type=FileType.FOLDER,
        ).save()
        file = File(
            name="1",
            save_name="1",
            sort_name="1",
            project=self.tmp_project,
            type=FileType.IMAGE,
        ).save()
        # 父级是image报错
        with self.assertRaises(TargetIsNotFolderError):
            File(
                name="2",
                save_name="2",
                sort_name="1",
                project=self.tmp_project,
                type=FileType.IMAGE,
                parent=file,
            ).save()
        self.assertEqual(0, File.objects(name="2").count())
        # 父级是dir保存成功
        file2 = File(
            name="2",
            save_name="2",
            sort_name="1",
            project=self.tmp_project,
            type=FileType.IMAGE,
            parent=dir,
        ).save()
        self.assertEqual(1, File.objects(name="2").count())
        # 父级是image报错
        with self.assertRaises(TargetIsNotFolderError):
            File(
                name="d2",
                save_name="2",
                sort_name="1",
                project=self.tmp_project,
                type=FileType.FOLDER,
                parent=file2,
            ).save()
        self.assertEqual(0, File.objects(name="d2").count())

    def test_dir_sort_name_and_ancestors(self):
        """测试dir_sort_name和ancestors的自动生成"""
        dir = File(
            name="d1",
            save_name="1",
            sort_name="d1",
            project=self.tmp_project,
            type=FileType.FOLDER,
        ).save()
        dir.reload()
        self.assertEqual("", dir.dir_sort_name)
        self.assertEqual([], dir.ancestors)
        # dir2存在dir下
        dir2 = File(
            name="d2",
            save_name="1",
            sort_name="d2",
            project=self.tmp_project,
            type=FileType.FOLDER,
            parent=dir,
        ).save()
        dir2.reload()
        self.assertEqual("d1/", dir2.dir_sort_name)
        self.assertEqual([dir], dir2.ancestors)
        # dir3存在dir2下
        dir3 = File(
            name="d3",
            save_name="1",
            sort_name="d3",
            project=self.tmp_project,
            type=FileType.FOLDER,
            parent=dir2,
        ).save()
        dir3.reload()
        self.assertEqual("d1/d2/", dir3.dir_sort_name)
        self.assertEqual([dir, dir2], dir3.ancestors)
        # file存在dir2下
        file = File(
            name="f1",
            save_name="1",
            sort_name="f1",
            project=self.tmp_project,
            type=FileType.IMAGE,
            parent=dir3,
        ).save()
        file.reload()
        self.assertEqual("d1/d2/d3/", file.dir_sort_name)
        self.assertEqual([dir, dir2, dir3], file.ancestors)

    def test_create_file(self):
        """测试创建文件"""
        with self.app.test_request_context():
            # 测试用项目、团队
            team = Team.create("t1")
            project = Project.create("p1", team=team)
            # 创建文件
            file1 = project.create_file("1.txt")
            dir = project.create_folder("1")
            file2 = project.create_file("1.txt", parent=dir)
            # 检测基本信息
            project.reload()
            self.assertEqual("1.txt", file1.name)
            self.assertEqual("1.txt", file2.name)
            self.assertEqual(dir, file2.parent)
            self.assertEqual(FileNotExistReason.NOT_UPLOAD, file1.file_not_exist_reason)
            self.assertEqual(FileNotExistReason.NOT_UPLOAD, file2.file_not_exist_reason)
            self.assertEqual(2, project.file_count)
            self.assertEqual(2, project.files(type_exclude=FileType.FOLDER).count())

    def test_upload_text_filename_case(self):
        """测试上传名称大小写（文本，因为文本有修订版区别）"""
        with self.app.test_request_context():
            with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
                # 测试用项目、团队
                team = Team.create("t1")
                project = Project.create("p1", team=team)
                # 上传文件
                md5sum1 = "d47b127bc2de2d687ddc82dac354c415"
                file1 = project.upload("A.txT", file)
                # 下载文件的md5
                download_file = file1.download_real_file()
                self.assertEqual(md5sum1, file1.md5)
                self.assertEqual(md5sum1, get_file_md5(download_file))
                self.assertEqual("A.txT", file1.name)
            with open(os.path.join(TEST_FILE_PATH, "1kbB.txt"), "rb") as file:
                md5sum2 = "e9f8000caffbce369d7fee9c07d43509"
                # 覆盖上传
                file2 = project.upload("a.txt", file)
                # 下载文件的md5
                download_file = file2.download_real_file()
                self.assertEqual(md5sum2, file2.md5)
                self.assertEqual(md5sum2, get_file_md5(download_file))
                self.assertEqual("A.txT", file2.name)
                self.assertEqual(file1.activated_revision, file2)

    def test_upload_image_filename_case(self):
        """测试上传名称大小写（图片）"""
        with self.app.test_request_context():
            with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
                # 测试用项目、团队
                team = Team.create("t1")
                project = Project.create("p1", team=team)
                # 上传文件
                md5sum1 = "d47b127bc2de2d687ddc82dac354c415"
                file1 = project.upload("A.JPg", file)
                # 下载文件的md5
                download_file = file1.download_real_file()
                self.assertEqual(md5sum1, file1.md5)
                self.assertEqual(md5sum1, get_file_md5(download_file))
                self.assertEqual("A.JPg", file1.name)
            with open(os.path.join(TEST_FILE_PATH, "1kbB.txt"), "rb") as file:
                md5sum2 = "e9f8000caffbce369d7fee9c07d43509"
                # 覆盖上传
                file2 = project.upload("a.jpG", file)
                # 下载文件的md5
                download_file = file2.download_real_file()
                self.assertEqual(md5sum2, file2.md5)
                self.assertEqual(md5sum2, get_file_md5(download_file))
                self.assertEqual("A.JPg", file2.name)
                self.assertEqual(file1, file2)

    def test_upload_file_reset_safe_status(self):
        """测试覆盖文件时，会重置安全检查状态"""
        with self.app.test_request_context():
            with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
                # 测试用项目、团队
                team = Team.create("t1")
                project = Project.create("p1", team=team)
                # 上传文件
                file1 = project.upload("1.jpg", file)
                self.assertEqual(file1.safe_status, FileSafeStatus.NEED_MACHINE_CHECK)
                file1.update(safe_status=FileSafeStatus.SAFE)
                file1.reload()
                self.assertEqual(file1.safe_status, FileSafeStatus.SAFE)
                # 覆盖文件，将重置安全检查状态
                project.upload("1.jpg", file)
                file1.reload()
                self.assertEqual(file1.safe_status, FileSafeStatus.NEED_MACHINE_CHECK)

    def test_file_md5(self):
        """测试md5的获取"""
        with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
            # 测试用项目、团队
            team = Team.create("t1")
            project = Project.create(
                name="p1",
                team=team,
                source_language=Language.by_code("ja"),
                target_languages=Language.by_code("zh-CN"),
            )
            md5sum = "d47b127bc2de2d687ddc82dac354c415"
            # 上传文件
            file1 = project.upload("1.txt", file)
            project.reload()
            # 下载文件的md5
            download_file = file1.download_real_file()
            self.assertEqual(md5sum, file1.md5)
            self.assertEqual(md5sum, get_file_md5(download_file))

    def test_upload_image_file(self):
        """测试上传图片文件"""
        """
        进行如下测试：
        不同文件夹不会覆盖
        不同文件名不会覆盖
        测试同名文件的覆盖（是否成功替换文件，原文件同时被删除，是否更新文件大小)
        测试原文不会被覆盖
        """
        # 测试用项目、团队
        team = Team.create("t1")
        project = Project.create(
            name="p1",
            team=team,
            source_language=Language.by_code("ja"),
            target_languages=Language.by_code("zh-CN"),
        )
        dir = project.create_folder("dir3")
        # 打开两张图片
        with open(os.path.join(TEST_FILE_PATH, "2kb.png"), "rb") as png2kb_file:
            with open(os.path.join(TEST_FILE_PATH, "3kb.png"), "rb") as png3kb_file:
                # 获取测试文件基本信息
                png2kb_md5 = get_file_md5(png2kb_file)
                png3kb_md5 = get_file_md5(png3kb_file)
                png2kb_size = math.ceil(get_file_size(png2kb_file))
                png3kb_size = math.ceil(get_file_size(png3kb_file))
                # 上传第一张图片
                png2kb = project.upload("1.png", png2kb_file)
                png2kb_old_save_name = png2kb.save_name
                png2kb.create_source("1", x=0, y=0)
                png2kb.create_source("2", x=0, y=0)
                png2kb_fisrt_save_name = png2kb.save_name
                self.assertEqual(png2kb_md5, png2kb.md5)
                self.assertEqual(png2kb_size, png2kb.file_size)
                self.assertEqual(2, png2kb.sources().count())
            # == 不同文件夹不会覆盖 ==
            with open(os.path.join(TEST_FILE_PATH, "3kb.png"), "rb") as png3kb_file:
                project.upload("1.png", png3kb_file, parent=dir)
                project.reload()
                self.assertEqual(2, project.file_count)
                self.assertEqual(2, project.files(type_exclude=FileType.FOLDER).count())
                self.assertEqual(png2kb_size + png3kb_size, project.file_size)
            # == 不同文件名不会覆盖 ==
            with open(os.path.join(TEST_FILE_PATH, "3kb.png"), "rb") as png3kb_file:
                project.upload("2.png", png3kb_file)
                png2kb.reload()
                self.assertEqual(png2kb_md5, png2kb.md5)
                project.reload()
                self.assertEqual(3, project.file_count)
                self.assertEqual(3, project.files(type_exclude=FileType.FOLDER).count())
                self.assertEqual(png2kb_size + png3kb_size * 2, project.file_size)
            # == 测试同名文件的覆盖（是否成功替换文件，原文件同时被删除，是否更新文件大小) ==
            # == 测试原文不会被覆盖 ==
            # png2kb的源文件还在oss上
            self.assertTrue(
                oss.is_exist(self.app.config["OSS_FILE_PREFIX"], png2kb_old_save_name)
            )
            with open(os.path.join(TEST_FILE_PATH, "3kb.png"), "rb") as png3kb_file:
                png3kb_replace_png2kb = project.upload("1.png", png3kb_file)
                png2kb.reload()
                self.assertEqual(png3kb_replace_png2kb.id, png2kb.id)
                self.assertEqual(png3kb_replace_png2kb.save_name, png2kb.save_name)
                self.assertNotEqual(png2kb_fisrt_save_name, png2kb.save_name)
                self.assertEqual(png3kb_md5, png2kb.md5)
                # 原文不会被覆盖
                self.assertEqual(2, png2kb.sources().count())
                self.assertEqual(2, png3kb_replace_png2kb.sources().count())
                # 项目缓存被刷新
                project.reload()
                self.assertEqual(3, project.file_count)
                self.assertEqual(3, project.files(type_exclude=FileType.FOLDER).count())
                self.assertEqual(png3kb_size * 3, project.file_size)  # size变化了
                self.assertEqual(
                    png3kb_size, png3kb_replace_png2kb.file_size
                )  # size变化了
                # png2kb的源文件已经删除
                self.assertFalse(
                    oss.is_exist(
                        self.app.config["OSS_FILE_PREFIX"],
                        png2kb_old_save_name,
                    )
                )
                # 从oss下载下来对比下md5，和新的png3kb一样了
                png3kb_from_oss = oss.download(
                    self.app.config["OSS_FILE_PREFIX"],
                    png3kb_replace_png2kb.save_name,
                )
                self.assertEqual(get_file_md5(png3kb_from_oss), png3kb_md5)

    def test_upload_text_file(self):
        """测试上传文本文件"""
        """
        进行如下测试
        测试同名文件的，创建了新修订版，并且新的为激活的
        测试是否成功复制Translation和Tip(包括含有多个的情况)
        """
        team = Team.create("t1")
        project = Project.create(
            name="p1",
            team=team,
            source_language=Language.by_code("ja"),
            target_languages=Language.by_code("zh-CN"),
        )
        target = project.targets().first()
        project.create_folder("dir3")
        user = User(name="u1", email="u1").save()
        user2 = User(name="u2", email="u2").save()
        # 上传revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionA.txt"), "rb") as file:
            revision_a = project.upload("1.txt", file)
            # 检查项目属性
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(1, project.files(type_exclude=FileType.FOLDER).count())
            # 检查文件相关的原文数
            self.assertEqual(4, revision_a.source_count)  # 不含空格有4行
            self.assertEqual(5, revision_a.sources().count())  # 含空格有5行
            # 给文章添加翻译
            for i, source in enumerate(revision_a.sources()):
                source.create_translation(str(i + 2), target, user=user)
                source.create_translation(
                    str(i), target, user=user
                )  # 再修改一遍，不会导致已翻译的计数出错
                source.create_tip(str(i), target, user=user)
            revision_a.reload()
            self.assertEqual(4, revision_a.translated_source_count)  # 不含空格有4行
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.translations()]
                    for source in revision_a.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.tips()]
                    for source in revision_a.sources()
                ],
            )
            # 检查激活修订版
            self.assertTrue(revision_a.activated)
            self.assertEqual(1, revision_a.revisions.count())
            self.assertEqual(revision_a, revision_a.activated_revision)
            self.assertEqual(0, revision_a.deactivated_revisions.count())
        # 上传revisionB.txt覆盖revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionB.txt"), "rb") as file:
            revision_b = project.upload("1.txt", file)
            # 检查项目属性
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(1, project.files(type_exclude=FileType.FOLDER).count())
            # 检查文件相关的原文数
            self.assertEqual(5, revision_b.source_count)  # 新的翻译，不含空格有5行
            self.assertEqual(7, revision_b.sources().count())  # 新的翻译，含空格有7行
            # 之前有翻译且能找到一模一样原文的有3行
            self.assertEqual(3, revision_b.translated_source_count)
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.translations()]
                    for source in revision_b.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.tips()]
                    for source in revision_b.sources()
                ],
            )
            # 给“五”增加翻译
            revision_b.sources()[5].create_translation("5-1", target, user=user)
            revision_b.sources()[5].create_tip("5-1", target, user=user)
            revision_b.sources()[5].create_translation(
                "5-2", target, user=user
            )  # 同用户，翻译覆盖
            revision_b.sources()[5].create_tip(
                "5-2", target, user=user
            )  # 同用户，提示新增
            revision_b.sources()[5].create_translation(
                "5-3", target, user=user2
            )  # 不同用户，翻译新增
            revision_b.sources()[5].create_tip(
                "5-3", target, user=user2
            )  # 不同用户，提示新增
            # 检查激活修订版
            revision_a.reload()
            self.assertFalse(revision_a.activated)
            self.assertTrue(revision_b.activated)
            self.assertEqual(2, revision_a.revisions.count())
            self.assertEqual(2, revision_b.revisions.count())
            self.assertEqual(revision_b, revision_a.activated_revision)
            self.assertEqual(revision_b, revision_b.activated_revision)
            self.assertEqual(1, revision_a.deactivated_revisions.count())
            self.assertEqual(1, revision_b.deactivated_revisions.count())
            self.assertIn(revision_a, revision_b.deactivated_revisions)
        # 上传revisionC.txt覆盖revisionB.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionC.txt"), "rb") as file:
            revision_c = project.upload("1.txt", file)
            # 检查项目属性
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(1, project.files(type_exclude=FileType.FOLDER).count())
            # 检查文件相关的原文数
            self.assertEqual(7, revision_c.source_count)  # 新的翻译，不含空格有7行
            self.assertEqual(8, revision_c.sources().count())  # 新的翻译，含空格有8行
            # 之前有翻译且能找到一模一样原文的有5行
            self.assertEqual(5, revision_c.translated_source_count)
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], ["5-3", "5-2"], ["1"]],
                [
                    [item.content for item in source.translations()]
                    for source in revision_c.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], ["5-3", "5-2", "5-1"], ["1"]],
                [
                    [item.content for item in source.tips()]
                    for source in revision_c.sources()
                ],
            )
            # 检查激活修订版
            revision_a.reload()
            revision_b.reload()
            self.assertFalse(revision_a.activated)
            self.assertFalse(revision_b.activated)
            self.assertTrue(revision_c.activated)
            self.assertEqual(3, revision_a.revisions.count())
            self.assertEqual(3, revision_b.revisions.count())
            self.assertEqual(3, revision_c.revisions.count())
            self.assertEqual(revision_c, revision_a.activated_revision)
            self.assertEqual(revision_c, revision_b.activated_revision)
            self.assertEqual(revision_c, revision_c.activated_revision)
            self.assertEqual(2, revision_a.deactivated_revisions.count())
            self.assertEqual(2, revision_b.deactivated_revisions.count())
            self.assertEqual(2, revision_c.deactivated_revisions.count())
            self.assertIn(revision_a, revision_c.deactivated_revisions)
            self.assertIn(revision_b, revision_c.deactivated_revisions)

    def test_clear_revisions(self):
        """测试文件的多个修订版删除操作"""
        """
        进行如下测试
        删除文件夹会删除文件及相应修订版（根目录）
        删除文件夹会删除文件及相应修订版（文件夹下）
        除文件会删除文件及相应修订版（文件夹下）
        删除文件会删除文件及相应修订版（根目录）
        """
        team = Team.create("t1")
        project = Project.create(
            name="p1",
            team=team,
            source_language=Language.by_code("ja"),
            target_languages=Language.by_code("zh-CN"),
        )
        target = project.targets().first()
        dir1 = project.create_folder("dir1")
        dir2 = project.create_folder("dir2", parent=dir1)
        dir3 = project.create_folder("dir3", parent=dir2)
        user = User(name="u1", email="u1").save()
        User(name="u2", email="u2").save()
        # == 删除文件夹会删除文件及相应修订版（根目录） ==
        # /1.txt 有三个修订版，删除激活的
        # 上传revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionA.txt"), "rb") as file:
            revision_a = project.upload("1.txt", file)
            # 检查文件相关的原文数
            self.assertEqual(4, revision_a.source_count)  # 不含空格有4行
            self.assertEqual(5, revision_a.sources().count())  # 含空格有5行
            # 给文章添加翻译
            for i, source in enumerate(revision_a.sources()):
                source.create_translation(str(i + 2), target, user=user)
                source.create_translation(
                    str(i), target, user=user
                )  # 再修改一遍，不会导致已翻译的计数出错
                source.create_tip(str(i), target, user=user)
            revision_a.reload()
            self.assertEqual(4, revision_a.translated_source_count)  # 不含空格有4行
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.translations()]
                    for source in revision_a.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.tips()]
                    for source in revision_a.sources()
                ],
            )
            # 检查激活修订版
            self.assertTrue(revision_a.activated)
            self.assertEqual(1, revision_a.revisions.count())
            self.assertEqual(revision_a, revision_a.activated_revision)
            self.assertEqual(0, revision_a.deactivated_revisions.count())
        # 上传revisionB.txt覆盖revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionB.txt"), "rb") as file:
            revision_b = project.upload("1.txt", file)
            # 检查文件相关的原文数
            self.assertEqual(5, revision_b.source_count)  # 新的翻译，不含空格有5行
            self.assertEqual(7, revision_b.sources().count())  # 新的翻译，含空格有7行
            # 之前有翻译且能找到一模一样原文的有3行
            self.assertEqual(3, revision_b.translated_source_count)
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.translations()]
                    for source in revision_b.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.tips()]
                    for source in revision_b.sources()
                ],
            )
            # 检查激活修订版
            revision_a.reload()
            self.assertFalse(revision_a.activated)
            self.assertTrue(revision_b.activated)
            self.assertEqual(2, revision_a.revisions.count())
            self.assertEqual(2, revision_b.revisions.count())
            self.assertEqual(revision_b, revision_a.activated_revision)
            self.assertEqual(revision_b, revision_b.activated_revision)
            self.assertEqual(1, revision_a.deactivated_revisions.count())
            self.assertEqual(1, revision_b.deactivated_revisions.count())
            self.assertIn(revision_a, revision_b.deactivated_revisions)
        # 上传revisionB.txt覆盖revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionB.txt"), "rb") as file:
            revision_c = project.upload("1.txt", file)
            # 检查文件相关的原文数
            self.assertEqual(5, revision_c.source_count)  # 新的翻译，不含空格有5行
            self.assertEqual(7, revision_c.sources().count())  # 新的翻译，含空格有7行
            # 之前有翻译且能找到一模一样原文的有3行
            self.assertEqual(3, revision_c.translated_source_count)
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.translations()]
                    for source in revision_b.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.tips()]
                    for source in revision_b.sources()
                ],
            )
            # 检查激活修订版
            revision_a.reload()
            revision_b.reload()
            self.assertFalse(revision_a.activated)
            self.assertFalse(revision_b.activated)
            self.assertTrue(revision_c.activated)
            self.assertEqual(3, revision_c.revisions.count())
            self.assertEqual(revision_c, revision_a.activated_revision)
            self.assertEqual(revision_c, revision_b.activated_revision)
            self.assertEqual(2, revision_c.deactivated_revisions.count())
            self.assertEqual(2, revision_c.deactivated_revisions.count())
            self.assertIn(revision_a, revision_b.deactivated_revisions)
        self.assertEqual(6, File.objects.count())
        self.assertTrue(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_a.save_name)
        )
        self.assertTrue(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_b.save_name)
        )
        self.assertTrue(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_c.save_name)
        )
        revision_c.clear()
        self.assertEqual(3, File.objects.count())
        self.assertFalse(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_a.save_name)
        )
        self.assertFalse(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_b.save_name)
        )
        self.assertFalse(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_c.save_name)
        )
        # == 删除文件夹会删除文件及相应修订版（文件夹下）==
        # /dir/1.txt 有两个修订版，删除激活的
        # 上传revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionA.txt"), "rb") as file:
            revision_a = project.upload("1.txt", file, parent=dir1)
            # 检查文件相关的原文数
            self.assertEqual(4, revision_a.source_count)  # 不含空格有4行
            self.assertEqual(5, revision_a.sources().count())  # 含空格有5行
            # 给文章添加翻译
            for i, source in enumerate(revision_a.sources()):
                source.create_translation(str(i + 2), target, user=user)
                source.create_translation(
                    str(i), target, user=user
                )  # 再修改一遍，不会导致已翻译的计数出错
                source.create_tip(str(i), target, user=user)
            revision_a.reload()
            self.assertEqual(4, revision_a.translated_source_count)  # 不含空格有4行
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.translations()]
                    for source in revision_a.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.tips()]
                    for source in revision_a.sources()
                ],
            )
            # 检查激活修订版
            self.assertTrue(revision_a.activated)
            self.assertEqual(1, revision_a.revisions.count())
            self.assertEqual(revision_a, revision_a.activated_revision)
            self.assertEqual(0, revision_a.deactivated_revisions.count())
        # 上传revisionB.txt覆盖revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionB.txt"), "rb") as file:
            revision_b = project.upload("1.txt", file, parent=dir1)
            # 检查文件相关的原文数
            self.assertEqual(5, revision_b.source_count)  # 新的翻译，不含空格有5行
            self.assertEqual(7, revision_b.sources().count())  # 新的翻译，含空格有7行
            # 之前有翻译且能找到一模一样原文的有3行
            self.assertEqual(3, revision_b.translated_source_count)
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.translations()]
                    for source in revision_b.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.tips()]
                    for source in revision_b.sources()
                ],
            )
            # 检查激活修订版
            revision_a.reload()
            self.assertFalse(revision_a.activated)
            self.assertTrue(revision_b.activated)
            self.assertEqual(2, revision_a.revisions.count())
            self.assertEqual(2, revision_b.revisions.count())
            self.assertEqual(revision_b, revision_a.activated_revision)
            self.assertEqual(revision_b, revision_b.activated_revision)
            self.assertEqual(1, revision_a.deactivated_revisions.count())
            self.assertEqual(1, revision_b.deactivated_revisions.count())
            self.assertIn(revision_a, revision_b.deactivated_revisions)
        self.assertEqual(5, File.objects.count())
        self.assertTrue(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_a.save_name)
        )
        self.assertTrue(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_b.save_name)
        )
        revision_b.clear()
        self.assertEqual(3, File.objects.count())
        self.assertFalse(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_a.save_name)
        )
        self.assertFalse(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_b.save_name)
        )
        # == 删除文件会删除文件及相应修订版（文件夹下）==
        # /dir/dir2/dir3/1.txt 有两个修订版，删除dir3
        with open(os.path.join(TEST_FILE_PATH, "revisionA.txt"), "rb") as file:
            revision_a = project.upload("1.txt", file, parent=dir3)
            # 检查文件相关的原文数
            self.assertEqual(4, revision_a.source_count)  # 不含空格有4行
            self.assertEqual(5, revision_a.sources().count())  # 含空格有5行
            # 给文章添加翻译
            for i, source in enumerate(revision_a.sources()):
                source.create_translation(str(i + 2), target, user=user)
                source.create_translation(
                    str(i), target, user=user
                )  # 再修改一遍，不会导致已翻译的计数出错
                source.create_tip(str(i), target, user=user)
            revision_a.reload()
            self.assertEqual(4, revision_a.translated_source_count)  # 不含空格有4行
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.translations()]
                    for source in revision_a.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.tips()]
                    for source in revision_a.sources()
                ],
            )
            # 检查激活修订版
            self.assertTrue(revision_a.activated)
            self.assertEqual(1, revision_a.revisions.count())
            self.assertEqual(revision_a, revision_a.activated_revision)
            self.assertEqual(0, revision_a.deactivated_revisions.count())
        # 上传revisionB.txt覆盖revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionB.txt"), "rb") as file:
            revision_b = project.upload("1.txt", file, parent=dir3)
            # 检查文件相关的原文数
            self.assertEqual(5, revision_b.source_count)  # 新的翻译，不含空格有5行
            self.assertEqual(7, revision_b.sources().count())  # 新的翻译，含空格有7行
            # 之前有翻译且能找到一模一样原文的有3行
            self.assertEqual(3, revision_b.translated_source_count)
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.translations()]
                    for source in revision_b.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.tips()]
                    for source in revision_b.sources()
                ],
            )
            # 检查激活修订版
            revision_a.reload()
            self.assertFalse(revision_a.activated)
            self.assertTrue(revision_b.activated)
            self.assertEqual(2, revision_a.revisions.count())
            self.assertEqual(2, revision_b.revisions.count())
            self.assertEqual(revision_b, revision_a.activated_revision)
            self.assertEqual(revision_b, revision_b.activated_revision)
            self.assertEqual(1, revision_a.deactivated_revisions.count())
            self.assertEqual(1, revision_b.deactivated_revisions.count())
            self.assertIn(revision_a, revision_b.deactivated_revisions)
        self.assertEqual(5, File.objects.count())
        self.assertTrue(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_a.save_name)
        )
        self.assertTrue(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_b.save_name)
        )
        dir3.clear()
        self.assertEqual(2, File.objects.count())
        self.assertFalse(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_a.save_name)
        )
        self.assertFalse(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_b.save_name)
        )
        # == 删除文件会删除文件及相应修订版（根目录）==
        # /dir/dir2/1.txt 有两个修订版，删除dir
        # 上传revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionA.txt"), "rb") as file:
            revision_a = project.upload("1.txt", file, parent=dir2)
            # 检查文件相关的原文数
            self.assertEqual(4, revision_a.source_count)  # 不含空格有4行
            self.assertEqual(5, revision_a.sources().count())  # 含空格有5行
            # 给文章添加翻译
            for i, source in enumerate(revision_a.sources()):
                source.create_translation(str(i + 2), target, user=user)
                source.create_translation(
                    str(i), target, user=user
                )  # 再修改一遍，不会导致已翻译的计数出错
                source.create_tip(str(i), target, user=user)
            revision_a.reload()
            self.assertEqual(4, revision_a.translated_source_count)  # 不含空格有4行
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.translations()]
                    for source in revision_a.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.tips()]
                    for source in revision_a.sources()
                ],
            )
            # 检查激活修订版
            self.assertTrue(revision_a.activated)
            self.assertEqual(1, revision_a.revisions.count())
            self.assertEqual(revision_a, revision_a.activated_revision)
            self.assertEqual(0, revision_a.deactivated_revisions.count())
        # 上传revisionB.txt覆盖revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionB.txt"), "rb") as file:
            revision_b = project.upload("1.txt", file, parent=dir2)
            # 检查文件相关的原文数
            self.assertEqual(5, revision_b.source_count)  # 新的翻译，不含空格有5行
            self.assertEqual(7, revision_b.sources().count())  # 新的翻译，含空格有7行
            # 之前有翻译且能找到一模一样原文的有3行
            self.assertEqual(3, revision_b.translated_source_count)
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.translations()]
                    for source in revision_b.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.tips()]
                    for source in revision_b.sources()
                ],
            )
            # 检查激活修订版
            revision_a.reload()
            self.assertFalse(revision_a.activated)
            self.assertTrue(revision_b.activated)
            self.assertEqual(2, revision_a.revisions.count())
            self.assertEqual(2, revision_b.revisions.count())
            self.assertEqual(revision_b, revision_a.activated_revision)
            self.assertEqual(revision_b, revision_b.activated_revision)
            self.assertEqual(1, revision_a.deactivated_revisions.count())
            self.assertEqual(1, revision_b.deactivated_revisions.count())
            self.assertIn(revision_a, revision_b.deactivated_revisions)
        self.assertEqual(4, File.objects.count())
        self.assertTrue(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_a.save_name)
        )
        self.assertTrue(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_b.save_name)
        )
        dir1.clear()
        self.assertEqual(0, File.objects.count())
        self.assertFalse(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_a.save_name)
        )
        self.assertFalse(
            oss.is_exist(current_app.config["OSS_FILE_PREFIX"], revision_b.save_name)
        )

    def test_clear(self):
        """测试文件的删除操作"""
        """
        进行如下测试
        1. 删除文件夹下文件
        2. 删除文件夹下空文件夹
        3. 删除文件夹下包含文件的文件夹
        4. 删除根目录（None）下文件
        5. 删除根目录（None）下空文件夹
        6. 删除根目录（None）下包含文件的文件夹
        """
        with self.app.test_request_context():
            with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
                # =======创建测试用文件夹=======
                # 测试用项目、团队
                team = Team.create("t1")
                project = Project.create(
                    name="p1",
                    team=team,
                    source_language=Language.by_code("ja"),
                    target_languages=Language.by_code("zh-CN"),
                )
                # 上传文件
                file1 = project.upload("file1.txt", file)
                project.reload()
                # 创建两个文件夹
                dir1 = project.create_folder("dir1")
                dir2 = project.create_folder("dir2", parent=dir1)
                # 向dir2上传文件
                file2 = project.upload("file2.txt", file, parent=dir2)
                # 向dir1上传文件
                file3 = project.upload("file3.txt", file, parent=dir1)
                dir3 = project.create_folder("dir3", parent=dir1)
                # 为dir3再创建个文件夹,上传文件
                # 为dir2创建个文件夹
                # 为None创建个文件夹
                dir4 = project.create_folder("dir4", parent=dir3)
                file4 = project.upload("file4.txt", file, parent=dir3)
                dir5 = project.create_folder("dir5", parent=dir2)
                dir6 = project.create_folder("dir6")
                # 刷新
                project.reload()
                dir1.reload()
                dir2.reload()
                dir3.reload()
                dir4.reload()
                dir5.reload()
                dir6.reload()
                file1.reload()
                file2.reload()
                file3.reload()
                file4.reload()
                # 校对cache
                self.assertEqual(4, project.file_size)
                self.assertEqual(4, project.file_count)
                self.assertEqual(6, project.folder_count)
                self.assertEqual(3, dir1.file_size)
                self.assertEqual(3, dir1.file_count)
                self.assertEqual(4, dir1.folder_count)
                self.assertEqual(1, dir2.file_size)
                self.assertEqual(1, dir2.file_count)
                self.assertEqual(1, dir2.folder_count)
                self.assertEqual(1, dir3.file_size)
                self.assertEqual(1, dir3.file_count)
                self.assertEqual(1, dir3.folder_count)
                self.assertEqual(0, dir4.file_size)
                self.assertEqual(0, dir4.file_count)
                self.assertEqual(0, dir4.folder_count)
                self.assertEqual(0, dir5.file_size)
                self.assertEqual(0, dir5.file_count)
                self.assertEqual(0, dir5.folder_count)
                self.assertEqual(0, dir6.file_size)
                self.assertEqual(0, dir6.file_count)
                self.assertEqual(0, dir6.folder_count)
                # 校对祖先
                self.assertEqual(None, file1.parent)
                self.assertEqual([], file1.ancestors)
                self.assertEqual(None, dir1.parent)
                self.assertEqual([], dir1.ancestors)
                self.assertEqual(dir1, dir2.parent)
                self.assertEqual([dir1], dir2.ancestors)
                self.assertEqual(dir2, file2.parent)
                self.assertEqual([dir1, dir2], file2.ancestors)
                self.assertEqual(dir1, file3.parent)
                self.assertEqual([dir1], file3.ancestors)
                self.assertEqual(dir1, dir3.parent)
                self.assertEqual([dir1], dir3.ancestors)
                self.assertEqual(None, dir6.parent)
                self.assertEqual([], dir6.ancestors)
                self.assertEqual(dir2, dir5.parent)
                self.assertEqual([dir1, dir2], dir5.ancestors)
                self.assertEqual(dir3, file4.parent)
                self.assertEqual([dir1, dir3], file4.ancestors)
                self.assertEqual(dir3, dir4.parent)
                self.assertEqual([dir1, dir3], dir4.ancestors)
                # =======开始测试=======
                """
                初始文件结构
                 |         |
                 - file1   - dir1
                 - dir6       |
                              - file3
                              - dir3
                                  |
                                  - file4
                                  - dir4
                              - dir2
                                  |
                                  - file2
                                  - dir5
                """
                file1_save_name = file1.save_name
                file2_save_name = file2.save_name
                file3_save_name = file3.save_name
                file4_save_name = file4.save_name
                # 检查oss文件状态
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file1_save_name)
                )
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file2_save_name)
                )
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file3_save_name)
                )
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file4_save_name)
                )
                # == 删除文件夹下文件 ==
                """
                 |         |
                 - file1   - dir1
                 - dir6       |
                              - file3
                              - dir3
                                  |
                                  - file4
                                  - dir4
                              - dir2
                                  |
                                  - dir5
                """
                file2.clear()
                # 检查oss文件状态
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file1_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file2_save_name)
                )
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file3_save_name)
                )
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file4_save_name)
                )
                # 刷新
                project.reload()
                dir1.reload()
                dir2.reload()
                dir3.reload()
                dir4.reload()
                dir5.reload()
                dir6.reload()
                file1.reload()
                file3.reload()
                file4.reload()
                # 校对cache
                self.assertEqual(3, project.file_size)
                self.assertEqual(3, project.file_count)
                self.assertEqual(6, project.folder_count)
                self.assertEqual(2, dir1.file_size)
                self.assertEqual(2, dir1.file_count)
                self.assertEqual(4, dir1.folder_count)
                self.assertEqual(0, dir2.file_size)
                self.assertEqual(0, dir2.file_count)
                self.assertEqual(1, dir2.folder_count)
                self.assertEqual(1, dir3.file_size)
                self.assertEqual(1, dir3.file_count)
                self.assertEqual(1, dir3.folder_count)
                self.assertEqual(0, dir4.file_size)
                self.assertEqual(0, dir4.file_count)
                self.assertEqual(0, dir4.folder_count)
                self.assertEqual(0, dir5.file_size)
                self.assertEqual(0, dir5.file_count)
                self.assertEqual(0, dir5.folder_count)
                self.assertEqual(0, dir6.file_size)
                self.assertEqual(0, dir6.file_count)
                self.assertEqual(0, dir6.folder_count)
                # == 删除文件夹下空文件夹 ==
                """
                 |         |
                 - file1   - dir1
                 - dir6       |
                              - file3
                              - dir3
                                  |
                                  - file4
                                  - dir4
                              - dir2
                """
                dir5.clear()
                # 检查oss文件状态
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file1_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file2_save_name)
                )
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file3_save_name)
                )
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file4_save_name)
                )
                # 刷新
                project.reload()
                dir1.reload()
                dir2.reload()
                dir3.reload()
                dir4.reload()
                dir6.reload()
                file1.reload()
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                file3.reload()
                file4.reload()
                # 校对cache
                self.assertEqual(3, project.file_size)
                self.assertEqual(3, project.file_count)
                self.assertEqual(5, project.folder_count)
                self.assertEqual(2, dir1.file_size)
                self.assertEqual(2, dir1.file_count)
                self.assertEqual(3, dir1.folder_count)
                self.assertEqual(0, dir2.file_size)
                self.assertEqual(0, dir2.file_count)
                self.assertEqual(0, dir2.folder_count)
                self.assertEqual(1, dir3.file_size)
                self.assertEqual(1, dir3.file_count)
                self.assertEqual(1, dir3.folder_count)
                self.assertEqual(0, dir4.file_size)
                self.assertEqual(0, dir4.file_count)
                self.assertEqual(0, dir4.folder_count)
                self.assertEqual(0, dir6.file_size)
                self.assertEqual(0, dir6.file_count)
                self.assertEqual(0, dir6.folder_count)
                # == 删除文件夹下包含文件的文件夹 ==
                """
                 |         |
                 - file1   - dir1
                 - dir6       |
                              - file3
                              - dir2
                """
                dir3.clear()
                # 检查oss文件状态
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file1_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file2_save_name)
                )
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file3_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file4_save_name)
                )
                # 刷新
                project.reload()
                dir1.reload()
                dir2.reload()
                with self.assertRaises(DoesNotExist):
                    dir3.reload()
                with self.assertRaises(DoesNotExist):
                    dir4.reload()
                dir6.reload()
                file1.reload()
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                file3.reload()
                with self.assertRaises(DoesNotExist):
                    file4.reload()
                # 校对cache
                self.assertEqual(2, project.file_size)
                self.assertEqual(2, project.file_count)
                self.assertEqual(3, project.folder_count)
                self.assertEqual(1, dir1.file_size)
                self.assertEqual(1, dir1.file_count)
                self.assertEqual(1, dir1.folder_count)
                self.assertEqual(0, dir2.file_size)
                self.assertEqual(0, dir2.file_count)
                self.assertEqual(0, dir2.folder_count)
                self.assertEqual(0, dir6.file_size)
                self.assertEqual(0, dir6.file_count)
                self.assertEqual(0, dir6.folder_count)
                # == 删除None下文件 ==
                """
                 |         |
                 |         - dir1
                 - dir6       |
                              - file3
                              - dir2
                """
                file1.clear()
                # 检查oss文件状态
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file1_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file2_save_name)
                )
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file3_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file4_save_name)
                )
                # 刷新
                project.reload()
                dir1.reload()
                dir2.reload()
                with self.assertRaises(DoesNotExist):
                    dir3.reload()
                with self.assertRaises(DoesNotExist):
                    dir4.reload()
                dir6.reload()
                with self.assertRaises(DoesNotExist):
                    file1.reload()
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                file3.reload()
                with self.assertRaises(DoesNotExist):
                    file4.reload()
                # 校对cache
                self.assertEqual(1, project.file_size)
                self.assertEqual(1, project.file_count)
                self.assertEqual(3, project.folder_count)
                self.assertEqual(1, dir1.file_size)
                self.assertEqual(1, dir1.file_count)
                self.assertEqual(1, dir1.folder_count)
                self.assertEqual(0, dir2.file_size)
                self.assertEqual(0, dir2.file_count)
                self.assertEqual(0, dir2.folder_count)
                self.assertEqual(0, dir6.file_size)
                self.assertEqual(0, dir6.file_count)
                self.assertEqual(0, dir6.folder_count)
                # == 删除None下空文件夹 ==
                """
                           |
                           - dir1
                              |
                              - file3
                              - dir2
                """
                dir6.clear()
                # 检查oss文件状态
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file1_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file2_save_name)
                )
                self.assertTrue(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file3_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file4_save_name)
                )
                # 刷新
                project.reload()
                dir1.reload()
                dir2.reload()
                with self.assertRaises(DoesNotExist):
                    dir3.reload()
                with self.assertRaises(DoesNotExist):
                    dir4.reload()
                with self.assertRaises(DoesNotExist):
                    dir6.reload()
                with self.assertRaises(DoesNotExist):
                    file1.reload()
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                file3.reload()
                with self.assertRaises(DoesNotExist):
                    file4.reload()
                # 校对cache
                self.assertEqual(1, project.file_size)
                self.assertEqual(1, project.file_count)
                self.assertEqual(2, project.folder_count)
                self.assertEqual(1, dir1.file_size)
                self.assertEqual(1, dir1.file_count)
                self.assertEqual(1, dir1.folder_count)
                self.assertEqual(0, dir2.file_size)
                self.assertEqual(0, dir2.file_count)
                self.assertEqual(0, dir2.folder_count)
                # == 删除None下包含文件的文件夹 ==
                """
                删光啦
                """
                dir1.clear()
                # 检查oss文件状态
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file1_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file2_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file3_save_name)
                )
                self.assertFalse(
                    oss.is_exist(current_app.config["OSS_FILE_PREFIX"], file4_save_name)
                )
                # 刷新
                project.reload()
                with self.assertRaises(DoesNotExist):
                    dir1.reload()
                with self.assertRaises(DoesNotExist):
                    dir2.reload()
                with self.assertRaises(DoesNotExist):
                    dir3.reload()
                with self.assertRaises(DoesNotExist):
                    dir4.reload()
                with self.assertRaises(DoesNotExist):
                    dir6.reload()
                with self.assertRaises(DoesNotExist):
                    file1.reload()
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                with self.assertRaises(DoesNotExist):
                    file3.reload()
                with self.assertRaises(DoesNotExist):
                    file4.reload()
                # 校对cache
                self.assertEqual(0, project.file_size)
                self.assertEqual(0, project.file_count)
                self.assertEqual(0, project.folder_count)

    def test_create_file_name_duplicate(self):
        """
        测试创建文件，名称重复的处理
        与文件夹重名
        """
        with self.app.test_request_context():
            # 测试用项目、团队
            team = Team.create("t1")
            project = Project.create(
                name="p1",
                team=team,
                source_language=Language.by_code("ja"),
                target_languages=Language.by_code("zh-CN"),
            )
            # 创建测试文件夹、文件
            text_file = project.create_file("1.txt")
            image_file = project.create_file("1.jpg")
            dir1 = project.create_folder("dir.txt")
            """
                |
                - text_file(1.txt)
                - image_file(1.jpg)
                - dir1(dir.txt)
            """
            project.reload()
            self.assertEqual(2, project.file_count)
            self.assertEqual(1, project.folder_count)
            # === 测试开始 ===
            # == 与文件夹重名，报错 ==
            # 再次与dir1(dir.txt)创建同名文件(dir.txt)，报错
            with self.assertRaises(FilenameDuplicateError):
                project.create_file("dir.txt")
            project.reload()
            self.assertEqual(3, File.objects().count())
            self.assertEqual(2, project.file_count)
            self.assertEqual(1, project.folder_count)

            # == 与文本重名，返回新修订版 ==
            new_text_file = project.create_file("1.txt")
            project.reload()
            self.assertEqual(4, File.objects().count())
            self.assertEqual(2, project.file_count)
            self.assertEqual(1, project.folder_count)
            self.assertNotEqual(text_file, new_text_file)

            # == 与图片重名，返回原图片 ==
            new_image_file = project.create_file("1.jpg")
            project.reload()
            self.assertEqual(4, File.objects().count())
            self.assertEqual(2, project.file_count)
            self.assertEqual(1, project.folder_count)
            self.assertEqual(image_file, new_image_file)

            # == 在dir1下创建同名dir.txt没问题 ==
            # 再次与dir1(dir.txt)创建同名文件(dir.txt)，报错
            dir2 = project.create_file("dir.txt", parent=dir1)
            project.reload()
            self.assertEqual(5, File.objects().count())
            self.assertEqual(3, project.file_count)
            self.assertEqual(1, project.folder_count)
            self.assertEqual(dir1, dir2.parent)
            self.assertNotEqual(dir1, dir2)

            # == 在dir1下创建同名1.txt没问题 ==
            text_file2 = project.create_file("1.txt", parent=dir1)
            project.reload()
            self.assertEqual(6, File.objects().count())
            self.assertEqual(4, project.file_count)
            self.assertEqual(1, project.folder_count)
            self.assertEqual(dir1, text_file2.parent)
            self.assertNotEqual(text_file, text_file2)

            # == 在dir1下创建同名1.jpg没问题 ==
            image_file2 = project.create_file("1.jpg", parent=dir1)
            project.reload()
            self.assertEqual(7, File.objects().count())
            self.assertEqual(5, project.file_count)
            self.assertEqual(1, project.folder_count)
            self.assertEqual(dir1, image_file2.parent)
            self.assertNotEqual(image_file, image_file2)

            # == 创建不同名2.jpg没问题 ==
            image_file2 = project.create_file("2.jpg")
            project.reload()
            self.assertEqual(8, File.objects().count())
            self.assertEqual(6, project.file_count)
            self.assertEqual(1, project.folder_count)

            # == 创建不同名2.txt没问题 ==
            image_file2 = project.create_file("2.txt")
            project.reload()
            self.assertEqual(9, File.objects().count())
            self.assertEqual(7, project.file_count)
            self.assertEqual(1, project.folder_count)

    def test_create_folder_name_duplicate(self):
        """测试创建文件夹，名称重复"""
        with self.app.test_request_context():
            # 测试用项目、团队
            team = Team.create("t1")
            project = Project.create(
                name="p1",
                team=team,
                source_language=Language.by_code("ja"),
                target_languages=Language.by_code("zh-CN"),
            )
            # 创建测试用文件、文件夹
            file1 = project.create_file("1.txt")
            dir1 = project.create_folder("dir.txt")
            """
                |
                - file1(1.txt)
                - dir1(dir.txt)
            """
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(1, project.folder_count)
            # === 开始测试 ===
            # == 与文件夹(dir.txt)同名，报错 ==
            with self.assertRaises(FilenameDuplicateError):
                project.create_folder("dir.txt")
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(1, project.folder_count)
            # == 与文件(1.txt)同名，报错 ==
            with self.assertRaises(FilenameDuplicateError):
                project.create_folder("1.txt")
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(1, project.folder_count)
            # == 创建非同名文件夹(dir)，没有问题 ==
            project.create_folder("dir")
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(2, project.folder_count)
            # == 给dir1创建同名文件夹(dir.txt)，没有问题 ==
            project.create_folder("dir.txt", parent=dir1)
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(3, project.folder_count)
            # == 给dir1创建同名文件(1.txt)，没有问题 ==
            project.create_folder("1.txt", parent=dir1)
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(4, project.folder_count)

    def test_create_file_and_folder(self):
        """测试上传文件/创建文件夹是否改变相关cache"""
        with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
            # 测试用项目、团队
            team = Team.create("t1")
            project = Project.create(
                name="p1",
                team=team,
                source_language=Language.by_code("ja"),
                target_languages=Language.by_code("zh-CN"),
            )
            """
             |
             - file1
            """
            # 上传文件
            file1 = project.upload("1.txt", file)
            project.reload()
            # 校对cache
            self.assertEqual(1, project.file_size)
            self.assertEqual(1, project.file_count)
            self.assertEqual(0, project.folder_count)
            # 校对祖先
            self.assertEqual(None, file1.parent)
            self.assertEqual([], file1.ancestors)
            # 创建两个文件夹
            dir1 = project.create_folder("dir1")
            dir2 = project.create_folder("dir2", parent=dir1)
            # 向dir2上传文件
            file2 = project.upload("1.txt", file, parent=dir2)
            """
             |         |
             - file1   - dir1
                          |
                          - dir2
                              |
                              - file2
            """
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            file1.reload()
            file2.reload()
            # 校对cache
            self.assertEqual(2, project.file_size)
            self.assertEqual(2, project.file_count)
            self.assertEqual(2, project.folder_count)
            self.assertEqual(1, dir1.file_size)
            self.assertEqual(1, dir1.file_count)
            self.assertEqual(1, dir1.folder_count)
            self.assertEqual(1, dir2.file_size)
            self.assertEqual(1, dir2.file_count)
            self.assertEqual(0, dir2.folder_count)
            # 校对祖先
            self.assertEqual(None, file1.parent)
            self.assertEqual([], file1.ancestors)
            self.assertEqual(None, dir1.parent)
            self.assertEqual([], dir1.ancestors)
            self.assertEqual(dir1, dir2.parent)
            self.assertEqual([dir1], dir2.ancestors)
            self.assertEqual(dir2, file2.parent)
            self.assertEqual([dir1, dir2], file2.ancestors)
            """
             |         |
             - file1   - dir1
                          |
                          - file3
                          - dir2
                              |
                              - file2
            """
            # 向dir1上传文件
            file3 = project.upload("1.txt", file, parent=dir1)
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            # 校对cache
            self.assertEqual(3, project.file_size)
            self.assertEqual(3, project.file_count)
            self.assertEqual(2, project.folder_count)
            self.assertEqual(2, dir1.file_size)
            self.assertEqual(2, dir1.file_count)
            self.assertEqual(1, dir1.folder_count)
            self.assertEqual(1, dir2.file_size)
            self.assertEqual(1, dir2.file_count)
            self.assertEqual(0, dir2.folder_count)
            # 校对祖先
            self.assertEqual(None, file1.parent)
            self.assertEqual([], file1.ancestors)
            self.assertEqual(None, dir1.parent)
            self.assertEqual([], dir1.ancestors)
            self.assertEqual(dir1, dir2.parent)
            self.assertEqual([dir1], dir2.ancestors)
            self.assertEqual(dir2, file2.parent)
            self.assertEqual([dir1, dir2], file2.ancestors)
            self.assertEqual(dir1, file3.parent)
            self.assertEqual([dir1], file3.ancestors)
            # 为dir1再创建个文件夹
            """
             |         |
             - file1   - dir1
                          |
                          - file3
                          - dir3
                          - dir2
                              |
                              - file2
            """
            dir3 = project.create_folder("dir3", parent=dir1)
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            # 校对cache
            self.assertEqual(3, project.file_size)
            self.assertEqual(3, project.file_count)
            self.assertEqual(3, project.folder_count)
            self.assertEqual(2, dir1.file_size)
            self.assertEqual(2, dir1.file_count)
            self.assertEqual(2, dir1.folder_count)
            self.assertEqual(1, dir2.file_size)
            self.assertEqual(1, dir2.file_count)
            self.assertEqual(0, dir2.folder_count)
            self.assertEqual(0, dir3.file_size)
            self.assertEqual(0, dir3.file_count)
            self.assertEqual(0, dir3.folder_count)
            # 校对祖先
            self.assertEqual(None, file1.parent)
            self.assertEqual([], file1.ancestors)
            self.assertEqual(None, dir1.parent)
            self.assertEqual([], dir1.ancestors)
            self.assertEqual(dir1, dir2.parent)
            self.assertEqual([dir1], dir2.ancestors)
            self.assertEqual(dir2, file2.parent)
            self.assertEqual([dir1, dir2], file2.ancestors)
            self.assertEqual(dir1, file3.parent)
            self.assertEqual([dir1], file3.ancestors)
            self.assertEqual(dir1, dir3.parent)
            self.assertEqual([dir1], dir3.ancestors)
            # 为dir3再创建个文件夹,上传文件
            # 为dir2创建个文件夹
            # 为None创建个文件夹
            """
             |         |
             - file1   - dir1
             - dir6       |
                          - file3
                          - dir3
                              |
                              - file4
                              - dir4
                          - dir2
                              |
                              - file2
                              - dir5
            """
            dir4 = project.create_folder("dir4", parent=dir3)
            file4 = project.upload("1.txt", file, parent=dir3)
            dir5 = project.create_folder("dir5", parent=dir2)
            dir6 = project.create_folder("dir6")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对cache
            self.assertEqual(4, project.file_size)
            self.assertEqual(4, project.file_count)
            self.assertEqual(6, project.folder_count)
            self.assertEqual(3, dir1.file_size)
            self.assertEqual(3, dir1.file_count)
            self.assertEqual(4, dir1.folder_count)
            self.assertEqual(1, dir2.file_size)
            self.assertEqual(1, dir2.file_count)
            self.assertEqual(1, dir2.folder_count)
            self.assertEqual(1, dir3.file_size)
            self.assertEqual(1, dir3.file_count)
            self.assertEqual(1, dir3.folder_count)
            # 校对祖先
            self.assertEqual(None, file1.parent)
            self.assertEqual([], file1.ancestors)
            self.assertEqual(None, dir1.parent)
            self.assertEqual([], dir1.ancestors)
            self.assertEqual(dir1, dir2.parent)
            self.assertEqual([dir1], dir2.ancestors)
            self.assertEqual(dir2, file2.parent)
            self.assertEqual([dir1, dir2], file2.ancestors)
            self.assertEqual(dir1, file3.parent)
            self.assertEqual([dir1], file3.ancestors)
            self.assertEqual(dir1, dir3.parent)
            self.assertEqual([dir1], dir3.ancestors)
            self.assertEqual(None, dir6.parent)
            self.assertEqual([], dir6.ancestors)
            self.assertEqual(dir2, dir5.parent)
            self.assertEqual([dir1, dir2], dir5.ancestors)
            self.assertEqual(dir3, file4.parent)
            self.assertEqual([dir1, dir3], file4.ancestors)
            self.assertEqual(dir3, dir4.parent)
            self.assertEqual([dir1, dir3], dir4.ancestors)

    def test_move_to_error(self):
        with self.app.test_request_context():
            with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
                # 测试用项目、团队
                team = Team.create("t1")
                project = Project.create(
                    name="p1",
                    team=team,
                    source_language=Language.by_code("ja"),
                    target_languages=Language.by_code("zh-CN"),
                )
                # 上传文件
                file1 = project.upload("file1.txt", file)
                project.reload()
                # 创建两个文件夹
                dir1 = project.create_folder("dir1")
                dir2 = project.create_folder("dir2", parent=dir1)
                # 向dir2上传文件
                file2 = project.upload("file2.txt", file, parent=dir2)
                # 向dir1上传文件
                file3 = project.upload("file3.txt", file, parent=dir1)
                dir3 = project.create_folder("dir3", parent=dir1)
                # 为dir3再创建个文件夹,上传文件
                # 为dir2创建个文件夹
                # 为None创建个文件夹
                dir4 = project.create_folder("dir4", parent=dir3)
                file4 = project.upload("1.txt", file, parent=dir3)
                dir5 = project.create_folder("1.txt", parent=dir2)
                dir6 = project.create_folder("dir6")
                # 刷新
                project.reload()
                dir1.reload()
                dir2.reload()
                dir3.reload()
                dir4.reload()
                dir5.reload()
                dir6.reload()
                file1.reload()
                file2.reload()
                file3.reload()
                file4.reload()
                # 校对cache
                self.assertEqual(4, project.file_size)
                self.assertEqual(4, project.file_count)
                self.assertEqual(6, project.folder_count)
                self.assertEqual(3, dir1.file_size)
                self.assertEqual(3, dir1.file_count)
                self.assertEqual(4, dir1.folder_count)
                self.assertEqual(1, dir2.file_size)
                self.assertEqual(1, dir2.file_count)
                self.assertEqual(1, dir2.folder_count)
                self.assertEqual(1, dir3.file_size)
                self.assertEqual(1, dir3.file_count)
                self.assertEqual(1, dir3.folder_count)
                """
                初始文件结构
                 |         |
                 - file1   - dir1
                 - dir6       |
                              - file3
                              - dir3
                                  |
                                  - file4（名字也叫1.txt）
                                  - dir4
                              - dir2
                                  |
                                  - file2
                                  - dir5（名字也叫1.txt）
                """
                # 不能移动到文件
                with self.assertRaises(FolderNotExistError):
                    dir1.move_to(file1)
                # 不能移动到子目录
                with self.assertRaises(FileParentIsSubFolderError):
                    dir1.move_to(dir3)
                # 不能移动原目录
                with self.assertRaises(FileParentIsSameError):
                    file1.move_to(None)
                with self.assertRaises(FileParentIsSameError):
                    file2.move_to(dir2)
                # 同名不能移动
                with self.assertRaises(FilenameDuplicateError):
                    file4.move_to(dir2)
                with self.assertRaises(FilenameDuplicateError):
                    dir5.move_to(dir3)
                # 刷新
                project.reload()
                dir1.reload()
                dir2.reload()
                dir3.reload()
                dir4.reload()
                dir5.reload()
                dir6.reload()
                file1.reload()
                file2.reload()
                file3.reload()
                file4.reload()
                # 校对cache
                self.assertEqual(4, project.file_size)
                self.assertEqual(4, project.file_count)
                self.assertEqual(6, project.folder_count)
                self.assertEqual(3, dir1.file_size)
                self.assertEqual(3, dir1.file_count)
                self.assertEqual(4, dir1.folder_count)
                self.assertEqual(1, dir2.file_size)
                self.assertEqual(1, dir2.file_count)
                self.assertEqual(1, dir2.folder_count)
                self.assertEqual(1, dir3.file_size)
                self.assertEqual(1, dir3.file_count)
                self.assertEqual(1, dir3.folder_count)

    def test_move_to_other_project_error(self):
        """测试移动到错误的parent"""
        with self.app.test_request_context():
            with open(os.path.join(TEST_FILE_PATH, "revisionA.txt"), "rb") as file:
                team = Team.create("t1")
                # 另一个项目
                project_out = Project.create("po", team=team)
                dir_out = project_out.create_folder("diro")
                file_out = project_out.upload("fo.txt", file)
                # 本项目
                project = Project.create("p1", team=team)
                dir1 = project.create_folder("dir1")
                file1 = project.upload("f1.txt", file)
                self.assertEqual(0, dir1.file_count)
                file1.move_to(dir1)
                dir1.reload()
                self.assertEqual(1, dir1.file_count)
                # 错误的parent
                with self.assertRaises(FolderNotExistError):
                    file1.move_to(file_out)
                with self.assertRaises(FolderNotExistError):
                    file1.move_to(dir_out)

    def test_move_to(self):
        """测试移动"""
        """
        共有以下测试
        1. 移动文件到None
        2. 平级移动文件
        3. 从None移动文件
        4. 从None移动文件夹
        5. 移动文件夹到None
        6. 平级移动文件夹
        """

        with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
            # =======创建测试用文件夹=======
            # 测试用项目、团队
            team = Team.create("t1")
            project = Project.create(
                name="p1",
                team=team,
                source_language=Language.by_code("ja"),
                target_languages=Language.by_code("zh-CN"),
            )
            # 上传文件
            file1 = project.upload("file1.txt", file)
            project.reload()
            # 创建两个文件夹
            dir1 = project.create_folder("dir1")
            dir2 = project.create_folder("dir2", parent=dir1)
            # 向dir2上传文件
            file2 = project.upload("file2.txt", file, parent=dir2)
            # 向dir1上传文件
            file3 = project.upload("file3.txt", file, parent=dir1)
            dir3 = project.create_folder("dir3", parent=dir1)
            # 为dir3再创建个文件夹,上传文件
            # 为dir2创建个文件夹
            # 为None创建个文件夹
            dir4 = project.create_folder("dir4", parent=dir3)
            file4 = project.upload("file4.txt", file, parent=dir3)
            dir5 = project.create_folder("dir5", parent=dir2)
            dir6 = project.create_folder("dir6")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对cache
            self.assertEqual(4, project.file_size)
            self.assertEqual(4, project.file_count)
            self.assertEqual(6, project.folder_count)
            self.assertEqual(3, dir1.file_size)
            self.assertEqual(3, dir1.file_count)
            self.assertEqual(4, dir1.folder_count)
            self.assertEqual(1, dir2.file_size)
            self.assertEqual(1, dir2.file_count)
            self.assertEqual(1, dir2.folder_count)
            self.assertEqual(1, dir3.file_size)
            self.assertEqual(1, dir3.file_count)
            self.assertEqual(1, dir3.folder_count)
            self.assertEqual(0, dir4.file_size)
            self.assertEqual(0, dir4.file_count)
            self.assertEqual(0, dir4.folder_count)
            self.assertEqual(0, dir5.file_size)
            self.assertEqual(0, dir5.file_count)
            self.assertEqual(0, dir5.folder_count)
            self.assertEqual(0, dir6.file_size)
            self.assertEqual(0, dir6.file_count)
            self.assertEqual(0, dir6.folder_count)
            # 校对祖先
            self.check_ancestors([], file1)
            self.check_ancestors([], dir1)
            self.check_ancestors([dir1], dir2)
            self.check_ancestors([dir1, dir2], file2)
            self.check_ancestors([dir1], file3)
            self.check_ancestors([dir1], dir3)
            self.check_ancestors([], dir6)
            self.check_ancestors([dir1, dir2], dir5)
            self.check_ancestors([dir1, dir3], file4)
            self.check_ancestors([dir1, dir3], dir4)
            # =======开始测试=======
            """
            初始文件结构
             |         |
             - file1   - dir1
             - dir6       |
                          - file3
                          - dir3
                              |
                              - file4
                              - dir4
                          - dir2
                              |
                              - file2
                              - dir5
            """
            # == 移动文件到None ==
            file3.move_to(None)
            """
             |         |
             - file1   - dir1
             - dir6       |
             - file3      - dir3
                              |
                              - file4
                              - dir4
                          - dir2
                              |
                              - file2
                              - dir5
            """
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对cache
            self.assertEqual(4, project.file_size)
            self.assertEqual(4, project.file_count)
            self.assertEqual(6, project.folder_count)
            self.assertEqual(2, dir1.file_size)
            self.assertEqual(2, dir1.file_count)
            self.assertEqual(4, dir1.folder_count)
            self.assertEqual(1, dir2.file_size)
            self.assertEqual(1, dir2.file_count)
            self.assertEqual(1, dir2.folder_count)
            self.assertEqual(1, dir3.file_size)
            self.assertEqual(1, dir3.file_count)
            self.assertEqual(1, dir3.folder_count)
            self.assertEqual(0, dir4.file_size)
            self.assertEqual(0, dir4.file_count)
            self.assertEqual(0, dir4.folder_count)
            self.assertEqual(0, dir5.file_size)
            self.assertEqual(0, dir5.file_count)
            self.assertEqual(0, dir5.folder_count)
            self.assertEqual(0, dir6.file_size)
            self.assertEqual(0, dir6.file_count)
            self.assertEqual(0, dir6.folder_count)
            # 校对祖先
            self.check_ancestors([], file1)
            self.check_ancestors([], dir1)
            self.check_ancestors([dir1], dir2)
            self.check_ancestors([dir1, dir2], file2)
            self.check_ancestors([], file3)
            self.check_ancestors([dir1], dir3)
            self.check_ancestors([], dir6)
            self.check_ancestors([dir1, dir2], dir5)
            self.check_ancestors([dir1, dir3], file4)
            self.check_ancestors([dir1, dir3], dir4)
            # == 平级移动文件 ==
            file4.move_to(dir2)
            """
             |         |
             - file1   - dir1
             - dir6       |
             - file3      - dir3
                              |
                              - dir4
                          - dir2
                              |
                              - file2
                              - dir5
                              - file4
            """
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对cache
            self.assertEqual(4, project.file_size)
            self.assertEqual(4, project.file_count)
            self.assertEqual(6, project.folder_count)
            self.assertEqual(2, dir1.file_size)
            self.assertEqual(2, dir1.file_count)
            self.assertEqual(4, dir1.folder_count)
            self.assertEqual(2, dir2.file_size)
            self.assertEqual(2, dir2.file_count)
            self.assertEqual(1, dir2.folder_count)
            self.assertEqual(0, dir3.file_size)
            self.assertEqual(0, dir3.file_count)
            self.assertEqual(1, dir3.folder_count)
            self.assertEqual(0, dir4.file_size)
            self.assertEqual(0, dir4.file_count)
            self.assertEqual(0, dir4.folder_count)
            self.assertEqual(0, dir5.file_size)
            self.assertEqual(0, dir5.file_count)
            self.assertEqual(0, dir5.folder_count)
            self.assertEqual(0, dir6.file_size)
            self.assertEqual(0, dir6.file_count)
            self.assertEqual(0, dir6.folder_count)
            # 校对祖先
            self.check_ancestors([], file1)
            self.check_ancestors([], dir1)
            self.check_ancestors([dir1], dir2)
            self.check_ancestors([dir1, dir2], file2)
            self.check_ancestors([], file3)
            self.check_ancestors([dir1], dir3)
            self.check_ancestors([], dir6)
            self.check_ancestors([dir1, dir2], dir5)
            self.check_ancestors([dir1, dir2], file4)
            self.check_ancestors([dir1, dir3], dir4)
            # == 从None移动文件 ==
            file3.move_to(dir3)
            file1.move_to(dir6)
            """
             |         |
             - dir6   - dir1
                 |        |
                 - file1  - dir3
                              |
                              - dir4
                              - file3
                          - dir2
                              |
                              - file2
                              - dir5
                              - file4
            """
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对cache
            self.assertEqual(4, project.file_size)
            self.assertEqual(4, project.file_count)
            self.assertEqual(6, project.folder_count)
            self.assertEqual(3, dir1.file_size)
            self.assertEqual(3, dir1.file_count)
            self.assertEqual(4, dir1.folder_count)
            self.assertEqual(2, dir2.file_size)
            self.assertEqual(2, dir2.file_count)
            self.assertEqual(1, dir2.folder_count)
            self.assertEqual(1, dir3.file_size)
            self.assertEqual(1, dir3.file_count)
            self.assertEqual(1, dir3.folder_count)
            self.assertEqual(0, dir4.file_size)
            self.assertEqual(0, dir4.file_count)
            self.assertEqual(0, dir4.folder_count)
            self.assertEqual(0, dir5.file_size)
            self.assertEqual(0, dir5.file_count)
            self.assertEqual(0, dir5.folder_count)
            self.assertEqual(1, dir6.file_size)
            self.assertEqual(1, dir6.file_count)
            self.assertEqual(0, dir6.folder_count)
            # 校对祖先
            self.check_ancestors([dir6], file1)
            self.check_ancestors([], dir1)
            self.check_ancestors([dir1], dir2)
            self.check_ancestors([dir1, dir2], file2)
            self.check_ancestors([dir1, dir3], file3)
            self.check_ancestors([dir1], dir3)
            self.check_ancestors([], dir6)
            self.check_ancestors([dir1, dir2], dir5)
            self.check_ancestors([dir1, dir2], file4)
            self.check_ancestors([dir1, dir3], dir4)
            # == 从None移动文件夹 ==
            dir7 = project.create_folder("dir7", parent=dir6)
            dir6.move_to(dir1)
            """
                       |
                       - dir1
                          |
                          - dir3
                              |
                              - dir4
                              - file3
                          - dir2
                              |
                              - file2
                              - dir5
                              - file4
                          - dir6
                              |
                              - file1
                              - dir7
            """
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            dir7.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对cache
            self.assertEqual(4, project.file_size)
            self.assertEqual(4, project.file_count)
            self.assertEqual(7, project.folder_count)
            self.assertEqual(4, dir1.file_size)
            self.assertEqual(4, dir1.file_count)
            self.assertEqual(6, dir1.folder_count)
            self.assertEqual(2, dir2.file_size)
            self.assertEqual(2, dir2.file_count)
            self.assertEqual(1, dir2.folder_count)
            self.assertEqual(1, dir3.file_size)
            self.assertEqual(1, dir3.file_count)
            self.assertEqual(1, dir3.folder_count)
            self.assertEqual(0, dir4.file_size)
            self.assertEqual(0, dir4.file_count)
            self.assertEqual(0, dir4.folder_count)
            self.assertEqual(0, dir5.file_size)
            self.assertEqual(0, dir5.file_count)
            self.assertEqual(0, dir5.folder_count)
            self.assertEqual(1, dir6.file_size)
            self.assertEqual(1, dir6.file_count)
            self.assertEqual(1, dir6.folder_count)
            # 校对祖先
            self.check_ancestors([dir1, dir6], file1)
            self.check_ancestors([dir1, dir6], dir7)
            self.check_ancestors([], dir1)
            self.check_ancestors([dir1], dir2)
            self.check_ancestors([dir1, dir2], file2)
            self.check_ancestors([dir1, dir3], file3)
            self.check_ancestors([dir1], dir3)
            self.check_ancestors([dir1], dir6)
            self.check_ancestors([dir1, dir2], dir5)
            self.check_ancestors([dir1, dir2], file4)
            self.check_ancestors([dir1, dir3], dir4)
            # == 移动文件夹到None ==
            dir2.move_to(None)
            """
            |            |
            - dir2       - dir1
               |             |
               - file2       - dir3
               - dir5            |
               - file4           - dir4
                                 - file3
                             - dir6
                                 |
                                 - file1
                                 - dir7
            """
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            dir7.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对cache
            self.assertEqual(4, project.file_size)
            self.assertEqual(4, project.file_count)
            self.assertEqual(7, project.folder_count)
            self.assertEqual(2, dir1.file_size)
            self.assertEqual(2, dir1.file_count)
            self.assertEqual(4, dir1.folder_count)
            self.assertEqual(2, dir2.file_size)
            self.assertEqual(2, dir2.file_count)
            self.assertEqual(1, dir2.folder_count)
            self.assertEqual(1, dir3.file_size)
            self.assertEqual(1, dir3.file_count)
            self.assertEqual(1, dir3.folder_count)
            self.assertEqual(0, dir4.file_size)
            self.assertEqual(0, dir4.file_count)
            self.assertEqual(0, dir4.folder_count)
            self.assertEqual(0, dir5.file_size)
            self.assertEqual(0, dir5.file_count)
            self.assertEqual(0, dir5.folder_count)
            self.assertEqual(1, dir6.file_size)
            self.assertEqual(1, dir6.file_count)
            self.assertEqual(1, dir6.folder_count)
            # 校对祖先
            self.check_ancestors([dir1, dir6], file1)
            self.check_ancestors([dir1, dir6], dir7)
            self.check_ancestors([], dir1)
            self.check_ancestors([], dir2)
            self.check_ancestors([dir2], file2)
            self.check_ancestors([dir1, dir3], file3)
            self.check_ancestors([dir1], dir3)
            self.check_ancestors([dir1], dir6)
            self.check_ancestors([dir2], dir5)
            self.check_ancestors([dir2], file4)
            self.check_ancestors([dir1, dir3], dir4)
            # == 平级移动文件夹 ==
            dir6.move_to(dir2)
            """
            |            |
            - dir2       - dir1
               |             |
               - file2       - dir3
               - dir5            |
               - file4           - dir4
               - dir6            - file3
                  |
                  - file1
                  - dir7
            """
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            dir7.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对cache
            self.assertEqual(4, project.file_size)
            self.assertEqual(4, project.file_count)
            self.assertEqual(7, project.folder_count)
            self.assertEqual(1, dir1.file_size)
            self.assertEqual(1, dir1.file_count)
            self.assertEqual(2, dir1.folder_count)
            self.assertEqual(3, dir2.file_size)
            self.assertEqual(3, dir2.file_count)
            self.assertEqual(3, dir2.folder_count)
            self.assertEqual(1, dir3.file_size)
            self.assertEqual(1, dir3.file_count)
            self.assertEqual(1, dir3.folder_count)
            self.assertEqual(0, dir4.file_size)
            self.assertEqual(0, dir4.file_count)
            self.assertEqual(0, dir4.folder_count)
            self.assertEqual(0, dir5.file_size)
            self.assertEqual(0, dir5.file_count)
            self.assertEqual(0, dir5.folder_count)
            self.assertEqual(1, dir6.file_size)
            self.assertEqual(1, dir6.file_count)
            self.assertEqual(1, dir6.folder_count)
            # 校对祖先
            self.check_ancestors([dir2, dir6], file1)
            self.check_ancestors([dir2, dir6], dir7)
            self.check_ancestors([], dir1)
            self.check_ancestors([], dir2)
            self.check_ancestors([dir2], file2)
            self.check_ancestors([dir1, dir3], file3)
            self.check_ancestors([dir1], dir3)
            self.check_ancestors([dir2], dir6)
            self.check_ancestors([dir2], dir5)
            self.check_ancestors([dir2], file4)
            self.check_ancestors([dir1, dir3], dir4)

    def test_revision_file_size_change(self):
        """测试创建新修订版时，文件大小缓存的变化是否正确"""
        # 测试用项目、团队
        team = Team.create("t1")
        project = Project.create(
            name="p1",
            team=team,
            source_language=Language.by_code("ja"),
            target_languages=Language.by_code("zh-CN"),
        )
        with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
            """
             |
             - file1 (revision1)
            """
            # 上传文件
            file1 = project.upload("1.txt", file)
            project.reload()
            # 校对cache
            self.assertEqual(1, project.file_size)
            self.assertEqual(1, file1.file_size)
            self.assertEqual(1, project.file_count)
            self.assertEqual(0, project.folder_count)
        with open(os.path.join(TEST_FILE_PATH, "3kbA.txt"), "rb") as file:
            """
             |
             - file1 (revision2)
            """
            # 上传文件
            file2 = project.upload("1.txt", file)
            project.reload()
            # 校对cache
            self.assertEqual(3, project.file_size)
            self.assertEqual(1, file1.file_size)
            self.assertEqual(3, file2.file_size)
            self.assertEqual(1, project.file_count)
            self.assertEqual(0, project.folder_count)

    def test_rename(self):
        """测试重命名"""
        with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
            # =======创建测试用文件夹=======
            team = Team.create("t1")
            project = Project.create("p1", team=team)
            # 上传文件
            file1 = project.upload("file1.txt", file)
            project.reload()
            # 创建两个文件夹
            dir1 = project.create_folder("dir1")
            dir2 = project.create_folder("dir2", parent=dir1)
            # 向dir2上传文件
            file2 = project.upload("file2.txt", file, parent=dir2)
            # 向dir1上传文件
            file3 = project.upload("file3.txt", file, parent=dir1)
            dir3 = project.create_folder("dir3", parent=dir1)
            # 为dir3再创建个文件夹,上传文件
            # 为dir2创建个文件夹
            # 为None创建个文件夹
            dir4 = project.create_folder("dir4", parent=dir3)
            file4 = project.upload("file4.txt", file, parent=dir3)
            dir5 = project.create_folder("dir5", parent=dir2)
            dir6 = project.create_folder("dir6")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对cache
            self.assertEqual(4, project.file_size)
            self.assertEqual(4, project.file_count)
            self.assertEqual(6, project.folder_count)
            self.assertEqual(3, dir1.file_size)
            self.assertEqual(3, dir1.file_count)
            self.assertEqual(4, dir1.folder_count)
            self.assertEqual(1, dir2.file_size)
            self.assertEqual(1, dir2.file_count)
            self.assertEqual(1, dir2.folder_count)
            self.assertEqual(1, dir3.file_size)
            self.assertEqual(1, dir3.file_count)
            self.assertEqual(1, dir3.folder_count)
            self.assertEqual(0, dir4.file_size)
            self.assertEqual(0, dir4.file_count)
            self.assertEqual(0, dir4.folder_count)
            self.assertEqual(0, dir5.file_size)
            self.assertEqual(0, dir5.file_count)
            self.assertEqual(0, dir5.folder_count)
            self.assertEqual(0, dir6.file_size)
            self.assertEqual(0, dir6.file_count)
            self.assertEqual(0, dir6.folder_count)
            # 校对祖先
            self.check_ancestors([], file1)
            self.check_ancestors([], dir1)
            self.check_ancestors([dir1], dir2)
            self.check_ancestors([dir1, dir2], file2)
            self.check_ancestors([dir1], file3)
            self.check_ancestors([dir1], dir3)
            self.check_ancestors([], dir6)
            self.check_ancestors([dir1, dir2], dir5)
            self.check_ancestors([dir1, dir3], file4)
            self.check_ancestors([dir1, dir3], dir4)
            # 校对sort_name
            self.check_sort_name("", "file000001", file1)
            self.check_sort_name("", "dir000001", dir1)
            self.check_sort_name("dir000001/", "dir000002", dir2)
            self.check_sort_name("dir000001/dir000002/", "file000002", file2)
            self.check_sort_name("dir000001/", "file000003", file3)
            self.check_sort_name("dir000001/", "dir000003", dir3)
            self.check_sort_name("", "dir000006", dir6)
            self.check_sort_name("dir000001/dir000002/", "dir000005", dir5)
            self.check_sort_name("dir000001/dir000003/", "file000004", file4)
            self.check_sort_name("dir000001/dir000003/", "dir000004", dir4)
            # 校对name
            self.assertEqual("file1.txt", file1.name)
            self.assertEqual("dir1", dir1.name)
            self.assertEqual("dir2", dir2.name)
            self.assertEqual("file2.txt", file2.name)
            self.assertEqual("file3.txt", file3.name)
            self.assertEqual("dir3", dir3.name)
            self.assertEqual("dir6", dir6.name)
            self.assertEqual("dir5", dir5.name)
            self.assertEqual("file4.txt", file4.name)
            self.assertEqual("dir4", dir4.name)
            # =======开始测试=======
            """
            初始文件结构
             |         |
             - file1   - dir1
             - dir6       |
                          - file3
                          - dir3
                              |
                              - file4
                              - dir4
                          - dir2
                              |
                              - file2
                              - dir5
            """
            # 改名
            file1.rename("nfile1.txt")
            dir6.rename("ndir6")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对sort_name
            self.check_sort_name("", "nfile000001", file1)
            self.check_sort_name("", "dir000001", dir1)
            self.check_sort_name("dir000001/", "dir000002", dir2)
            self.check_sort_name("dir000001/dir000002/", "file000002", file2)
            self.check_sort_name("dir000001/", "file000003", file3)
            self.check_sort_name("dir000001/", "dir000003", dir3)
            self.check_sort_name("", "ndir000006", dir6)
            self.check_sort_name("dir000001/dir000002/", "dir000005", dir5)
            self.check_sort_name("dir000001/dir000003/", "file000004", file4)
            self.check_sort_name("dir000001/dir000003/", "dir000004", dir4)
            # 校对name
            self.assertEqual("nfile1.txt", file1.name)
            self.assertEqual("dir1", dir1.name)
            self.assertEqual("dir2", dir2.name)
            self.assertEqual("file2.txt", file2.name)
            self.assertEqual("file3.txt", file3.name)
            self.assertEqual("dir3", dir3.name)
            self.assertEqual("ndir6", dir6.name)
            self.assertEqual("dir5", dir5.name)
            self.assertEqual("file4.txt", file4.name)
            self.assertEqual("dir4", dir4.name)

            # 改名
            file3.rename("nfile3.txt")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对sort_name
            self.check_sort_name("", "nfile000001", file1)
            self.check_sort_name("", "dir000001", dir1)
            self.check_sort_name("dir000001/", "dir000002", dir2)
            self.check_sort_name("dir000001/dir000002/", "file000002", file2)
            self.check_sort_name("dir000001/", "nfile000003", file3)
            self.check_sort_name("dir000001/", "dir000003", dir3)
            self.check_sort_name("", "ndir000006", dir6)
            self.check_sort_name("dir000001/dir000002/", "dir000005", dir5)
            self.check_sort_name("dir000001/dir000003/", "file000004", file4)
            self.check_sort_name("dir000001/dir000003/", "dir000004", dir4)
            # 校对name
            self.assertEqual("nfile1.txt", file1.name)
            self.assertEqual("dir1", dir1.name)
            self.assertEqual("dir2", dir2.name)
            self.assertEqual("file2.txt", file2.name)
            self.assertEqual("nfile3.txt", file3.name)
            self.assertEqual("dir3", dir3.name)
            self.assertEqual("ndir6", dir6.name)
            self.assertEqual("dir5", dir5.name)
            self.assertEqual("file4.txt", file4.name)
            self.assertEqual("dir4", dir4.name)

            # 改名，不同文件夹file可以重名
            file4.rename("file2.txt")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对sort_name
            self.check_sort_name("", "nfile000001", file1)
            self.check_sort_name("", "dir000001", dir1)
            self.check_sort_name("dir000001/", "dir000002", dir2)
            self.check_sort_name("dir000001/dir000002/", "file000002", file2)
            self.check_sort_name("dir000001/", "nfile000003", file3)
            self.check_sort_name("dir000001/", "dir000003", dir3)
            self.check_sort_name("", "ndir000006", dir6)
            self.check_sort_name("dir000001/dir000002/", "dir000005", dir5)
            self.check_sort_name("dir000001/dir000003/", "file000002", file4)
            self.check_sort_name("dir000001/dir000003/", "dir000004", dir4)
            # 校对name
            self.assertEqual("nfile1.txt", file1.name)
            self.assertEqual("dir1", dir1.name)
            self.assertEqual("dir2", dir2.name)
            self.assertEqual("file2.txt", file2.name)
            self.assertEqual("nfile3.txt", file3.name)
            self.assertEqual("dir3", dir3.name)
            self.assertEqual("ndir6", dir6.name)
            self.assertEqual("dir5", dir5.name)
            self.assertEqual("file2.txt", file4.name)
            self.assertEqual("dir4", dir4.name)

            # 改名，不同文件夹dir可以重名
            dir5.rename("dir4")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对sort_name
            self.check_sort_name("", "nfile000001", file1)
            self.check_sort_name("", "dir000001", dir1)
            self.check_sort_name("dir000001/", "dir000002", dir2)
            self.check_sort_name("dir000001/dir000002/", "file000002", file2)
            self.check_sort_name("dir000001/", "nfile000003", file3)
            self.check_sort_name("dir000001/", "dir000003", dir3)
            self.check_sort_name("", "ndir000006", dir6)
            self.check_sort_name("dir000001/dir000002/", "dir000004", dir5)
            self.check_sort_name("dir000001/dir000003/", "file000002", file4)
            self.check_sort_name("dir000001/dir000003/", "dir000004", dir4)
            # 校对name
            self.assertEqual("nfile1.txt", file1.name)
            self.assertEqual("dir1", dir1.name)
            self.assertEqual("dir2", dir2.name)
            self.assertEqual("file2.txt", file2.name)
            self.assertEqual("nfile3.txt", file3.name)
            self.assertEqual("dir3", dir3.name)
            self.assertEqual("ndir6", dir6.name)
            self.assertEqual("dir4", dir5.name)
            self.assertEqual("file2.txt", file4.name)
            self.assertEqual("dir4", dir4.name)

            # 改名
            dir3.rename("ndir3")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对sort_name
            self.check_sort_name("", "nfile000001", file1)
            self.check_sort_name("", "dir000001", dir1)
            self.check_sort_name("dir000001/", "dir000002", dir2)
            self.check_sort_name("dir000001/dir000002/", "file000002", file2)
            self.check_sort_name("dir000001/", "nfile000003", file3)
            self.check_sort_name("dir000001/", "ndir000003", dir3)
            self.check_sort_name("", "ndir000006", dir6)
            self.check_sort_name("dir000001/dir000002/", "dir000004", dir5)
            self.check_sort_name("dir000001/ndir000003/", "file000002", file4)
            self.check_sort_name("dir000001/ndir000003/", "dir000004", dir4)
            # 校对name
            self.assertEqual("nfile1.txt", file1.name)
            self.assertEqual("dir1", dir1.name)
            self.assertEqual("dir2", dir2.name)
            self.assertEqual("file2.txt", file2.name)
            self.assertEqual("nfile3.txt", file3.name)
            self.assertEqual("ndir3", dir3.name)
            self.assertEqual("ndir6", dir6.name)
            self.assertEqual("dir4", dir5.name)
            self.assertEqual("file2.txt", file4.name)
            self.assertEqual("dir4", dir4.name)

            # 改名
            dir1.rename("ndir1")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对sort_name
            self.check_sort_name("", "nfile000001", file1)
            self.check_sort_name("", "ndir000001", dir1)
            self.check_sort_name("ndir000001/", "dir000002", dir2)
            self.check_sort_name("ndir000001/dir000002/", "file000002", file2)
            self.check_sort_name("ndir000001/", "nfile000003", file3)
            self.check_sort_name("ndir000001/", "ndir000003", dir3)
            self.check_sort_name("", "ndir000006", dir6)
            self.check_sort_name("ndir000001/dir000002/", "dir000004", dir5)
            self.check_sort_name("ndir000001/ndir000003/", "file000002", file4)
            self.check_sort_name("ndir000001/ndir000003/", "dir000004", dir4)
            # 校对name
            self.assertEqual("nfile1.txt", file1.name)
            self.assertEqual("ndir1", dir1.name)
            self.assertEqual("dir2", dir2.name)
            self.assertEqual("file2.txt", file2.name)
            self.assertEqual("nfile3.txt", file3.name)
            self.assertEqual("ndir3", dir3.name)
            self.assertEqual("ndir6", dir6.name)
            self.assertEqual("dir4", dir5.name)
            self.assertEqual("file2.txt", file4.name)
            self.assertEqual("dir4", dir4.name)

            # 同名没有问题
            file2.rename("file2.txt")
            dir4.rename("dir4")
            dir3.rename("ndir3")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对sort_name
            self.check_sort_name("", "nfile000001", file1)
            self.check_sort_name("", "ndir000001", dir1)
            self.check_sort_name("ndir000001/", "dir000002", dir2)
            self.check_sort_name("ndir000001/dir000002/", "file000002", file2)
            self.check_sort_name("ndir000001/", "nfile000003", file3)
            self.check_sort_name("ndir000001/", "ndir000003", dir3)
            self.check_sort_name("", "ndir000006", dir6)
            self.check_sort_name("ndir000001/dir000002/", "dir000004", dir5)
            self.check_sort_name("ndir000001/ndir000003/", "file000002", file4)
            self.check_sort_name("ndir000001/ndir000003/", "dir000004", dir4)
            # 校对name
            self.assertEqual("nfile1.txt", file1.name)
            self.assertEqual("ndir1", dir1.name)
            self.assertEqual("dir2", dir2.name)
            self.assertEqual("file2.txt", file2.name)
            self.assertEqual("nfile3.txt", file3.name)
            self.assertEqual("ndir3", dir3.name)
            self.assertEqual("ndir6", dir6.name)
            self.assertEqual("dir4", dir5.name)
            self.assertEqual("file2.txt", file4.name)
            self.assertEqual("dir4", dir4.name)

            # 可以修改文件名大小写
            file2.rename("File2.txT")
            dir4.rename("Dir4")
            dir3.rename("Dir3")
            # 刷新
            project.reload()
            dir1.reload()
            dir2.reload()
            dir3.reload()
            dir4.reload()
            dir5.reload()
            dir6.reload()
            file1.reload()
            file2.reload()
            file3.reload()
            file4.reload()
            # 校对sort_name
            self.check_sort_name("", "nfile000001", file1)
            self.check_sort_name("", "ndir000001", dir1)
            self.check_sort_name("ndir000001/", "dir000002", dir2)
            self.check_sort_name("ndir000001/dir000002/", "File000002", file2)
            self.check_sort_name("ndir000001/", "nfile000003", file3)
            self.check_sort_name("ndir000001/", "Dir000003", dir3)
            self.check_sort_name("", "ndir000006", dir6)
            self.check_sort_name("ndir000001/dir000002/", "dir000004", dir5)
            self.check_sort_name("ndir000001/Dir000003/", "file000002", file4)
            self.check_sort_name("ndir000001/Dir000003/", "Dir000004", dir4)
            # 校对name
            self.assertEqual("nfile1.txt", file1.name)
            self.assertEqual("ndir1", dir1.name)
            self.assertEqual("dir2", dir2.name)
            self.assertEqual("File2.txT", file2.name)
            self.assertEqual("nfile3.txt", file3.name)
            self.assertEqual("Dir3", dir3.name)
            self.assertEqual("ndir6", dir6.name)
            self.assertEqual("dir4", dir5.name)
            self.assertEqual("file2.txt", file4.name)
            self.assertEqual("Dir4", dir4.name)

            # 允许把jpg修改成jpeg这样
            img1 = project.upload("img.jpg", file)
            self.assertEqual("img.jpg", img1.name)

            img1.rename("img.jPG")
            img1.reload()
            self.assertEqual("img.jPG", img1.name)

            img1.rename("imG.jPG")
            img1.reload()
            self.assertEqual("imG.jPG", img1.name)

            img1.rename("Img.jpeg")
            img1.reload()
            self.assertEqual("Img.jpeg", img1.name)
            # 但是不允许修改成txt
            with self.assertRaises(SuffixNotInFileTypeError):
                img1.rename("img.txt")

    def test_rename_error(self):
        """测试重命名"""
        with self.app.test_request_context():
            with open(os.path.join(TEST_FILE_PATH, "1kbA.txt"), "rb") as file:
                # =======创建测试用文件夹=======
                team = Team.create("t1")
                project = Project.create("p1", team=team)
                # 上传文件
                file1 = project.upload("file1.txt", file)
                project.reload()
                # 创建两个文件夹
                dir1 = project.create_folder("dir1")
                dir2 = project.create_folder("dir2", parent=dir1)
                # 向dir2上传文件
                file2 = project.upload("file2.txt", file, parent=dir2)
                # 向dir1上传文件
                file3 = project.upload("file3.txt", file, parent=dir1)
                dir3 = project.create_folder("dir3", parent=dir1)
                # 为dir3再创建个文件夹,上传文件
                # 为dir2创建个文件夹
                # 为None创建个文件夹
                dir4 = project.create_folder("dir4", parent=dir3)
                file4 = project.upload("file4.txt", file, parent=dir3)
                dir5 = project.create_folder("dir5", parent=dir2)
                dir6 = project.create_folder("dir6")
                # 刷新
                project.reload()
                dir1.reload()
                dir2.reload()
                dir3.reload()
                dir4.reload()
                dir5.reload()
                dir6.reload()
                file1.reload()
                file2.reload()
                file3.reload()
                file4.reload()
                # 校对cache
                self.assertEqual(4, project.file_size)
                self.assertEqual(4, project.file_count)
                self.assertEqual(6, project.folder_count)
                self.assertEqual(3, dir1.file_size)
                self.assertEqual(3, dir1.file_count)
                self.assertEqual(4, dir1.folder_count)
                self.assertEqual(1, dir2.file_size)
                self.assertEqual(1, dir2.file_count)
                self.assertEqual(1, dir2.folder_count)
                self.assertEqual(1, dir3.file_size)
                self.assertEqual(1, dir3.file_count)
                self.assertEqual(1, dir3.folder_count)
                self.assertEqual(0, dir4.file_size)
                self.assertEqual(0, dir4.file_count)
                self.assertEqual(0, dir4.folder_count)
                self.assertEqual(0, dir5.file_size)
                self.assertEqual(0, dir5.file_count)
                self.assertEqual(0, dir5.folder_count)
                self.assertEqual(0, dir6.file_size)
                self.assertEqual(0, dir6.file_count)
                self.assertEqual(0, dir6.folder_count)
                # 校对祖先
                self.check_ancestors([], file1)
                self.check_ancestors([], dir1)
                self.check_ancestors([dir1], dir2)
                self.check_ancestors([dir1, dir2], file2)
                self.check_ancestors([dir1], file3)
                self.check_ancestors([dir1], dir3)
                self.check_ancestors([], dir6)
                self.check_ancestors([dir1, dir2], dir5)
                self.check_ancestors([dir1, dir3], file4)
                self.check_ancestors([dir1, dir3], dir4)
                # 校对sort_name
                self.check_sort_name("", "file000001", file1)
                self.check_sort_name("", "dir000001", dir1)
                self.check_sort_name("dir000001/", "dir000002", dir2)
                self.check_sort_name("dir000001/dir000002/", "file000002", file2)
                self.check_sort_name("dir000001/", "file000003", file3)
                self.check_sort_name("dir000001/", "dir000003", dir3)
                self.check_sort_name("", "dir000006", dir6)
                self.check_sort_name("dir000001/dir000002/", "dir000005", dir5)
                self.check_sort_name("dir000001/dir000003/", "file000004", file4)
                self.check_sort_name("dir000001/dir000003/", "dir000004", dir4)
                # =======开始测试=======
                """
                初始文件结构
                 |         |
                 - file1   - dir1
                 - dir6       |
                              - file3
                              - dir3
                                  |
                                  - file4
                                  - dir4
                              - dir2
                                  |
                                  - file2
                                  - dir5
                """

                # dir 非法的名称
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename("")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename("/.txt")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename("\.txt")  # noqa: W605
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename("?.txt")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename("<.txt")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(">.txt")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(":.txt")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename("*.txt")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(".txt")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(" .txt")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(".")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename("..")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(" . ")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(" .. ")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(" . . ")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(" ..")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(".. ")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(" . .")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename(". . ")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename("hi.")
                with self.assertRaises(FilenameIllegalError):
                    dir6.rename("hi. ")

                # file 非法的名称
                with self.assertRaises(FilenameIllegalError):
                    file1.rename("")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename("/.txt")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename("\.txt")  # noqa: W605
                with self.assertRaises(FilenameIllegalError):
                    file1.rename("?.txt")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename("<.txt")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(">.txt")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(":.txt")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename("*.txt")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(".txt")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(" .txt")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(".")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename("..")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(" . ")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(" .. ")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(" . . ")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(" ..")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(".. ")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(" . .")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename(". . ")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename("hi.")
                with self.assertRaises(FilenameIllegalError):
                    file1.rename("hi. ")

                # file 后缀FileType不支持
                with self.assertRaises(SuffixNotInFileTypeError):
                    file1.rename("hi.cad")

                # file 后缀FileType必须相同
                with self.assertRaises(SuffixNotInFileTypeError):
                    file1.rename("hi.jpg")

                # 同文件夹dir不能和file重名
                with self.assertRaises(FilenameDuplicateError):
                    dir4.rename("file4.txt")
                with self.assertRaises(FilenameDuplicateError):
                    dir4.rename("file4.txT")
                with self.assertRaises(FilenameDuplicateError):
                    dir4.rename("File4.txt")
                with self.assertRaises(FilenameDuplicateError):
                    dir4.rename("File4.txT")

                # 同文件夹file不能和dir重名
                dir4.rename("dir4.txt")
                with self.assertRaises(FilenameDuplicateError):
                    file4.rename("dir4.txt")
                with self.assertRaises(FilenameDuplicateError):
                    file4.rename("dir4.txT")
                with self.assertRaises(FilenameDuplicateError):
                    file4.rename("Dir4.txt")
                with self.assertRaises(FilenameDuplicateError):
                    file4.rename("Dir4.txT")

    def test_next_source_rank(self):
        """next_source_rank 返回至比最大的 rank 大 1"""
        team = Team.create("t1")
        project = Project.create(
            name="p1",
            team=team,
            source_language=Language.by_code("ja"),
            target_languages=Language.by_code("zh-CN"),
        )
        file = project.create_file("f1.png")
        file2 = project.create_file("f2.png")
        file.create_source("1", x=0, y=0, rank=1)
        file.create_source("2", x=0, y=0, rank=8)  # file 中 rank 最大的 source
        file2.create_source("3", x=0, y=0, rank=3)
        self.assertEqual(9, file.next_source_rank())
