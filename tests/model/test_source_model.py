from app.models.file import File, Source
from app.models.project import Project
from app.models.team import Team
from app.models.user import User
from app.constants.file import FileType
from tests import MoeAPITestCase


class SourceTestCase(MoeAPITestCase):
    @staticmethod
    def by_content(content):
        return Source.objects(content=content).first()

    def create_test_sources(self, count):
        self.create_user("11", "1@1.com", "111111").generate_token()
        user = User.objects(email="1@1.com").first()
        team = Team.create("t1", creator=user)
        # 创建一个项目用于测试
        project = Project.create("p1", team=team, creator=user)
        file = project.create_file("1.jpg")
        for i in range(count):
            file.create_source(f"{i+1}")

    def assertRank(self, content_list):
        # 排序的rank [0, 1, 2, 3, 4, 5, 6]
        sorted_ranks = list(range(len(content_list)))
        # 按rank排序查出的sources
        sorted_sources = Source.objects().order_by("rank")
        # Source的rank需要是 [0, 1, 2, 3, 4, 5, 6]
        self.assertListEqual(sorted_ranks, [source.rank for source in sorted_sources])
        # 内容需要和content_list相同
        self.assertListEqual(
            content_list, [source.content for source in sorted_sources]
        )

    # 移动1
    def test_move_ahead1(self):
        """
        before: 1 2 3 4 5 6 7
               ^+
        after : 1 2 3 4 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("1")
        next_source = source
        source.move_ahead(next_source)
        self.assertRank(["1", "2", "3", "4", "5", "6", "7"])

    def test_move_ahead2(self):
        """
        before: 1 2 3 4 5 6 7
                +^
        after : 1 2 3 4 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("1")
        next_source = self.by_content("2")
        source.move_ahead(next_source)
        self.assertRank(["1", "2", "3", "4", "5", "6", "7"])

    def test_move_ahead3(self):
        """
        before: 1 2 3 4 5 6 7
                +--^
        after : 2 1 3 4 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("1")
        next_source = self.by_content("3")
        source.move_ahead(next_source)
        self.assertRank(["2", "1", "3", "4", "5", "6", "7"])

    def test_move_ahead4(self):
        """
        before: 1 2 3 4 5 6 7
                +------^
        after : 2 3 4 1 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("1")
        next_source = self.by_content("5")
        source.move_ahead(next_source)
        self.assertRank(["2", "3", "4", "1", "5", "6", "7"])

    def test_move_ahead5(self):
        """
        before: 1 2 3 4 5 6 7
                +------------^
        after : 2 3 4 5 6 7 1
        """
        self.create_test_sources(7)
        source = self.by_content("1")
        source.move_ahead(None)
        self.assertRank(["2", "3", "4", "5", "6", "7", "1"])

    # 移动7
    def test_move_ahead6(self):
        """
        before: 1 2 3 4 5 6 7
                            +^
        after : 1 2 3 4 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("7")
        source.move_ahead(None)
        self.assertRank(["1", "2", "3", "4", "5", "6", "7"])

    def test_move_ahead7(self):
        """
        before: 1 2 3 4 5 6 7
                           ^+
        after : 1 2 3 4 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("7")
        next_source = self.by_content("7")
        source.move_ahead(next_source)
        self.assertRank(["1", "2", "3", "4", "5", "6", "7"])

    def test_move_ahead8(self):
        """
        before: 1 2 3 4 5 6 7
                         ^--+
        after : 1 2 3 4 5 7 6
        """
        self.create_test_sources(7)
        source = self.by_content("7")
        next_source = self.by_content("6")
        source.move_ahead(next_source)
        self.assertRank(["1", "2", "3", "4", "5", "7", "6"])

    def test_move_ahead9(self):
        """
        before: 1 2 3 4 5 6 7
                     ^------+
        after : 1 2 3 7 4 5 6
        """
        self.create_test_sources(7)
        source = self.by_content("7")
        next_source = self.by_content("4")
        source.move_ahead(next_source)
        self.assertRank(["1", "2", "3", "7", "4", "5", "6"])

    def test_move_ahead10(self):
        """
        before: 1 2 3 4 5 6 7
               ^------------+
        after : 1 2 3 7 4 5 6
        """
        self.create_test_sources(7)
        source = self.by_content("7")
        next_source = self.by_content("1")
        source.move_ahead(next_source)
        self.assertRank(["7", "1", "2", "3", "4", "5", "6"])

    # 4向后移动
    def test_move_ahead11(self):
        """
        before: 1 2 3 4 5 6 7
                      +^
        after : 1 2 3 4 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("4")
        next_source = self.by_content("5")
        source.move_ahead(next_source)
        self.assertRank(["1", "2", "3", "4", "5", "6", "7"])

    def test_move_ahead12(self):
        """
        before: 1 2 3 4 5 6 7
                      +--^
        after : 1 2 3 5 4 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("4")
        next_source = self.by_content("6")
        source.move_ahead(next_source)
        self.assertRank(["1", "2", "3", "5", "4", "6", "7"])

    def test_move_ahead13(self):
        """
        before: 1 2 3 4 5 6 7
                      +----^
        after : 1 2 3 5 6 4 7
        """
        self.create_test_sources(7)
        source = self.by_content("4")
        next_source = self.by_content("7")
        source.move_ahead(next_source)
        self.assertRank(["1", "2", "3", "5", "6", "4", "7"])

    def test_move_ahead14(self):
        """
        before: 1 2 3 4 5 6 7
                      +------^
        after : 1 2 3 5 6 7 4
        """
        self.create_test_sources(7)
        source = self.by_content("4")
        source.move_ahead(None)
        self.assertRank(["1", "2", "3", "5", "6", "7", "4"])

    # 4向前移动
    def test_move_ahead15(self):
        """
        before: 1 2 3 4 5 6 7
                     ^+
        after : 1 2 3 4 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("4")
        next_source = source
        source.move_ahead(next_source)
        self.assertRank(["1", "2", "3", "4", "5", "6", "7"])

    # 4向前移动
    def test_move_ahead16(self):
        """
        before: 1 2 3 4 5 6 7
                   ^--+
        after : 1 2 4 3 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("4")
        next_source = self.by_content("3")
        source.move_ahead(next_source)
        self.assertRank(["1", "2", "4", "3", "5", "6", "7"])

    def test_move_ahead17(self):
        """
        before: 1 2 3 4 5 6 7
                 ^----+
        after : 1 4 2 3 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("4")
        next_source = self.by_content("2")
        source.move_ahead(next_source)
        self.assertRank(["1", "4", "2", "3", "5", "6", "7"])

    def test_move_ahead18(self):
        """
        before: 1 2 3 4 5 6 7
               ^------+
        after : 4 1 2 3 5 6 7
        """
        self.create_test_sources(7)
        source = self.by_content("4")
        next_source = self.by_content("1")
        source.move_ahead(next_source)
        self.assertRank(["4", "1", "2", "3", "5", "6", "7"])

    # def test_move_speed(self):
    #     """
    #     before: 1 2 3 4 5 6 7
    #            ^------+
    #     after : 4 1 2 3 5 6 7
    #     """
    #     self.create_test_sources(10000)
    #     import time
    #     start_time = time.time()
    #     source = self.by_content('8000')
    #     next_source = self.by_content('2000')
    #     source.move_ahead(next_source)
    #     end_time = time.time()
    #     print((end_time-start_time)*1000, 'ms')

    def test_create_source_rank(self):
        """测试创建Source时Rank是否正确"""
        t1 = Team.create("t1")
        p1 = Project.create("p1", t1)
        file = File(
            name="1", save_name="1", sort_name="1", project=p1, type=FileType.TEXT,
        ).save()
        s1 = file.create_source("1")
        self.assertEqual(s1.rank, 0)
        s2 = file.create_source("2")
        self.assertEqual(s2.rank, 1)
        s3 = file.create_source("3")
        self.assertEqual(s3.rank, 2)
        s4 = file.create_source("4", rank=100)
        self.assertEqual(s4.rank, 100)
        s5 = file.create_source("5", rank=100)
        self.assertEqual(s5.rank, 100)
