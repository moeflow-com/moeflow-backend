import os

from mongoengine import DoesNotExist

from app.models.file import File, FileTargetCache, Source, Tip, Translation
from app.models.language import Language
from app.models.project import Project, ProjectRole
from app.models.target import Target
from app.models.team import Team
from app.models.user import User
from app.constants.file import FileType
from tests import TEST_FILE_PATH, MoeAPITestCase
from app.exceptions.language import SameTargetLanguageError


class MultiTargetCacheTestCase(MoeAPITestCase):
    """测试多目标语言的Cache变化"""

    def test_project_default_create_target(self):
        """测试创建向时自动创建了target"""
        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        team = Team.create("t1", creator=user)
        project = Project.create("p1", team=team, creator=user)
        file1 = project.create_file("1.jpg")
        # == 开始测试 ==
        # Target
        self.assertEqual(1, project.targets().count())
        target = project.targets().first()
        self.assertEqual(Language.by_code("zh-CN"), target.language)
        self.assertEqual(0, target.translated_source_count)
        self.assertEqual(0, target.checked_source_count)
        # FileTargetCache
        self.assertEqual(1, FileTargetCache.objects().count())
        file_target_cache = FileTargetCache.objects().first()
        self.assertEqual(0, file_target_cache.translated_source_count)
        self.assertEqual(0, file_target_cache.checked_source_count)

    def test_create_target(self):
        """测试创建向时自动创建了target"""
        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        team = Team.create("t1", creator=user)
        project = Project.create(
            "p1",
            team=team,
            creator=user,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        # == 开始测试 ==
        self.assertEqual(2, Target.objects().count())
        self.assertEqual(0, FileTargetCache.objects().count())
        file1 = project.create_file("1.txt")
        file1 = project.create_file("1.jpg")
        self.assertEqual(2, Target.objects().count())
        self.assertEqual(2 * 2, FileTargetCache.objects().count())
        # 创建一个已有语言的Target，报错，数量不会增加
        with self.assertRaises(SameTargetLanguageError):
            Target.create(project=project, language=Language.by_code("ja"))
        self.assertEqual(2, Target.objects().count())
        self.assertEqual(2 * 2, FileTargetCache.objects().count())
        # 创建一个新语言的Target，数量增加
        Target.create(project=project, language=Language.by_code("ko"))
        self.assertEqual(3, Target.objects().count())
        self.assertEqual(3 * 2, FileTargetCache.objects().count())
        # 创建已有文件，FileTargetCache不增加
        file1 = project.create_file("1.jpg")
        self.assertEqual(3, Target.objects().count())
        self.assertEqual(3 * 2, FileTargetCache.objects().count())
        # 创建同名txt文件，因为会建立新修订版，增加
        file1 = project.create_file("1.txt")
        self.assertEqual(3, Target.objects().count())
        self.assertEqual(3 * 3, FileTargetCache.objects().count())
        # 创建新文件，增加
        file1 = project.create_file("2.txt")
        self.assertEqual(3, Target.objects().count())
        self.assertEqual(3 * 4, FileTargetCache.objects().count())

    def test_target_count(self):
        """测试target的计数"""
        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        team = Team.create("t1", creator=user)
        project1 = Project.create("p1", team=team, creator=user)
        project2 = Project.create(
            "p2",
            team=team,
            creator=user,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        # == 开始测试 ==
        self.assertEqual(1, project1.target_count)
        self.assertEqual(2, project2.target_count)
        # 给project创建一个同名target，报错，计数不增加
        with self.assertRaises(SameTargetLanguageError):
            Target.create(project=project2, language=Language.by_code("ja"))
        project2.reload()
        self.assertEqual(2, project2.target_count)
        # 给project创建一个新target，增加
        target = Target.create(project=project2, language=Language.by_code("ko"))
        project2.reload()
        self.assertEqual(3, project2.target_count)
        # 给project上传一个file，不增加
        project2.create_file("1.txt")
        project2.reload()
        self.assertEqual(3, project2.target_count)
        # 删除target，数量减少
        target.clear()
        project2.reload()
        self.assertEqual(2, project2.target_count)

    def test_cache_create_delete_normal_step(self):
        """测试一步一步增加/选定/取消选定/删除翻译对计数的影响"""

        def check_cache(
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            file1.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t),
                file1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c), file1.checked_source_count
            )
            file1_target1.reload()
            self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
            self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
            file1_target2.reload()
            self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
            self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            file2.reload()
            self.assertEqual(
                (file2_target1_t + file2_target2_t),
                file2.translated_source_count,
            )
            self.assertEqual(
                (file2_target1_c + file2_target2_c), file2.checked_source_count
            )
            file2_target1.reload()
            self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
            self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
            file2_target2.reload()
            self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
            self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            dir1.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                dir1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                dir1.checked_source_count,
            )
            dir1_target1.reload()
            self.assertEqual(
                file1_target1_t + file2_target1_t,
                dir1_target1.translated_source_count,
            )
            self.assertEqual(
                file1_target1_c + file2_target1_c,
                dir1_target1.checked_source_count,
            )
            dir1_target2.reload()
            self.assertEqual(
                file1_target2_t + file2_target2_t,
                dir1_target2.translated_source_count,
            )
            self.assertEqual(
                file1_target2_c + file2_target2_c,
                dir1_target2.checked_source_count,
            )
            # dir2 和他两个Cache
            dir2.reload()
            self.assertEqual(
                file2_target1_t + file2_target2_t, dir2.translated_source_count
            )
            self.assertEqual(
                file2_target1_c + file2_target2_c, dir2.checked_source_count
            )
            dir2_target1.reload()
            self.assertEqual(file2_target1_t, dir2_target1.translated_source_count)
            self.assertEqual(file2_target1_c, dir2_target1.checked_source_count)
            dir2_target2.reload()
            self.assertEqual(file2_target2_t, dir2_target2.translated_source_count)
            self.assertEqual(file2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir1", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # == 初始状态 ==
        # 验证数量
        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # ==== 测试增加翻译、选定翻译对Cache影响 ====
        # === 第一轮 file1 target1 ===

        # == user1给file1_source1增加翻译 ==
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        # 验证数量
        self.assertEqual(1, file1_source1.translations().count())
        check_cache(
            file1_target1_t=1,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file1_source1修改翻译，不改变Cache ==
        file1_source1.create_translation(
            "file1_source1_target1_tra1/2", target=target1, user=user1
        )
        # 验证数量
        self.assertEqual(1, file1_source1.translations().count())
        check_cache(
            file1_target1_t=1,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user2给file1_source1增加翻译，不改变Cache ==
        file1_source1_target1_tra2 = file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        # 验证数量
        self.assertEqual(2, file1_source1.translations().count())
        check_cache(
            file1_target1_t=1,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file1_source1确认翻译 ==
        file1_source1_target1_tra1.select(user=user1)
        # 验证数量
        file1_source1_target1_tra1.reload()
        file1_source1_target1_tra2.reload()
        self.assertEqual(True, file1_source1_target1_tra1.selected)
        self.assertEqual(False, file1_source1_target1_tra2.selected)
        self.assertEqual(2, file1_source1.translations().count())
        check_cache(
            file1_target1_t=1,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=1,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file1_source1修改确认翻译，不改变Cache ==
        file1_source1_target1_tra2.select(user=user1)
        # 验证数量
        file1_source1_target1_tra1.reload()
        file1_source1_target1_tra2.reload()
        self.assertEqual(False, file1_source1_target1_tra1.selected)
        self.assertEqual(True, file1_source1_target1_tra2.selected)
        self.assertEqual(2, file1_source1.translations().count())
        check_cache(
            file1_target1_t=1,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=1,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # === 第二轮 file1 target1 ===

        # == user1给file1_source2增加翻译 ==
        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        # 验证数量
        self.assertEqual(1, file1_source2.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=1,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file1_source2修改翻译，不改变Cache ==
        file1_source2.create_translation(
            "file1_source2_target1_tra1/2", target=target1, user=user1
        )
        # 验证数量
        self.assertEqual(1, file1_source2.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=1,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user2给file1_source2增加翻译，不改变Cache ==
        file1_source2_target1_tra2 = file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        # 验证数量
        self.assertEqual(2, file1_source2.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=1,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file1_source2确认翻译 ==
        file1_source2_target1_tra1.select(user=user1)
        # 验证数量
        file1_source2_target1_tra1.reload()
        file1_source2_target1_tra2.reload()
        self.assertEqual(True, file1_source2_target1_tra1.selected)
        self.assertEqual(False, file1_source2_target1_tra2.selected)
        self.assertEqual(2, file1_source2.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file1_source1修改确认翻译，不改变Cache ==
        file1_source2_target1_tra2.select(user=user1)
        # 验证数量
        file1_source2_target1_tra1.reload()
        file1_source2_target1_tra2.reload()
        self.assertEqual(False, file1_source2_target1_tra1.selected)
        self.assertEqual(True, file1_source2_target1_tra2.selected)
        self.assertEqual(2, file1_source2.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # === 第三轮 file1 target2 ===

        # == user1给file1_source1增加翻译 ==
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        # 验证数量
        self.assertEqual(3, file1_source1.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file1_source1修改翻译，不改变Cache ==
        file1_source1.create_translation(
            "file1_source1_target2_tra1/2", target=target2, user=user1
        )
        # 验证数量
        self.assertEqual(3, file1_source1.translations().count())
        file1_source1_target2_tra1.reload()
        self.assertEqual(
            "file1_source1_target2_tra1/2", file1_source1_target2_tra1.content
        )
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user2给file1_source1增加翻译，不改变Cache ==
        file1_source1_target2_tra2 = file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        # 验证数量
        self.assertEqual(4, file1_source1.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file1_source1确认翻译 ==
        file1_source1_target2_tra1.select(user=user1)
        # 验证数量
        file1_source1_target2_tra1.reload()
        file1_source1_target2_tra2.reload()
        self.assertEqual(True, file1_source1_target2_tra1.selected)
        self.assertEqual(False, file1_source1_target2_tra2.selected)
        self.assertEqual(4, file1_source1.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=1,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file1_source1修改确认翻译，不改变Cache ==
        file1_source1_target2_tra2.select(user=user1)
        # 验证数量
        file1_source1_target2_tra1.reload()
        file1_source1_target2_tra2.reload()
        self.assertEqual(False, file1_source1_target2_tra1.selected)
        self.assertEqual(True, file1_source1_target2_tra2.selected)
        self.assertEqual(4, file1_source1.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=1,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # === 第四轮 file2 target1 ===

        # == user1给file2_source1增加翻译 ==
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        # 验证数量
        self.assertEqual(1, file2_source1.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=1,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file2_source1修改翻译，不改变Cache ==
        file2_source1.create_translation(
            "file2_source1_target1_tra1/2", target=target1, user=user1
        )
        # 验证数量
        file2_source1_target1_tra1.reload()
        self.assertEqual(
            "file2_source1_target1_tra1/2", file2_source1_target1_tra1.content
        )
        self.assertEqual(1, file2_source1.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=1,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user2给file2_source1增加翻译，不改变Cache ==
        file2_source1_target1_tra2 = file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        # 验证数量
        self.assertEqual(2, file2_source1.translations().count())
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=1,
            file2_target1_c=0,
            file2_target2_c=0,
        )

        # == user1给file2_source1选定翻译 ==
        file2_source1_target1_tra1.select(user=user1)
        # 验证数量
        self.assertEqual(2, file2_source1.translations().count())
        file2_source1_target1_tra1.reload()
        file2_source1_target1_tra2.reload()
        self.assertEqual(True, file2_source1_target1_tra1.selected)
        self.assertEqual(False, file2_source1_target1_tra2.selected)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=1,
            file2_target1_c=1,
            file2_target2_c=0,
        )

        # == user1给file2_source1切换翻译，不改变Cache ==
        file2_source1_target1_tra2.select(user=user1)
        # 验证数量
        self.assertEqual(2, file2_source1.translations().count())
        file2_source1_target1_tra1.reload()
        file2_source1_target1_tra2.reload()
        self.assertEqual(False, file2_source1_target1_tra1.selected)
        self.assertEqual(True, file2_source1_target1_tra2.selected)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=1,
            file2_target1_c=1,
            file2_target2_c=0,
        )

        # ==== 测试取消选定、删除翻译对Cache影响 ====
        # == 取消选定 file1_source1_target2_tra2 ==
        file1_source1_target2_tra2.unselect()
        file1_source1_target2_tra1.reload()
        file1_source1_target2_tra2.reload()
        self.assertEqual(False, file1_source1_target2_tra1.selected)
        self.assertEqual(False, file1_source1_target2_tra2.selected)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=0,  # 选中的减少
            file2_target1_c=1,
            file2_target2_c=0,
        )

        # == 删除翻译 source1 的 tra2 ==
        file1_source1_target1_tra2.clear()  # 这个原来是选中的
        check_cache(
            file1_target1_t=2,
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=1,  # 减少一个
            file1_target2_c=0,
            file2_target1_c=1,
            file2_target2_c=0,
        )

        # == 删除翻译 source1 的tra1 ==
        file1_source1_target1_tra1.clear()  # 删了这source1就没有翻译了
        check_cache(
            file1_target1_t=1,  # 减少一个
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=1,
            file1_target2_c=0,
            file2_target1_c=1,
            file2_target2_c=0,
        )

        # == 删除 source2 ，即删除了 ==
        # == file1_source2_target1_tra1 和 file1_source2_target1_tra2 ==
        self.assertEqual(2, file1_source2.translations().count())
        file1_source2.clear()  # 这时候file1_target1就没有翻译和选定了
        with self.assertRaises(DoesNotExist):
            file1_source2_target1_tra1.reload()
        with self.assertRaises(DoesNotExist):
            file1_source2_target1_tra2.reload()
        check_cache(
            file1_target1_t=0,  # 减少一个
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=0,  # 减少一个
            file1_target2_c=0,
            file2_target1_c=1,
            file2_target2_c=0,
        )

        # == 将 file2_source1_target1_tra1 unselect ==
        # == 原来就没有 select ，不生效，file2_source1_target1_tra2才是被选中的翻译 ==
        file2_source1_target1_tra1.unselect()
        check_cache(
            file1_target1_t=0,  # 减少一个
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=0,  # 减少一个
            file1_target2_c=0,
            file2_target1_c=1,
            file2_target2_c=0,
        )

        # == 将 file2_source1_target1_tra2 unselect，target1 被选中的减少
        file2_source1_target1_tra2.unselect()
        check_cache(
            file1_target1_t=0,
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,  # 减少一个
            file2_target2_c=0,
        )

        file1_source1_target2_tra1.clear()
        file1_source1_target2_tra2.clear()
        file2_source1_target1_tra1.clear()
        file2_source1_target1_tra2.clear()

        # 删光了

        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

    def test_delete_source_and_tra(self):
        """测试删除原文和翻译"""

        def check_cache(
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            file1.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t),
                file1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c), file1.checked_source_count
            )
            file1_target1.reload()
            self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
            self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
            file1_target2.reload()
            self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
            self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            file2.reload()
            self.assertEqual(
                (file2_target1_t + file2_target2_t),
                file2.translated_source_count,
            )
            self.assertEqual(
                (file2_target1_c + file2_target2_c), file2.checked_source_count
            )
            file2_target1.reload()
            self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
            self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
            file2_target2.reload()
            self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
            self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            dir1.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                dir1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                dir1.checked_source_count,
            )
            dir1_target1.reload()
            self.assertEqual(
                file1_target1_t + file2_target1_t,
                dir1_target1.translated_source_count,
            )
            self.assertEqual(
                file1_target1_c + file2_target1_c,
                dir1_target1.checked_source_count,
            )
            dir1_target2.reload()
            self.assertEqual(
                file1_target2_t + file2_target2_t,
                dir1_target2.translated_source_count,
            )
            self.assertEqual(
                file1_target2_c + file2_target2_c,
                dir1_target2.checked_source_count,
            )
            # dir2 和他两个Cache
            dir2.reload()
            self.assertEqual(
                file2_target1_t + file2_target2_t, dir2.translated_source_count
            )
            self.assertEqual(
                file2_target1_c + file2_target2_c, dir2.checked_source_count
            )
            dir2_target1.reload()
            self.assertEqual(file2_target1_t, dir2_target1.translated_source_count)
            self.assertEqual(file2_target1_c, dir2_target1.checked_source_count)
            dir2_target2.reload()
            self.assertEqual(file2_target2_t, dir2_target2.translated_source_count)
            self.assertEqual(file2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir1", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2_source2 = file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # 创建翻译
        # file1 target1
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        file1_source1_target1_tra2 = file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        file1_source1_target1_tra1.select(user=user1)

        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        file1_source2_target1_tra2 = file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        file1_source2_target1_tra1.select(user=user1)
        # file1 target2
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        file1_source1_target2_tra2 = file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        file1_source1_target2_tra1.select(user=user1)
        file1_source2_target2_tra1 = file1_source2.create_translation(
            "file1_source2_target2_tra1", target=target2, user=user1
        )
        file1_source2_target2_tra2 = file1_source2.create_translation(
            "file1_source2_target2_tra2", target=target2, user=user2
        )
        file1_source2_target2_tra1.select(user=user1)
        # file2 target1
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        file2_source1_target1_tra2 = file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        file2_source1_target1_tra1.select(user=user1)

        file2_source2_target1_tra1 = file2_source2.create_translation(
            "file2_source2_target1_tra1", target=target1, user=user1
        )
        file2_source2_target1_tra2 = file2_source2.create_translation(
            "file2_source2_target1_tra2", target=target1, user=user2
        )
        file2_source2_target1_tra1.select(user=user1)
        # file2 target2
        file2_source1_target2_tra1 = file2_source1.create_translation(
            "file2_source1_target2_tra1", target=target2, user=user1
        )
        file2_source1.create_translation(
            "file2_source1_target2_tra2", target=target2, user=user2
        )
        file2_source1_target2_tra1.select(user=user1)

        file2_source2_target2_tra1 = file2_source2.create_translation(
            "file2_source2_target2_tra1", target=target2, user=user1
        )
        file2_source2.create_translation(
            "file2_source2_target2_tra2", target=target2, user=user2
        )
        file2_source2_target2_tra1.select(user=user1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
        )
        # == 仅取消选定 ==
        file1_source1_target1_tra1.unselect()
        file1_source2_target1_tra1.unselect()

        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=0,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
        )

        # == 还有一个翻译不影响 ==
        file1_source1_target1_tra1.clear()
        file1_source2_target1_tra1.clear()

        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=0,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
        )

        # == 这次删光了 ==
        file1_source1_target1_tra2.clear()
        file1_source2_target1_tra2.clear()

        check_cache(
            file1_target1_t=0,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=0,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
        )

        # == 取消选定后删除 ==
        file1_source1_target2_tra1.unselect()
        file1_source2_target2_tra1.unselect()
        file1_source1_target2_tra1.clear()
        file1_source2_target2_tra1.clear()
        file1_source1_target2_tra2.clear()
        file1_source2_target2_tra2.clear()
        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=2,
            file2_target2_c=2,
        )

        # == 直接删除 ==
        file2_source1_target1_tra1.clear()
        file2_source2_target1_tra1.clear()
        file2_source1_target1_tra2.clear()
        file2_source2_target1_tra2.clear()
        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=2,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=2,
        )

    def test_delete_file(self):
        """测试删除文件"""

        def check_cache(
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            try:
                file1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file1_target1_t + file1_target2_t),
                    file1.translated_source_count,
                )
                self.assertEqual(
                    (file1_target1_c + file1_target2_c),
                    file1.checked_source_count,
                )
                file1_target1.reload()
                self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
                self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
                file1_target2.reload()
                self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
                self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            try:
                file2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file2_target1_t + file2_target2_t),
                    file2.translated_source_count,
                )
                self.assertEqual(
                    (file2_target1_c + file2_target2_c),
                    file2.checked_source_count,
                )
                file2_target1.reload()
                self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
                file2_target2.reload()
                self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            try:
                dir1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target2.reload()
            else:
                self.assertEqual(
                    (
                        file1_target1_t
                        + file1_target2_t
                        + file2_target1_t
                        + file2_target2_t
                    ),
                    dir1.translated_source_count,
                )
                self.assertEqual(
                    (
                        file1_target1_c
                        + file1_target2_c
                        + file2_target1_c
                        + file2_target2_c
                    ),
                    dir1.checked_source_count,
                )
                dir1_target1.reload()
                self.assertEqual(
                    file1_target1_t + file2_target1_t,
                    dir1_target1.translated_source_count,
                )
                self.assertEqual(
                    file1_target1_c + file2_target1_c,
                    dir1_target1.checked_source_count,
                )
                dir1_target2.reload()
                self.assertEqual(
                    file1_target2_t + file2_target2_t,
                    dir1_target2.translated_source_count,
                )
                self.assertEqual(
                    file1_target2_c + file2_target2_c,
                    dir1_target2.checked_source_count,
                )
            # dir2 和他两个Cache
            try:
                dir2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target2.reload()
            else:
                self.assertEqual(
                    file2_target1_t + file2_target2_t,
                    dir2.translated_source_count,
                )
                self.assertEqual(
                    file2_target1_c + file2_target2_c,
                    dir2.checked_source_count,
                )
                dir2_target1.reload()
                self.assertEqual(file2_target1_t, dir2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, dir2_target1.checked_source_count)
                dir2_target2.reload()
                self.assertEqual(file2_target2_t, dir2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir1", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2_source2 = file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # 创建翻译
        # file1 target1
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        file1_source1_target1_tra2 = file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        file1_source1_target1_tra1.select(user=user1)

        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        file1_source2_target1_tra2 = file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        file1_source2_target1_tra1.select(user=user1)
        # file1 target2
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        file1_source1_target2_tra2 = file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        file1_source1_target2_tra1.select(user=user1)
        file1_source2_target2_tra1 = file1_source2.create_translation(
            "file1_source2_target2_tra1", target=target2, user=user1
        )
        file1_source2_target2_tra2 = file1_source2.create_translation(
            "file1_source2_target2_tra2", target=target2, user=user2
        )
        file1_source2_target2_tra1.select(user=user1)
        # file2 target1
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        file2_source1_target1_tra2 = file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        file2_source1_target1_tra1.select(user=user1)

        file2_source2_target1_tra1 = file2_source2.create_translation(
            "file2_source2_target1_tra1", target=target1, user=user1
        )
        file2_source2_target1_tra2 = file2_source2.create_translation(
            "file2_source2_target1_tra2", target=target1, user=user2
        )
        file2_source2_target1_tra1.select(user=user1)
        # file2 target2
        file2_source1_target2_tra1 = file2_source1.create_translation(
            "file2_source1_target2_tra1", target=target2, user=user1
        )
        file2_source1_target2_tra2 = file2_source1.create_translation(
            "file2_source1_target2_tra2", target=target2, user=user2
        )
        file2_source1_target2_tra1.select(user=user1)

        file2_source2_target2_tra1 = file2_source2.create_translation(
            "file2_source2_target2_tra1", target=target2, user=user1
        )
        file2_source2_target2_tra2 = file2_source2.create_translation(
            "file2_source2_target2_tra2", target=target2, user=user2
        )
        file2_source2_target2_tra1.select(user=user1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
        )
        # == 删除 file2 ==
        file2.clear()
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=0,
            file2_target2_c=0,
        )
        # == 删除 file1 ==
        file1.clear()
        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

    def test_delete_root_folder(self):
        """测试直接删除根目录"""

        def check_cache(
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            try:
                file1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file1_target1_t + file1_target2_t),
                    file1.translated_source_count,
                )
                self.assertEqual(
                    (file1_target1_c + file1_target2_c),
                    file1.checked_source_count,
                )
                file1_target1.reload()
                self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
                self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
                file1_target2.reload()
                self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
                self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            try:
                file2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file2_target1_t + file2_target2_t),
                    file2.translated_source_count,
                )
                self.assertEqual(
                    (file2_target1_c + file2_target2_c),
                    file2.checked_source_count,
                )
                file2_target1.reload()
                self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
                file2_target2.reload()
                self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            try:
                dir1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target2.reload()
            else:
                self.assertEqual(
                    (
                        file1_target1_t
                        + file1_target2_t
                        + file2_target1_t
                        + file2_target2_t
                    ),
                    dir1.translated_source_count,
                )
                self.assertEqual(
                    (
                        file1_target1_c
                        + file1_target2_c
                        + file2_target1_c
                        + file2_target2_c
                    ),
                    dir1.checked_source_count,
                )
                dir1_target1.reload()
                self.assertEqual(
                    file1_target1_t + file2_target1_t,
                    dir1_target1.translated_source_count,
                )
                self.assertEqual(
                    file1_target1_c + file2_target1_c,
                    dir1_target1.checked_source_count,
                )
                dir1_target2.reload()
                self.assertEqual(
                    file1_target2_t + file2_target2_t,
                    dir1_target2.translated_source_count,
                )
                self.assertEqual(
                    file1_target2_c + file2_target2_c,
                    dir1_target2.checked_source_count,
                )
            # dir2 和他两个Cache
            try:
                dir2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target2.reload()
            else:
                self.assertEqual(
                    file2_target1_t + file2_target2_t,
                    dir2.translated_source_count,
                )
                self.assertEqual(
                    file2_target1_c + file2_target2_c,
                    dir2.checked_source_count,
                )
                dir2_target1.reload()
                self.assertEqual(file2_target1_t, dir2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, dir2_target1.checked_source_count)
                dir2_target2.reload()
                self.assertEqual(file2_target2_t, dir2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir1", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2_source2 = file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # 创建翻译
        # file1 target1
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        file1_source1_target1_tra2 = file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        file1_source1_target1_tra1.select(user=user1)

        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        file1_source2_target1_tra2 = file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        file1_source2_target1_tra1.select(user=user1)
        # file1 target2
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        file1_source1_target2_tra2 = file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        file1_source1_target2_tra1.select(user=user1)
        file1_source2_target2_tra1 = file1_source2.create_translation(
            "file1_source2_target2_tra1", target=target2, user=user1
        )
        file1_source2_target2_tra2 = file1_source2.create_translation(
            "file1_source2_target2_tra2", target=target2, user=user2
        )
        file1_source2_target2_tra1.select(user=user1)
        # file2 target1
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        file2_source1_target1_tra2 = file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        file2_source1_target1_tra1.select(user=user1)

        file2_source2_target1_tra1 = file2_source2.create_translation(
            "file2_source2_target1_tra1", target=target1, user=user1
        )
        file2_source2_target1_tra2 = file2_source2.create_translation(
            "file2_source2_target1_tra2", target=target1, user=user2
        )
        file2_source2_target1_tra1.select(user=user1)
        # file2 target2
        file2_source1_target2_tra1 = file2_source1.create_translation(
            "file2_source1_target2_tra1", target=target2, user=user1
        )
        file2_source1_target2_tra2 = file2_source1.create_translation(
            "file2_source1_target2_tra2", target=target2, user=user2
        )
        file2_source1_target2_tra1.select(user=user1)

        file2_source2_target2_tra1 = file2_source2.create_translation(
            "file2_source2_target2_tra1", target=target2, user=user1
        )
        file2_source2_target2_tra2 = file2_source2.create_translation(
            "file2_source2_target2_tra2", target=target2, user=user2
        )
        file2_source2_target2_tra1.select(user=user1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
        )
        # == 删除 dir1 ==
        dir1.clear()
        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

    def test_delete_folder(self):
        """测试删除dir1再删除dir2"""

        def check_cache(
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            try:
                file1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file1_target1_t + file1_target2_t),
                    file1.translated_source_count,
                )
                self.assertEqual(
                    (file1_target1_c + file1_target2_c),
                    file1.checked_source_count,
                )
                file1_target1.reload()
                self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
                self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
                file1_target2.reload()
                self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
                self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            try:
                file2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file2_target1_t + file2_target2_t),
                    file2.translated_source_count,
                )
                self.assertEqual(
                    (file2_target1_c + file2_target2_c),
                    file2.checked_source_count,
                )
                file2_target1.reload()
                self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
                file2_target2.reload()
                self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            try:
                dir1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target2.reload()
            else:
                self.assertEqual(
                    (
                        file1_target1_t
                        + file1_target2_t
                        + file2_target1_t
                        + file2_target2_t
                    ),
                    dir1.translated_source_count,
                )
                self.assertEqual(
                    (
                        file1_target1_c
                        + file1_target2_c
                        + file2_target1_c
                        + file2_target2_c
                    ),
                    dir1.checked_source_count,
                )
                dir1_target1.reload()
                self.assertEqual(
                    file1_target1_t + file2_target1_t,
                    dir1_target1.translated_source_count,
                )
                self.assertEqual(
                    file1_target1_c + file2_target1_c,
                    dir1_target1.checked_source_count,
                )
                dir1_target2.reload()
                self.assertEqual(
                    file1_target2_t + file2_target2_t,
                    dir1_target2.translated_source_count,
                )
                self.assertEqual(
                    file1_target2_c + file2_target2_c,
                    dir1_target2.checked_source_count,
                )
            # dir2 和他两个Cache
            try:
                dir2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir2.reload()
                with self.assertRaises(DoesNotExist):
                    dir2_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir2_target2.reload()
            else:
                self.assertEqual(
                    file2_target1_t + file2_target2_t,
                    dir2.translated_source_count,
                )
                self.assertEqual(
                    file2_target1_c + file2_target2_c,
                    dir2.checked_source_count,
                )
                dir2_target1.reload()
                self.assertEqual(file2_target1_t, dir2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, dir2_target1.checked_source_count)
                dir2_target2.reload()
                self.assertEqual(file2_target2_t, dir2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir1", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2_source2 = file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # 创建翻译
        # file1 target1
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        file1_source1_target1_tra2 = file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        file1_source1_target1_tra1.select(user=user1)

        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        file1_source2_target1_tra2 = file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        file1_source2_target1_tra1.select(user=user1)
        # file1 target2
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        file1_source1_target2_tra2 = file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        file1_source1_target2_tra1.select(user=user1)
        file1_source2_target2_tra1 = file1_source2.create_translation(
            "file1_source2_target2_tra1", target=target2, user=user1
        )
        file1_source2_target2_tra2 = file1_source2.create_translation(
            "file1_source2_target2_tra2", target=target2, user=user2
        )
        file1_source2_target2_tra1.select(user=user1)
        # file2 target1
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        file2_source1_target1_tra2 = file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        file2_source1_target1_tra1.select(user=user1)

        file2_source2_target1_tra1 = file2_source2.create_translation(
            "file2_source2_target1_tra1", target=target1, user=user1
        )
        file2_source2_target1_tra2 = file2_source2.create_translation(
            "file2_source2_target1_tra2", target=target1, user=user2
        )
        file2_source2_target1_tra1.select(user=user1)
        # file2 target2
        file2_source1_target2_tra1 = file2_source1.create_translation(
            "file2_source1_target2_tra1", target=target2, user=user1
        )
        file2_source1_target2_tra2 = file2_source1.create_translation(
            "file2_source1_target2_tra2", target=target2, user=user2
        )
        file2_source1_target2_tra1.select(user=user1)

        file2_source2_target2_tra1 = file2_source2.create_translation(
            "file2_source2_target2_tra1", target=target2, user=user1
        )
        file2_source2_target2_tra2 = file2_source2.create_translation(
            "file2_source2_target2_tra2", target=target2, user=user2
        )
        file2_source2_target2_tra1.select(user=user1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
        )
        # == 删除 dir2 ==
        dir2.clear()
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=0,
            file2_target2_c=0,
        )
        # == 删除 dir1 ==
        dir1.clear()
        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

    def test_delete_file_then_folder(self):
        """测试删除file2再删除dir2"""

        def check_cache(
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            try:
                file1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file1_target1_t + file1_target2_t),
                    file1.translated_source_count,
                )
                self.assertEqual(
                    (file1_target1_c + file1_target2_c),
                    file1.checked_source_count,
                )
                file1_target1.reload()
                self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
                self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
                file1_target2.reload()
                self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
                self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            try:
                file2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file2_target1_t + file2_target2_t),
                    file2.translated_source_count,
                )
                self.assertEqual(
                    (file2_target1_c + file2_target2_c),
                    file2.checked_source_count,
                )
                file2_target1.reload()
                self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
                file2_target2.reload()
                self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            try:
                dir1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target2.reload()
            else:
                self.assertEqual(
                    (
                        file1_target1_t
                        + file1_target2_t
                        + file2_target1_t
                        + file2_target2_t
                    ),
                    dir1.translated_source_count,
                )
                self.assertEqual(
                    (
                        file1_target1_c
                        + file1_target2_c
                        + file2_target1_c
                        + file2_target2_c
                    ),
                    dir1.checked_source_count,
                )
                dir1_target1.reload()
                self.assertEqual(
                    file1_target1_t + file2_target1_t,
                    dir1_target1.translated_source_count,
                )
                self.assertEqual(
                    file1_target1_c + file2_target1_c,
                    dir1_target1.checked_source_count,
                )
                dir1_target2.reload()
                self.assertEqual(
                    file1_target2_t + file2_target2_t,
                    dir1_target2.translated_source_count,
                )
                self.assertEqual(
                    file1_target2_c + file2_target2_c,
                    dir1_target2.checked_source_count,
                )
            # dir2 和他两个Cache
            try:
                dir2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir2.reload()
                with self.assertRaises(DoesNotExist):
                    dir2_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir2_target2.reload()
            else:
                self.assertEqual(
                    file2_target1_t + file2_target2_t,
                    dir2.translated_source_count,
                )
                self.assertEqual(
                    file2_target1_c + file2_target2_c,
                    dir2.checked_source_count,
                )
                dir2_target1.reload()
                self.assertEqual(file2_target1_t, dir2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, dir2_target1.checked_source_count)
                dir2_target2.reload()
                self.assertEqual(file2_target2_t, dir2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir1", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2_source2 = file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # 创建翻译
        # file1 target1
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        file1_source1_target1_tra2 = file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        file1_source1_target1_tra1.select(user=user1)

        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        file1_source2_target1_tra2 = file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        file1_source2_target1_tra1.select(user=user1)
        # file1 target2
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        file1_source1_target2_tra2 = file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        file1_source1_target2_tra1.select(user=user1)
        file1_source2_target2_tra1 = file1_source2.create_translation(
            "file1_source2_target2_tra1", target=target2, user=user1
        )
        file1_source2_target2_tra2 = file1_source2.create_translation(
            "file1_source2_target2_tra2", target=target2, user=user2
        )
        file1_source2_target2_tra1.select(user=user1)
        # file2 target1
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        file2_source1_target1_tra2 = file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        file2_source1_target1_tra1.select(user=user1)

        file2_source2_target1_tra1 = file2_source2.create_translation(
            "file2_source2_target1_tra1", target=target1, user=user1
        )
        file2_source2_target1_tra2 = file2_source2.create_translation(
            "file2_source2_target1_tra2", target=target1, user=user2
        )
        file2_source2_target1_tra1.select(user=user1)
        # file2 target2
        file2_source1_target2_tra1 = file2_source1.create_translation(
            "file2_source1_target2_tra1", target=target2, user=user1
        )
        file2_source1_target2_tra2 = file2_source1.create_translation(
            "file2_source1_target2_tra2", target=target2, user=user2
        )
        file2_source1_target2_tra1.select(user=user1)

        file2_source2_target2_tra1 = file2_source2.create_translation(
            "file2_source2_target2_tra1", target=target2, user=user1
        )
        file2_source2_target2_tra2 = file2_source2.create_translation(
            "file2_source2_target2_tra2", target=target2, user=user2
        )
        file2_source2_target2_tra1.select(user=user1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
        )
        # == 删除 file2 ==
        file2.clear()
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=0,
            file2_target2_c=0,
        )
        # == 删除 dir2，没有影响 ==
        dir2.clear()
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=0,
            file2_target2_c=0,
        )
        # == 删除 file1 ==
        file1.clear()
        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )
        # == 删除 dir1，没有影响 ==
        dir1.clear()
        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

    def test_delete_folder_then_file(self):
        """测试删除dir2再删除file1"""

        def check_cache(
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            try:
                file1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file1_target1_t + file1_target2_t),
                    file1.translated_source_count,
                )
                self.assertEqual(
                    (file1_target1_c + file1_target2_c),
                    file1.checked_source_count,
                )
                file1_target1.reload()
                self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
                self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
                file1_target2.reload()
                self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
                self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            try:
                file2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file2_target1_t + file2_target2_t),
                    file2.translated_source_count,
                )
                self.assertEqual(
                    (file2_target1_c + file2_target2_c),
                    file2.checked_source_count,
                )
                file2_target1.reload()
                self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
                file2_target2.reload()
                self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            try:
                dir1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target2.reload()
            else:
                self.assertEqual(
                    (
                        file1_target1_t
                        + file1_target2_t
                        + file2_target1_t
                        + file2_target2_t
                    ),
                    dir1.translated_source_count,
                )
                self.assertEqual(
                    (
                        file1_target1_c
                        + file1_target2_c
                        + file2_target1_c
                        + file2_target2_c
                    ),
                    dir1.checked_source_count,
                )
                dir1_target1.reload()
                self.assertEqual(
                    file1_target1_t + file2_target1_t,
                    dir1_target1.translated_source_count,
                )
                self.assertEqual(
                    file1_target1_c + file2_target1_c,
                    dir1_target1.checked_source_count,
                )
                dir1_target2.reload()
                self.assertEqual(
                    file1_target2_t + file2_target2_t,
                    dir1_target2.translated_source_count,
                )
                self.assertEqual(
                    file1_target2_c + file2_target2_c,
                    dir1_target2.checked_source_count,
                )
            # dir2 和他两个Cache
            try:
                dir2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir2.reload()
                with self.assertRaises(DoesNotExist):
                    dir2_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir2_target2.reload()
            else:
                self.assertEqual(
                    file2_target1_t + file2_target2_t,
                    dir2.translated_source_count,
                )
                self.assertEqual(
                    file2_target1_c + file2_target2_c,
                    dir2.checked_source_count,
                )
                dir2_target1.reload()
                self.assertEqual(file2_target1_t, dir2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, dir2_target1.checked_source_count)
                dir2_target2.reload()
                self.assertEqual(file2_target2_t, dir2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir1", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2_source2 = file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # 创建翻译
        # file1 target1
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        file1_source1_target1_tra2 = file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        file1_source1_target1_tra1.select(user=user1)

        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        file1_source2_target1_tra2 = file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        file1_source2_target1_tra1.select(user=user1)
        # file1 target2
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        file1_source1_target2_tra2 = file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        file1_source1_target2_tra1.select(user=user1)
        file1_source2_target2_tra1 = file1_source2.create_translation(
            "file1_source2_target2_tra1", target=target2, user=user1
        )
        file1_source2_target2_tra2 = file1_source2.create_translation(
            "file1_source2_target2_tra2", target=target2, user=user2
        )
        file1_source2_target2_tra1.select(user=user1)
        # file2 target1
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        file2_source1_target1_tra2 = file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        file2_source1_target1_tra1.select(user=user1)

        file2_source2_target1_tra1 = file2_source2.create_translation(
            "file2_source2_target1_tra1", target=target1, user=user1
        )
        file2_source2_target1_tra2 = file2_source2.create_translation(
            "file2_source2_target1_tra2", target=target1, user=user2
        )
        file2_source2_target1_tra1.select(user=user1)
        # file2 target2
        file2_source1_target2_tra1 = file2_source1.create_translation(
            "file2_source1_target2_tra1", target=target2, user=user1
        )
        file2_source1_target2_tra2 = file2_source1.create_translation(
            "file2_source1_target2_tra2", target=target2, user=user2
        )
        file2_source1_target2_tra1.select(user=user1)

        file2_source2_target2_tra1 = file2_source2.create_translation(
            "file2_source2_target2_tra1", target=target2, user=user1
        )
        file2_source2_target2_tra2 = file2_source2.create_translation(
            "file2_source2_target2_tra2", target=target2, user=user2
        )
        file2_source2_target2_tra1.select(user=user1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
        )
        # == 删除 dir2 ==
        dir2.clear()
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=0,
            file2_target2_c=0,
        )
        # == 删除 file1 ==
        file1.clear()
        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )
        # == 删除 dir1，没有影响 ==
        dir1.clear()
        check_cache(
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=0,
            file2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=0,
            file2_target2_c=0,
        )

    def test_move_to(self):
        """测试移动文件对计数的影响"""

        def check_cache(
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            dir1_target1_t,
            dir1_target2_t,
            dir2_target1_t,
            dir2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
            dir1_target1_c,
            dir1_target2_c,
            dir2_target1_c,
            dir2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            try:
                file1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file1_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file1_target1_t + file1_target2_t),
                    file1.translated_source_count,
                )
                self.assertEqual(
                    (file1_target1_c + file1_target2_c),
                    file1.checked_source_count,
                )
                file1_target1.reload()
                self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
                self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
                file1_target2.reload()
                self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
                self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            try:
                file2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    file2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_target2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source1_target2_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target1_tra2.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra1.reload()
                with self.assertRaises(DoesNotExist):
                    file2_source2_target2_tra2.reload()
            else:
                self.assertEqual(
                    (file2_target1_t + file2_target2_t),
                    file2.translated_source_count,
                )
                self.assertEqual(
                    (file2_target1_c + file2_target2_c),
                    file2.checked_source_count,
                )
                file2_target1.reload()
                self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
                self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
                file2_target2.reload()
                self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
                self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            try:
                dir1.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir1_target2.reload()
            else:
                self.assertEqual(
                    dir1_target1_t + dir1_target2_t,
                    dir1.translated_source_count,
                )
                self.assertEqual(
                    dir1_target1_c + dir1_target2_c, dir1.checked_source_count
                )
                dir1_target1.reload()
                self.assertEqual(dir1_target1_t, dir1_target1.translated_source_count)
                self.assertEqual(dir1_target1_c, dir1_target1.checked_source_count)
                dir1_target2.reload()
                self.assertEqual(dir1_target2_t, dir1_target2.translated_source_count)
                self.assertEqual(dir1_target2_c, dir1_target2.checked_source_count)
            # dir2 和他两个Cache
            try:
                dir2.reload()
            except DoesNotExist:  # 没有则说明target和翻译也没了
                with self.assertRaises(DoesNotExist):
                    dir2.reload()
                with self.assertRaises(DoesNotExist):
                    dir2_target1.reload()
                with self.assertRaises(DoesNotExist):
                    dir2_target2.reload()
            else:
                self.assertEqual(
                    dir2_target1_t + dir2_target2_t,
                    dir2.translated_source_count,
                )
                self.assertEqual(
                    dir2_target1_c + dir2_target2_c, dir2.checked_source_count
                )
                dir2_target1.reload()
                self.assertEqual(dir2_target1_t, dir2_target1.translated_source_count)
                self.assertEqual(dir2_target1_c, dir2_target1.checked_source_count)
                dir2_target2.reload()
                self.assertEqual(dir2_target2_t, dir2_target2.translated_source_count)
                self.assertEqual(dir2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir2", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2_source2 = file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # 创建翻译
        # file1 target1
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        file1_source1_target1_tra2 = file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        file1_source1_target1_tra1.select(user=user1)

        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        file1_source2_target1_tra2 = file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        file1_source2_target1_tra1.select(user=user1)
        # file1 target2
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        file1_source1_target2_tra2 = file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        file1_source1_target2_tra1.select(user=user1)
        file1_source2_target2_tra1 = file1_source2.create_translation(
            "file1_source2_target2_tra1", target=target2, user=user1
        )
        file1_source2_target2_tra2 = file1_source2.create_translation(
            "file1_source2_target2_tra2", target=target2, user=user2
        )
        file1_source2_target2_tra1.select(user=user1)
        # file2 target1
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        file2_source1_target1_tra2 = file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        file2_source1_target1_tra1.select(user=user1)

        file2_source2_target1_tra1 = file2_source2.create_translation(
            "file2_source2_target1_tra1", target=target1, user=user1
        )
        file2_source2_target1_tra2 = file2_source2.create_translation(
            "file2_source2_target1_tra2", target=target1, user=user2
        )
        file2_source2_target1_tra1.select(user=user1)
        # file2 target2
        file2_source1_target2_tra1 = file2_source1.create_translation(
            "file2_source1_target2_tra1", target=target2, user=user1
        )
        file2_source1_target2_tra2 = file2_source1.create_translation(
            "file2_source1_target2_tra2", target=target2, user=user2
        )
        file2_source1_target2_tra1.select(user=user1)

        file2_source2_target2_tra1 = file2_source2.create_translation(
            "file2_source2_target2_tra1", target=target2, user=user1
        )
        file2_source2_target2_tra2 = file2_source2.create_translation(
            "file2_source2_target2_tra2", target=target2, user=user2
        )
        file2_source2_target2_tra1.select(user=user1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=4,
            dir1_target2_t=4,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=4,
            dir1_target2_c=4,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )
        # == 移动dir2到root ==
        dir2.move_to(parent=None)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=2,
            dir1_target2_t=2,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=2,
            dir1_target2_c=2,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )
        # == 移动dir2到dir1 ==
        dir2.move_to(parent=dir1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=4,
            dir1_target2_t=4,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=4,
            dir1_target2_c=4,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )
        # == 移动file1到root ==
        file1.move_to(parent=None)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=2,
            dir1_target2_t=2,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=2,
            dir1_target2_c=2,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )
        # == 移动file1到dir2 ==
        file1.move_to(parent=dir2)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=4,
            dir1_target2_t=4,
            dir2_target1_t=4,
            dir2_target2_t=4,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=4,
            dir1_target2_c=4,
            dir2_target1_c=4,
            dir2_target2_c=4,
        )
        # == 连续的移动 ==
        file1.move_to(parent=dir1)
        file2.move_to(parent=dir1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=4,
            dir1_target2_t=4,
            dir2_target1_t=0,
            dir2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=4,
            dir1_target2_c=4,
            dir2_target1_c=0,
            dir2_target2_c=0,
        )
        file1.move_to(parent=None)
        file1.move_to(parent=dir1)
        file1.move_to(parent=dir2)
        file2.move_to(parent=None)
        file2.move_to(parent=dir2)
        file2.move_to(parent=dir1)
        dir2.move_to(parent=None)
        dir2.move_to(parent=dir1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=4,
            dir1_target2_t=4,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=4,
            dir1_target2_c=4,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )

    def test_activate_revision(self):
        """测试激活修订版对计数的影响"""

        def check_cache(
            file1,
            file2,
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            dir1_target1_t,
            dir1_target2_t,
            dir2_target1_t,
            dir2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
            dir1_target1_c,
            dir1_target2_c,
            dir2_target1_c,
            dir2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            file1.reload()
            file1_target1 = file1.cache(target1)
            file1_target2 = file1.cache(target2)
            self.assertEqual(
                (file1_target1_t + file1_target2_t),
                file1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c), file1.checked_source_count
            )
            file1_target1.reload()
            self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
            self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
            file1_target2.reload()
            self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
            self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            file2.reload()
            file2_target1 = file2.cache(target1)
            file2_target2 = file2.cache(target2)
            self.assertEqual(
                (file2_target1_t + file2_target2_t),
                file2.translated_source_count,
            )
            self.assertEqual(
                (file2_target1_c + file2_target2_c), file2.checked_source_count
            )
            file2_target1.reload()
            self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
            self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
            file2_target2.reload()
            self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
            self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            dir1.reload()
            self.assertEqual(
                dir1_target1_t + dir1_target2_t, dir1.translated_source_count
            )
            self.assertEqual(dir1_target1_c + dir1_target2_c, dir1.checked_source_count)
            dir1_target1.reload()
            self.assertEqual(dir1_target1_t, dir1_target1.translated_source_count)
            self.assertEqual(dir1_target1_c, dir1_target1.checked_source_count)
            dir1_target2.reload()
            self.assertEqual(dir1_target2_t, dir1_target2.translated_source_count)
            self.assertEqual(dir1_target2_c, dir1_target2.checked_source_count)
            # dir2 和他两个Cache
            dir2.reload()
            self.assertEqual(
                dir2_target1_t + dir2_target2_t, dir2.translated_source_count
            )
            self.assertEqual(dir2_target1_c + dir2_target2_c, dir2.checked_source_count)
            dir2_target1.reload()
            self.assertEqual(dir2_target1_t, dir2_target1.translated_source_count)
            self.assertEqual(dir2_target1_c, dir2_target1.checked_source_count)
            dir2_target2.reload()
            self.assertEqual(dir2_target2_t, dir2_target2.translated_source_count)
            self.assertEqual(dir2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir2", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2_source2 = file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # 创建翻译
        # file1 target1
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        file1_source1_target1_tra1.select(user=user1)
        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        file1_source2_target1_tra1.select(user=user1)
        # file1 target2
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        file1_source1_target2_tra1.select(user=user1)
        file1_source2_target2_tra1 = file1_source2.create_translation(
            "file1_source2_target2_tra1", target=target2, user=user1
        )
        file1_source2.create_translation(
            "file1_source2_target2_tra2", target=target2, user=user2
        )
        file1_source2_target2_tra1.select(user=user1)
        # file2 target1
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        file2_source1_target1_tra1.select(user=user1)

        file2_source2_target1_tra1 = file2_source2.create_translation(
            "file2_source2_target1_tra1", target=target1, user=user1
        )
        file2_source2.create_translation(
            "file2_source2_target1_tra2", target=target1, user=user2
        )
        file2_source2_target1_tra1.select(user=user1)
        # file2 target2
        file2_source1_target2_tra1 = file2_source1.create_translation(
            "file2_source1_target2_tra1", target=target2, user=user1
        )
        file2_source1.create_translation(
            "file2_source1_target2_tra2", target=target2, user=user2
        )
        file2_source1_target2_tra1.select(user=user1)

        file2_source2_target2_tra1 = file2_source2.create_translation(
            "file2_source2_target2_tra1", target=target2, user=user1
        )
        file2_source2.create_translation(
            "file2_source2_target2_tra2", target=target2, user=user2
        )
        file2_source2_target2_tra1.select(user=user1)
        check_cache(
            file1=file1,
            file2=file2,
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=4,
            dir1_target2_t=4,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=4,
            dir1_target2_c=4,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )
        # 为file1创建新修订版，仅创建修订版不影响缓存
        file1_new_revision1 = file1.create_revision()
        file1_new_revision2 = file1.create_revision()
        check_cache(
            file1=file1,
            file2=file2,
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=4,
            dir1_target2_t=4,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=4,
            dir1_target2_c=4,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )
        # 激活修订版
        file1_new_revision1.activate_revision()
        check_cache(
            file1=file1_new_revision1,
            file2=file2,
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=2,
            dir1_target2_t=2,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=2,
            dir1_target2_c=2,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )
        # 原file1没有变
        file1.reload()
        self.assertEqual(4, file1.translated_source_count)
        self.assertEqual(4, file1.checked_source_count)
        file1_target1.reload()
        self.assertEqual(2, file1_target1.translated_source_count)
        self.assertEqual(2, file1_target1.checked_source_count)
        file1_target2.reload()
        self.assertEqual(2, file1_target2.translated_source_count)
        self.assertEqual(2, file1_target2.checked_source_count)
        # 给file2新增revision，并给target1新增一个翻译
        file2_new_revision1 = file2.create_revision()
        file2_new_revision1.activate_revision()
        file2_new_revision1_source1 = file2_new_revision1.create_source("s1")
        t1 = file2_new_revision1_source1.create_translation("t1", target1, user=user1)
        t1.select(user=user1)
        check_cache(
            file1=file1_new_revision1,
            file2=file2_new_revision1,
            file1_target1_t=0,
            file1_target2_t=0,
            file2_target1_t=1,
            file2_target2_t=0,
            dir1_target1_t=1,
            dir1_target2_t=0,
            dir2_target1_t=1,
            dir2_target2_t=0,
            file1_target1_c=0,
            file1_target2_c=0,
            file2_target1_c=1,
            file2_target2_c=0,
            dir1_target1_c=1,
            dir1_target2_c=0,
            dir2_target1_c=1,
            dir2_target2_c=0,
        )
        # 原file2没有变
        file2.reload()
        self.assertEqual(4, file2.translated_source_count)
        self.assertEqual(4, file2.checked_source_count)
        file2_target1.reload()
        self.assertEqual(2, file2_target1.translated_source_count)
        self.assertEqual(2, file2_target1.checked_source_count)
        file2_target2.reload()
        self.assertEqual(2, file2_target2.translated_source_count)
        self.assertEqual(2, file2_target2.checked_source_count)
        # 切换回 file1
        file1.activate_revision()
        check_cache(
            file1=file1,
            file2=file2_new_revision1,
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=1,
            file2_target2_t=0,
            dir1_target1_t=3,
            dir1_target2_t=2,
            dir2_target1_t=1,
            dir2_target2_t=0,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=1,
            file2_target2_c=0,
            dir1_target1_c=3,
            dir1_target2_c=2,
            dir2_target1_c=1,
            dir2_target2_c=0,
        )
        # 原file1_new_revision1,没有变
        file1_new_revision1.reload()
        self.assertEqual(0, file1_new_revision1.translated_source_count)
        self.assertEqual(0, file1_new_revision1.checked_source_count)
        file1_new_revision1_target1 = file1_new_revision1.cache(target=target1)
        self.assertEqual(0, file1_new_revision1_target1.translated_source_count)
        self.assertEqual(0, file1_new_revision1_target1.checked_source_count)
        file1_new_revision1_target2 = file1_new_revision1.cache(target=target2)
        self.assertEqual(0, file1_new_revision1_target2.translated_source_count)
        self.assertEqual(0, file1_new_revision1_target2.checked_source_count)
        file1_new_revision2.reload()
        self.assertEqual(0, file1_new_revision2.translated_source_count)
        self.assertEqual(0, file1_new_revision2.checked_source_count)
        file1_new_revision2_target1 = file1_new_revision2.cache(target=target1)
        self.assertEqual(0, file1_new_revision2_target1.translated_source_count)
        self.assertEqual(0, file1_new_revision2_target1.checked_source_count)
        file1_new_revision2_target2 = file1_new_revision2.cache(target=target2)
        self.assertEqual(0, file1_new_revision2_target2.translated_source_count)
        self.assertEqual(0, file1_new_revision2_target2.checked_source_count)
        # 切换回 file2
        file2.activate_revision()
        check_cache(
            file1=file1,
            file2=file2,
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=4,
            dir1_target2_t=4,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=4,
            dir1_target2_c=4,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )
        # 原file2_new_revision1,没有变
        file2_new_revision1.reload()
        self.assertEqual(1, file2_new_revision1.translated_source_count)
        self.assertEqual(1, file2_new_revision1.checked_source_count)
        file2_new_revision1_target1 = file2_new_revision1.cache(target=target1)
        self.assertEqual(1, file2_new_revision1_target1.translated_source_count)
        self.assertEqual(1, file2_new_revision1_target1.checked_source_count)
        file2_new_revision1_target2 = file2_new_revision1.cache(target=target2)
        self.assertEqual(0, file2_new_revision1_target2.translated_source_count)
        self.assertEqual(0, file2_new_revision1_target2.checked_source_count)

    def test_copy_source(self):
        """测试复制Source对计数的影响"""

        def check_cache(
            file1,
            file2,
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            dir1_target1_t,
            dir1_target2_t,
            dir2_target1_t,
            dir2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
            dir1_target1_c,
            dir1_target2_c,
            dir2_target1_c,
            dir2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            file1.reload()
            file1_target1 = file1.cache(target1)
            file1_target2 = file1.cache(target2)
            self.assertEqual(
                (file1_target1_t + file1_target2_t),
                file1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c), file1.checked_source_count
            )
            file1_target1.reload()
            self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
            self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
            file1_target2.reload()
            self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
            self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            file2.reload()
            file2_target1 = file2.cache(target1)
            file2_target2 = file2.cache(target2)
            self.assertEqual(
                (file2_target1_t + file2_target2_t),
                file2.translated_source_count,
            )
            self.assertEqual(
                (file2_target1_c + file2_target2_c), file2.checked_source_count
            )
            file2_target1.reload()
            self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
            self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
            file2_target2.reload()
            self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
            self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            dir1.reload()
            self.assertEqual(
                dir1_target1_t + dir1_target2_t, dir1.translated_source_count
            )
            self.assertEqual(dir1_target1_c + dir1_target2_c, dir1.checked_source_count)
            dir1_target1.reload()
            self.assertEqual(dir1_target1_t, dir1_target1.translated_source_count)
            self.assertEqual(dir1_target1_c, dir1_target1.checked_source_count)
            dir1_target2.reload()
            self.assertEqual(dir1_target2_t, dir1_target2.translated_source_count)
            self.assertEqual(dir1_target2_c, dir1_target2.checked_source_count)
            # dir2 和他两个Cache
            dir2.reload()
            self.assertEqual(
                dir2_target1_t + dir2_target2_t, dir2.translated_source_count
            )
            self.assertEqual(dir2_target1_c + dir2_target2_c, dir2.checked_source_count)
            dir2_target1.reload()
            self.assertEqual(dir2_target1_t, dir2_target1.translated_source_count)
            self.assertEqual(dir2_target1_c, dir2_target1.checked_source_count)
            dir2_target2.reload()
            self.assertEqual(dir2_target2_t, dir2_target2.translated_source_count)
            self.assertEqual(dir2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir2", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2_source2 = file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # 创建翻译
        # file1 target1
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        file1_source1_target1_tra1.select(user=user1)

        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        file1_source2_target1_tra1.select(user=user1)
        # file1 target2
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        file1_source1_target2_tra1.select(user=user1)
        file1_source2_target2_tra1 = file1_source2.create_translation(
            "file1_source2_target2_tra1", target=target2, user=user1
        )
        file1_source2.create_translation(
            "file1_source2_target2_tra2", target=target2, user=user2
        )
        file1_source2_target2_tra1.select(user=user1)
        # file2 target1
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        file2_source1_target1_tra1.select(user=user1)

        file2_source2_target1_tra1 = file2_source2.create_translation(
            "file2_source2_target1_tra1", target=target1, user=user1
        )
        file2_source2_target1_tra2 = file2_source2.create_translation(
            "file2_source2_target1_tra2", target=target1, user=user2
        )
        file2_source2_target1_tra1.select(user=user1)
        # file2 target2
        file2_source1_target2_tra1 = file2_source1.create_translation(
            "file2_source1_target2_tra1", target=target2, user=user1
        )
        file2_source1.create_translation(
            "file2_source1_target2_tra2", target=target2, user=user2
        )
        file2_source1_target2_tra1.select(user=user1)

        file2_source2_target2_tra1 = file2_source2.create_translation(
            "file2_source2_target2_tra1", target=target2, user=user1
        )
        file2_source2.create_translation(
            "file2_source2_target2_tra2", target=target2, user=user2
        )
        file2_source2_target2_tra1.select(user=user1)
        check_cache(
            file1=file1,
            file2=file2,
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=4,
            dir1_target2_t=4,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=4,
            dir1_target2_c=4,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )
        # == file1建立新修订版，并复制一个翻译 ==
        # 为file1创建新修订版
        file1_new_revision1 = file1.create_revision()
        # 激活修订版
        file1_new_revision1.activate_revision()
        # 建立source
        file1_new_revision1_source1 = file1_new_revision1.create_source("ss1")
        # 复制原source
        file1_new_revision1_source1.copy(file1_source2)
        check_cache(
            file1=file1_new_revision1,
            file2=file2,
            file1_target1_t=1,
            file1_target2_t=1,
            file2_target1_t=2,
            file2_target2_t=2,
            dir1_target1_t=3,
            dir1_target2_t=3,
            dir2_target1_t=2,
            dir2_target2_t=2,
            file1_target1_c=1,
            file1_target2_c=1,
            file2_target1_c=2,
            file2_target2_c=2,
            dir1_target1_c=3,
            dir1_target2_c=3,
            dir2_target1_c=2,
            dir2_target2_c=2,
        )
        # 原file1没有变
        file1.reload()
        self.assertEqual(4, file1.translated_source_count)
        self.assertEqual(4, file1.checked_source_count)
        file1_target1.reload()
        self.assertEqual(2, file1_target1.translated_source_count)
        self.assertEqual(2, file1_target1.checked_source_count)
        file1_target2.reload()
        self.assertEqual(2, file1_target2.translated_source_count)
        self.assertEqual(2, file1_target2.checked_source_count)

        # == file2建立新修订版，并复制所有翻译 ==
        # 先给file2 删除翻译, target1 少1个翻译和一个选定
        file2_source2_target1_tra1.clear()
        file2_source2_target1_tra2.clear()
        check_cache(
            file1=file1_new_revision1,
            file2=file2,
            file1_target1_t=1,
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=2,
            dir1_target1_t=2,
            dir1_target2_t=3,
            dir2_target1_t=1,
            dir2_target2_t=2,
            file1_target1_c=1,
            file1_target2_c=1,
            file2_target1_c=1,
            file2_target2_c=2,
            dir1_target1_c=2,
            dir1_target2_c=3,
            dir2_target1_c=1,
            dir2_target2_c=2,
        )
        # 为file2创建新修订版
        file2_new_revision1 = file2.create_revision()
        # 激活修订版
        file2_new_revision1.activate_revision()
        # 建立source
        file2_new_revision1_source1 = file2_new_revision1.create_source("ss1")
        file2_new_revision1_source2 = file2_new_revision1.create_source("ss2")
        # 复制原source
        file2_new_revision1_source1.copy(file2_source2)
        file2_new_revision1_source2.copy(file2_source1)
        check_cache(
            file1=file1_new_revision1,
            file2=file2,
            file1_target1_t=1,
            file1_target2_t=1,
            file2_target1_t=1,
            file2_target2_t=2,
            dir1_target1_t=2,
            dir1_target2_t=3,
            dir2_target1_t=1,
            dir2_target2_t=2,
            file1_target1_c=1,
            file1_target2_c=1,
            file2_target1_c=1,
            file2_target2_c=2,
            dir1_target1_c=2,
            dir1_target2_c=3,
            dir2_target1_c=1,
            dir2_target2_c=2,
        )
        # 原file2没有变
        file2.reload()
        self.assertEqual(3, file2.translated_source_count)
        self.assertEqual(3, file2.checked_source_count)
        file2_target1.reload()
        self.assertEqual(1, file2_target1.translated_source_count)
        self.assertEqual(1, file2_target1.checked_source_count)
        file2_target2.reload()
        self.assertEqual(2, file2_target2.translated_source_count)
        self.assertEqual(2, file2_target2.checked_source_count)

    def test_upload_new_revision(self):
        """测试上传新修订版对计数的影响"""
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
        target1 = project.targets().first()
        target2 = Target.create(project=project, language=Language.by_code("en"))
        dir = project.create_folder("dir")
        user = User(name="u1", email="u1").save()
        user2 = User(name="u2", email="u2").save()
        # 上传revisionA.txt
        with open(os.path.join(TEST_FILE_PATH, "revisionA.txt"), "rb") as file:
            revision_a = project.upload("1.txt", file, parent=dir)
            # 检查项目属性
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(1, project.files(type_exclude=FileType.FOLDER).count())
            # 检查文件相关的原文数
            self.assertEqual(4, revision_a.source_count)  # 不含空格有4行
            self.assertEqual(5, revision_a.sources().count())  # 含空格有5行
            # 给文章添加翻译
            for i, source in enumerate(revision_a.sources()):
                t = source.create_translation(str(i + 2), target1, user=user)
                source.create_translation(
                    str(i), target1, user=user
                )  # 再修改一遍，不会导致已翻译的计数出错
                source.create_tip(str(i), target1, user=user)
                t.select(user=user)
            # target2少一个5
            for i, source in enumerate(revision_a.sources()):
                if i == 3:
                    continue
                t = source.create_translation(str(i + 2), target2, user=user)
                source.create_translation(
                    str(i), target2, user=user
                )  # 再修改一遍，不会导致已翻译的计数出错
                source.create_tip(str(i), target2, user=user)
                t.select(user=user)
            # 检查project的Cache
            project.reload()
            target1.reload()
            target2.reload()
            self.assertEqual(7, project.translated_source_count)
            self.assertEqual(4, target1.translated_source_count)
            self.assertEqual(3, target2.translated_source_count)
            self.assertEqual(7, project.checked_source_count)
            self.assertEqual(4, target1.checked_source_count)
            self.assertEqual(3, target2.checked_source_count)
            # 检查dir的Cache
            dir.reload()
            self.assertEqual(7, dir.translated_source_count)
            self.assertEqual(4, dir.cache(target=target1).translated_source_count)
            self.assertEqual(3, dir.cache(target=target2).translated_source_count)
            self.assertEqual(7, dir.checked_source_count)
            self.assertEqual(4, dir.cache(target=target1).checked_source_count)
            self.assertEqual(3, dir.cache(target=target2).checked_source_count)
            # 检查file[修订版a]的Cache
            revision_a.reload()
            self.assertEqual(7, revision_a.translated_source_count)  # 不含空格有7行
            self.assertEqual(
                4, revision_a.cache(target=target1).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(
                3, revision_a.cache(target=target2).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(7, revision_a.checked_source_count)  # 不含空格有7行
            self.assertEqual(
                4, revision_a.cache(target=target1).checked_source_count
            )  # 不含空格有4行
            self.assertEqual(
                3, revision_a.cache(target=target2).checked_source_count
            )  # 不含空格有4行
            # 检查target1翻译内容
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.translations(target=target1)]
                    for source in revision_a.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], ["2"], ["3"], ["4"]],
                [
                    [item.content for item in source.tips(target=target1)]
                    for source in revision_a.sources()
                ],
            )
            # 检查target2翻译内容
            self.assertEqual(
                [["0"], ["1"], ["2"], [], ["4"]],
                [
                    [item.content for item in source.translations(target=target2)]
                    for source in revision_a.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], ["2"], [], ["4"]],
                [
                    [item.content for item in source.tips(target=target2)]
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
            revision_b = project.upload("1.txt", file, parent=dir)
            # 检查项目属性
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(1, project.files(type_exclude=FileType.FOLDER).count())
            # 检查文件相关的原文数
            self.assertEqual(5, revision_b.source_count)  # 新的原文，不含空格有5行
            self.assertEqual(7, revision_b.sources().count())  # 新的原文，含空格有7行
            # 之前有翻译且能找到一模一样原文的有5个，target1 3个，target2 2个
            # 检查project的Cache
            project.reload()
            target1.reload()
            target2.reload()
            self.assertEqual(5, project.translated_source_count)
            self.assertEqual(3, target1.translated_source_count)
            self.assertEqual(2, target2.translated_source_count)
            self.assertEqual(5, project.checked_source_count)
            self.assertEqual(3, target1.checked_source_count)
            self.assertEqual(2, target2.checked_source_count)
            # 检查dir的Cache
            dir.reload()
            self.assertEqual(5, dir.translated_source_count)
            self.assertEqual(3, dir.cache(target=target1).translated_source_count)
            self.assertEqual(2, dir.cache(target=target2).translated_source_count)
            self.assertEqual(5, dir.checked_source_count)
            self.assertEqual(3, dir.cache(target=target1).checked_source_count)
            self.assertEqual(2, dir.cache(target=target2).checked_source_count)
            # 检查file[修订版b]的Cache
            revision_b.reload()
            self.assertEqual(5, revision_b.translated_source_count)  # 不含空格有7行
            self.assertEqual(
                3, revision_b.cache(target=target1).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(
                2, revision_b.cache(target=target2).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(5, revision_b.checked_source_count)  # 不含空格有7行
            self.assertEqual(
                3, revision_b.cache(target=target1).checked_source_count
            )  # 不含空格有4行
            self.assertEqual(
                2, revision_b.cache(target=target2).checked_source_count
            )  # 不含空格有4行
            # 检查file[修订版a]的Cache，没有变化
            revision_a.reload()
            self.assertEqual(7, revision_a.translated_source_count)  # 不含空格有7行
            self.assertEqual(
                4, revision_a.cache(target=target1).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(
                3, revision_a.cache(target=target2).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(7, revision_a.checked_source_count)  # 不含空格有7行
            self.assertEqual(
                4, revision_a.cache(target=target1).checked_source_count
            )  # 不含空格有4行
            self.assertEqual(
                3, revision_a.cache(target=target2).checked_source_count
            )  # 不含空格有4行
            # 检查target1翻译内容
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.translations(target=target1)]
                    for source in revision_b.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], []],
                [
                    [item.content for item in source.tips(target=target1)]
                    for source in revision_b.sources()
                ],
            )
            # 检查target2翻译内容
            self.assertEqual(
                [["0"], ["1"], [], [], [], [], []],
                [
                    [item.content for item in source.translations(target=target2)]
                    for source in revision_b.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], [], [], [], [], []],
                [
                    [item.content for item in source.tips(target=target2)]
                    for source in revision_b.sources()
                ],
            )
            # 给“五”增加翻译
            revision_b.sources()[5].create_translation("5-1", target1, user=user)
            revision_b.sources()[5].create_tip("5-1", target1, user=user)
            revision_b.sources()[5].create_translation(
                "5-2", target1, user=user
            )  # 同用户，翻译覆盖
            revision_b.sources()[5].create_tip(
                "5-2", target1, user=user
            )  # 同用户，提示新增
            revision_b.sources()[5].create_translation(
                "5-3", target1, user=user2
            )  # 不同用户，翻译新增
            revision_b.sources()[5].create_tip(
                "5-3", target1, user=user2
            )  # 不同用户，提示新增
            revision_b.sources()[5].create_translation("5-1", target2, user=user)
            revision_b.sources()[5].create_tip("5-1", target2, user=user)
            revision_b.sources()[5].create_translation(
                "5-2", target2, user=user
            )  # 同用户，翻译覆盖
            revision_b.sources()[5].create_tip(
                "5-2", target2, user=user
            )  # 同用户，提示新增
            revision_b.sources()[5].create_translation(
                "5-3", target2, user=user2
            )  # 不同用户，翻译新增
            revision_b.sources()[5].create_tip(
                "5-3", target2, user=user2
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
            revision_c = project.upload("1.txt", file, parent=dir)
            # 检查项目属性
            project.reload()
            self.assertEqual(1, project.file_count)
            self.assertEqual(1, project.files(type_exclude=FileType.FOLDER).count())
            # 检查文件相关的原文数
            self.assertEqual(7, revision_c.source_count)  # 新的原文，不含空格有7行
            self.assertEqual(8, revision_c.sources().count())  # 新的原文，含空格有8行
            # 之前有翻译且能找到一模一样原文的有9行，target1 5行，target2 4行
            # 检查project的Cache
            project.reload()
            target1.reload()
            target2.reload()
            self.assertEqual(9, project.translated_source_count)
            self.assertEqual(5, target1.translated_source_count)
            self.assertEqual(4, target2.translated_source_count)
            # 新增的5没有selected，
            self.assertEqual(7, project.checked_source_count)
            self.assertEqual(4, target1.checked_source_count)
            self.assertEqual(3, target2.checked_source_count)
            # 检查dir的Cache
            dir.reload()
            self.assertEqual(9, dir.translated_source_count)
            self.assertEqual(5, dir.cache(target=target1).translated_source_count)
            self.assertEqual(4, dir.cache(target=target2).translated_source_count)
            self.assertEqual(7, dir.checked_source_count)
            self.assertEqual(4, dir.cache(target=target1).checked_source_count)
            self.assertEqual(3, dir.cache(target=target2).checked_source_count)
            # 检查file[修订版c]的Cache
            revision_c.reload()
            self.assertEqual(9, revision_c.translated_source_count)  # 不含空格有7行
            self.assertEqual(
                5, revision_c.cache(target=target1).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(
                4, revision_c.cache(target=target2).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(7, revision_c.checked_source_count)  # 不含空格有7行
            self.assertEqual(
                4, revision_c.cache(target=target1).checked_source_count
            )  # 不含空格有4行
            self.assertEqual(
                3, revision_c.cache(target=target2).checked_source_count
            )  # 不含空格有4行
            # 检查file[修订版b]的Cache，b的翻译增加了一个“5”，所以target1、target2各增加一个
            revision_b.reload()
            self.assertEqual(7, revision_b.translated_source_count)  # 不含空格有7行
            self.assertEqual(
                4, revision_b.cache(target=target1).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(
                3, revision_b.cache(target=target2).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(5, revision_b.checked_source_count)  # 不含空格有7行
            self.assertEqual(
                3, revision_b.cache(target=target1).checked_source_count
            )  # 不含空格有4行
            self.assertEqual(
                2, revision_b.cache(target=target2).checked_source_count
            )  # 不含空格有4行
            # 检查file[修订版a]的Cache，没有变化
            revision_a.reload()
            self.assertEqual(7, revision_a.translated_source_count)  # 不含空格有7行
            self.assertEqual(
                4, revision_a.cache(target=target1).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(
                3, revision_a.cache(target=target2).translated_source_count
            )  # 不含空格有4行
            self.assertEqual(7, revision_a.checked_source_count)  # 不含空格有7行
            self.assertEqual(
                4, revision_a.cache(target=target1).checked_source_count
            )  # 不含空格有4行
            self.assertEqual(
                3, revision_a.cache(target=target2).checked_source_count
            )  # 不含空格有4行
            # 检查target1翻译内容
            self.assertEqual(
                5, revision_c.cache(target=target1).translated_source_count
            )
            self.assertEqual(
                [["0"], ["1"], [], ["3"], [], [], ["5-3", "5-2"], ["1"]],
                [
                    [item.content for item in source.translations(target=target1)]
                    for source in revision_c.sources()
                ],
            )
            self.assertEqual(
                [
                    ["0"],
                    ["1"],
                    [],
                    ["3"],
                    [],
                    [],
                    ["5-3", "5-2", "5-1"],
                    ["1"],
                ],
                [
                    [item.content for item in source.tips(target=target1)]
                    for source in revision_c.sources()
                ],
            )
            # 检查target2翻译内容
            self.assertEqual(
                4, revision_c.cache(target=target2).translated_source_count
            )
            self.assertEqual(
                [["0"], ["1"], [], [], [], [], ["5-3", "5-2"], ["1"]],
                [
                    [item.content for item in source.translations(target=target2)]
                    for source in revision_c.sources()
                ],
            )
            self.assertEqual(
                [["0"], ["1"], [], [], [], [], ["5-3", "5-2", "5-1"], ["1"]],
                [
                    [item.content for item in source.tips(target=target2)]
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

    def test_delete_project(self):
        """测试删除project时Cache关联删除"""

        def check_cache(
            file1_target1_t,
            file1_target2_t,
            file2_target1_t,
            file2_target2_t,
            file1_target1_c,
            file1_target2_c,
            file2_target1_c,
            file2_target2_c,
        ):
            # 验证数量
            # Project 和 Target
            project.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                project.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                project.checked_source_count,
            )
            target1.reload()
            self.assertEqual(
                (file1_target1_t + file2_target1_t),
                target1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file2_target1_c),
                target1.checked_source_count,
            )
            target2.reload()
            self.assertEqual(
                (file1_target2_t + file2_target2_t),
                target2.translated_source_count,
            )
            self.assertEqual(
                (file1_target2_c + file2_target2_c),
                target2.checked_source_count,
            )
            # file1和它的两个Cache
            file1.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t),
                file1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c), file1.checked_source_count
            )
            file1_target1.reload()
            self.assertEqual(file1_target1_t, file1_target1.translated_source_count)
            self.assertEqual(file1_target1_c, file1_target1.checked_source_count)
            file1_target2.reload()
            self.assertEqual(file1_target2_t, file1_target2.translated_source_count)
            self.assertEqual(file1_target2_c, file1_target2.checked_source_count)
            # file2和它的两个Cache
            file2.reload()
            self.assertEqual(
                (file2_target1_t + file2_target2_t),
                file2.translated_source_count,
            )
            self.assertEqual(
                (file2_target1_c + file2_target2_c), file2.checked_source_count
            )
            file2_target1.reload()
            self.assertEqual(file2_target1_t, file2_target1.translated_source_count)
            self.assertEqual(file2_target1_c, file2_target1.checked_source_count)
            file2_target2.reload()
            self.assertEqual(file2_target2_t, file2_target2.translated_source_count)
            self.assertEqual(file2_target2_c, file2_target2.checked_source_count)
            # dir1 和他两个Cache
            dir1.reload()
            self.assertEqual(
                (file1_target1_t + file1_target2_t + file2_target1_t + file2_target2_t),
                dir1.translated_source_count,
            )
            self.assertEqual(
                (file1_target1_c + file1_target2_c + file2_target1_c + file2_target2_c),
                dir1.checked_source_count,
            )
            dir1_target1.reload()
            self.assertEqual(
                file1_target1_t + file2_target1_t,
                dir1_target1.translated_source_count,
            )
            self.assertEqual(
                file1_target1_c + file2_target1_c,
                dir1_target1.checked_source_count,
            )
            dir1_target2.reload()
            self.assertEqual(
                file1_target2_t + file2_target2_t,
                dir1_target2.translated_source_count,
            )
            self.assertEqual(
                file1_target2_c + file2_target2_c,
                dir1_target2.checked_source_count,
            )
            # dir2 和他两个Cache
            dir2.reload()
            self.assertEqual(
                file2_target1_t + file2_target2_t, dir2.translated_source_count
            )
            self.assertEqual(
                file2_target1_c + file2_target2_c, dir2.checked_source_count
            )
            dir2_target1.reload()
            self.assertEqual(file2_target1_t, dir2_target1.translated_source_count)
            self.assertEqual(file2_target1_c, dir2_target1.checked_source_count)
            dir2_target2.reload()
            self.assertEqual(file2_target2_t, dir2_target2.translated_source_count)
            self.assertEqual(file2_target2_c, dir2_target2.checked_source_count)

        # == 创建测试数据 ==
        self.create_user("11", "1@1.com", "111111").generate_token()
        user1 = User.objects(email="1@1.com").first()
        self.create_user("22", "2@1.com", "111111").generate_token()
        user2 = User.objects(email="2@1.com").first()
        team = Team.create("t1", creator=user1)
        project = Project.create(
            "p2",
            team=team,
            creator=user1,
            source_language=Language.by_code("en"),
            target_languages=[
                Language.by_code("zh-CN"),
                Language.by_code("ja"),
            ],
        )
        user1.join(project, role=ProjectRole.by_system_code("admin"))
        """
        |
        -dir1
            |
            -file1
            -dir2
                |
                file2
        """
        target1 = project.targets(Language.by_code("zh-CN")).first()
        target2 = project.targets(Language.by_code("ja")).first()
        # 文件夹
        dir1 = project.create_folder("dir1")
        dir1_target1 = dir1.cache(target=target1)
        dir1_target2 = dir1.cache(target=target2)
        dir2 = project.create_folder("dir1", parent=dir1)
        dir2_target1 = dir2.cache(target=target1)
        dir2_target2 = dir2.cache(target=target2)
        # file1
        file1 = project.create_file("1.txt", parent=dir1)
        file1_source1 = file1.create_source("file1_source1")
        file1_source2 = file1.create_source("file1_source2")
        file1_target1 = file1.cache(target=target1)
        file1_target2 = file1.cache(target=target2)
        # file2
        file2 = project.create_file("1.jpg", parent=dir2)
        file2_source1 = file2.create_source("file2_source1")
        file2_source2 = file2.create_source("file2_source2")
        file2_target1 = file2.cache(target=target1)
        file2_target2 = file2.cache(target=target2)
        # 创建翻译
        # file1 target1
        file1_source1_target1_tra1 = file1_source1.create_translation(
            "file1_source1_target1_tra1", target=target1, user=user1
        )
        file1_source1_target1_tra2 = file1_source1.create_translation(
            "file1_source1_target1_tra2", target=target1, user=user2
        )
        file1_source1_target1_tra1.select(user=user1)

        file1_source2_target1_tra1 = file1_source2.create_translation(
            "file1_source2_target1_tra1", target=target1, user=user1
        )
        file1_source2_target1_tra2 = file1_source2.create_translation(
            "file1_source2_target1_tra2", target=target1, user=user2
        )
        file1_source2_target1_tra1.select(user=user1)
        # file1 target2
        file1_source1_target2_tra1 = file1_source1.create_translation(
            "file1_source1_target2_tra1", target=target2, user=user1
        )
        file1_source1_target2_tra2 = file1_source1.create_translation(
            "file1_source1_target2_tra2", target=target2, user=user2
        )
        file1_source1_target2_tra1.select(user=user1)
        file1_source2_target2_tra1 = file1_source2.create_translation(
            "file1_source2_target2_tra1", target=target2, user=user1
        )
        file1_source2_target2_tra2 = file1_source2.create_translation(
            "file1_source2_target2_tra2", target=target2, user=user2
        )
        file1_source2_target2_tra1.select(user=user1)
        # file2 target1
        file2_source1_target1_tra1 = file2_source1.create_translation(
            "file2_source1_target1_tra1", target=target1, user=user1
        )
        file2_source1_target1_tra2 = file2_source1.create_translation(
            "file2_source1_target1_tra2", target=target1, user=user2
        )
        file2_source1_target1_tra1.select(user=user1)

        file2_source2_target1_tra1 = file2_source2.create_translation(
            "file2_source2_target1_tra1", target=target1, user=user1
        )
        file2_source2_target1_tra2 = file2_source2.create_translation(
            "file2_source2_target1_tra2", target=target1, user=user2
        )
        file2_source2_target1_tra1.select(user=user1)
        # file2 target2
        file2_source1_target2_tra1 = file2_source1.create_translation(
            "file2_source1_target2_tra1", target=target2, user=user1
        )
        file2_source1_target2_tra2 = file2_source1.create_translation(
            "file2_source1_target2_tra2", target=target2, user=user2
        )
        file2_source1_target2_tra1.select(user=user1)

        file2_source2_target2_tra1 = file2_source2.create_translation(
            "file2_source2_target2_tra1", target=target2, user=user1
        )
        file2_source2_target2_tra2 = file2_source2.create_translation(
            "file2_source2_target2_tra2", target=target2, user=user2
        )
        file2_source2_target2_tra1.select(user=user1)
        check_cache(
            file1_target1_t=2,
            file1_target2_t=2,
            file2_target1_t=2,
            file2_target2_t=2,
            file1_target1_c=2,
            file1_target2_c=2,
            file2_target1_c=2,
            file2_target2_c=2,
        )
        project.clear()
        with self.assertRaises(DoesNotExist):
            project.reload()
        with self.assertRaises(DoesNotExist):
            target1.reload()
        with self.assertRaises(DoesNotExist):
            target2.reload()
        with self.assertRaises(DoesNotExist):
            dir1.reload()
        with self.assertRaises(DoesNotExist):
            dir1_target1.reload()
        with self.assertRaises(DoesNotExist):
            dir1_target2.reload()
        with self.assertRaises(DoesNotExist):
            dir2.reload()
        with self.assertRaises(DoesNotExist):
            dir2_target1.reload()
        with self.assertRaises(DoesNotExist):
            dir2_target2.reload()
        with self.assertRaises(DoesNotExist):
            file1.reload()
        with self.assertRaises(DoesNotExist):
            file1_source1.reload()
        with self.assertRaises(DoesNotExist):
            file1_source2.reload()
        with self.assertRaises(DoesNotExist):
            file1_target1.reload()
        with self.assertRaises(DoesNotExist):
            file1_target2.reload()
        with self.assertRaises(DoesNotExist):
            file2.reload()
        with self.assertRaises(DoesNotExist):
            file2_source1.reload()
        with self.assertRaises(DoesNotExist):
            file2_source2.reload()
        with self.assertRaises(DoesNotExist):
            file2_target1.reload()
        with self.assertRaises(DoesNotExist):
            file2_target2.reload()
        with self.assertRaises(DoesNotExist):
            file1_source1_target1_tra1.reload()
        with self.assertRaises(DoesNotExist):
            file1_source1_target1_tra2.reload()
        with self.assertRaises(DoesNotExist):
            file1_source2_target1_tra1.reload()
        with self.assertRaises(DoesNotExist):
            file1_source2_target1_tra2.reload()
        with self.assertRaises(DoesNotExist):
            file1_source1_target2_tra1.reload()
        with self.assertRaises(DoesNotExist):
            file1_source1_target2_tra2.reload()
        with self.assertRaises(DoesNotExist):
            file1_source2_target2_tra1.reload()
        with self.assertRaises(DoesNotExist):
            file1_source2_target2_tra2.reload()
        with self.assertRaises(DoesNotExist):
            file2_source1_target1_tra1.reload()
        with self.assertRaises(DoesNotExist):
            file2_source1_target1_tra2.reload()
        with self.assertRaises(DoesNotExist):
            file2_source2_target1_tra1.reload()
        with self.assertRaises(DoesNotExist):
            file2_source2_target1_tra2.reload()
        with self.assertRaises(DoesNotExist):
            file2_source1_target2_tra1.reload()
        with self.assertRaises(DoesNotExist):
            file2_source1_target2_tra2.reload()
        with self.assertRaises(DoesNotExist):
            file2_source2_target2_tra1.reload()
        with self.assertRaises(DoesNotExist):
            file2_source2_target2_tra2.reload()
        self.assertEqual(0, Project.objects.count())
        self.assertEqual(0, Target.objects.count())
        self.assertEqual(0, FileTargetCache.objects.count())
        self.assertEqual(0, File.objects.count())
        self.assertEqual(0, Source.objects.count())
        self.assertEqual(0, Translation.objects.count())
        self.assertEqual(0, Tip.objects.count())
