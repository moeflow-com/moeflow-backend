import datetime
import re
from time import sleep

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    IntField,
    ListField,
    ReferenceField,
    StringField,
)

from app.models.file import Filename
from tests import MoeTestCase


class Thing(Document):
    name = StringField()
    time = DateTimeField(default=datetime.datetime.utcnow)


class ThingWrong(Document):
    """错误的"""

    name = StringField()
    time = DateTimeField(default=datetime.datetime.utcnow())


class Sort(Document):
    """用于测试排序，以及sort_name的生成效果"""

    rank = IntField()
    sort_name = StringField()


class ListT(Document):
    content = ListField()


class ThingNone(Document):
    name = StringField()
    thing = ReferenceField("Thing")


class ThingRefUseID(Document):
    name = StringField()
    thing = ReferenceField("Thing")


class ThingBool(Document):
    right = BooleanField(default=False)
    wrong = BooleanField(default=True)


class MongoengineTestCase(MoeTestCase):
    def test_default_time(self):
        """
        测试默认时间，默认是创建时的时间，不会随着save变化，不会随着调用变化
        """
        t = Thing(name="1").save()
        t.reload()  # 获取现在储存的时间
        time1 = t.time
        self.assertEqual(t.name, "1")
        sleep(0.2)
        # 修改一个名字，时间没有变
        t.name = "2"
        t.save()
        t.reload()  # 获取现在储存的时间
        time2 = t.time
        self.assertEqual(time1, time2)
        self.assertEqual(t.name, "2")
        sleep(0.2)
        # 重新查找这个对象，时间没有变
        t = Thing.objects.first()  # 获取现在储存的时间
        time3 = t.time
        self.assertEqual(time2, time3)
        sleep(0.2)
        # 再次调用值，时间没有变
        self.assertEqual(time3, t.time)

    def test_default_time2(self):
        """
        当使用utcnow()引用的时候，都是启动程序的时间
        """
        t1 = ThingWrong(name="1").save()
        sleep(0.2)
        t2 = ThingWrong(name="2").save()
        t1.reload()
        t2.reload()
        self.assertEqual(t1.time, t2.time)

    def test_name_sort(self):
        """测试字符串的排序顺序 None第一个，''第二个，然后是数字、字母顺序"""
        Sort(rank=2, sort_name=Filename("123.jpg").sort_name).save()
        Sort(rank=0, sort_name=None).save()
        Sort(rank=4, sort_name=Filename("a00.jpg").sort_name).save()
        Sort(rank=3, sort_name=Filename("a.jpg").sort_name).save()
        Sort(rank=1, sort_name="").save()
        Sort(rank=7, sort_name=Filename("a0-10.jpg").sort_name).save()
        Sort(rank=6, sort_name=Filename("a0-2.jpg").sort_name).save()
        Sort(rank=8, sort_name=Filename("a0-011.jpg").sort_name).save()
        Sort(rank=11, sort_name=Filename("a1-12.jpg").sort_name).save()
        Sort(rank=5, sort_name=Filename("a0-1.jpg").sort_name).save()
        Sort(rank=9, sort_name=Filename("a01.jpg").sort_name).save()
        Sort(rank=10, sort_name=Filename("a01-001.jpg").sort_name).save()
        Sort(rank=12, sort_name=Filename("a1-100.jpg").sort_name).save()
        Sort(rank=14, sort_name=Filename("a003.j").sort_name).save()
        Sort(rank=15, sort_name=Filename("a4.jpg").sort_name).save()
        Sort(rank=17, sort_name=Filename("a11.jpg").sort_name).save()
        Sort(rank=13, sort_name=Filename("a2.j").sort_name).save()
        Sort(rank=16, sort_name=Filename("a10.jpg").sort_name).save()
        Sort(rank=19, sort_name=Filename("b1.jpeg").sort_name).save()
        Sort(rank=18, sort_name=Filename("b.jpeg").sort_name).save()
        sorts = Sort.objects.order_by("sort_name")
        for i in range(Sort.objects.count()):
            self.assertEqual(i, sorts[i].rank)

    def test_list(self):
        """测试存入的list和去除的是否一致"""
        content = [2, 3, 4, 66, 1, 0]
        ListT(content=content).save()
        list_t = ListT.objects.first()
        self.assertEqual(content, list_t.content)

        content2 = [1, 2, 3]
        list_t.content = content2
        list_t.save()
        list_t.reload()
        self.assertEqual(content2, list_t.content)

        content3 = ["12312", 3, 2, 321, 1]
        list_t.update(content=content3)
        list_t.reload()
        self.assertEqual(content3, list_t.content)

    def test_iexact(self):
        """测试iexact中的使用类似正则表达式的文本不会影响查询，iexact仅仅是正则表达式的快捷方式"""
        Thing(name="Hello moetra").save()
        Thing(name="Hello world").save()
        # 部分不匹配
        self.assertEqual(0, Thing.objects(name__iexact="Hello").count())
        self.assertEqual(0, Thing.objects(name__iexact="Hello moetr").count())
        self.assertEqual(0, Thing.objects(name__iexact="hello").count())
        self.assertEqual(0, Thing.objects(name__iexact="moetra").count())
        # 完全匹配
        self.assertEqual(1, Thing.objects(name__iexact="Hello moetra").count())
        self.assertEqual(1, Thing.objects(name__iexact="Hello world").count())
        # 大小写不同，也可以
        self.assertEqual(1, Thing.objects(name__iexact="hello Moetra").count())
        self.assertEqual(1, Thing.objects(name__iexact="hello World").count())
        # 使用正则表达式，也可以
        regex = re.compile(".*")
        self.assertEqual(2, Thing.objects(name=regex).count())
        # 类正则表达式不影响
        self.assertEqual(0, Thing.objects(name__iexact=".*").count())
        self.assertEqual(0, Thing.objects(name__iexact="{.*}").count())
        self.assertEqual(0, Thing.objects(name__iexact="[.*]").count())
        self.assertEqual(0, Thing.objects(name__iexact="/.*/").count())
        self.assertEqual(0, Thing.objects(name__iexact="/.*/").count())
        self.assertEqual(0, Thing.objects(name__iexact="\\.*\\").count())
        self.assertEqual(0, Thing.objects(name__iexact=r"\.*\\").count())

    def test_save(self):
        """save返回的是创建的对象"""
        thing = Thing(name="1").save()
        thing_found = Thing.objects(name="1").first()
        self.assertEqual(thing, thing_found)

    def test_ref_none(self):
        """测试关联对象设置为None的表现"""
        thing = Thing(name="1").save()
        # 有
        none1 = ThingNone(name="none1", thing=thing).save()
        # {
        #     "_id" : ObjectId("5bfce445ff036b1b86e13565"),
        #     "name" : "none1",
        #     "thing" : ObjectId("5bfce445ff036b1b86e13564")
        # }

        # None
        none2 = ThingNone(name="none2", thing=None).save()
        # {
        #     "_id" : ObjectId("5bfce445ff036b1b86e13566"),
        #     "name" : "none2"
        # }

        # 没有
        none3 = ThingNone(name="none3").save()
        # {
        #     "_id" : ObjectId("5bfce445ff036b1b86e13567"),
        #     "name" : "none3"
        # }

        # 先有后None
        none4 = ThingNone(name="none4", thing=thing).save()
        none4.thing = None
        none4.save()
        # {
        #     "_id" : ObjectId("5bfce445ff036b1b86e13568"),
        #     "name" : "none4"
        # }

        # 测试通过对象获取
        self.assertTrue(isinstance(none1.thing, Thing))
        self.assertIsNone(none2.thing)
        self.assertIsNone(none3.thing)
        self.assertIsNone(none4.thing)

    def test_ref_search(self):
        """测试关联对象搜索"""
        thing = Thing(name="1").save()
        ThingNone(name="none1", thing=thing).save()
        ThingNone(name="none2").save()

        # 通过对象搜索
        nones = ThingNone.objects(thing=thing)
        self.assertEqual(1, nones.count())
        self.assertEqual("none1", nones.first().name)
        # 通过id搜索
        nones = ThingNone.objects(thing=thing.id)
        self.assertEqual(1, nones.count())
        self.assertEqual("none1", nones.first().name)
        # 通过None搜索
        nones = ThingNone.objects(thing=None)
        self.assertEqual(1, nones.count())
        self.assertEqual("none2", nones.first().name)
        # 不限制条件
        nones = ThingNone.objects()
        self.assertEqual(2, nones.count())
        # 通过filter限制
        nones = ThingNone.objects()
        self.assertEqual(1, nones.filter(thing=thing).count())
        self.assertEqual("none1", nones.filter(thing=thing).first().name)
        self.assertEqual(1, nones.filter(thing=None).count())
        self.assertEqual("none2", nones.filter(thing=None).first().name)

    def test_create_ref_with_id(self):
        """测试创建对象ref字段提供id"""
        thing = Thing(name="1").save()
        ThingRefUseID(name="none1", thing=thing.id).save()
        ThingRefUseID(name="none2", thing=str(thing.id)).save()

    def test_set_none(self):
        """测试将字段设为None是否能删除字段"""
        thing1 = Thing(name="1").save()
        thing2 = Thing().save()
        self.assertEqual("1", thing1.name)
        self.assertEqual(None, thing2.name)
        self.assertTrue(thing1.name)
        self.assertFalse(thing2.name)
        # 将thing1的name设置成None
        thing1.name = None
        thing1.save()
        self.assertEqual(thing1.name, thing2.name)
        self.assertEqual(None, thing1.name)
        self.assertEqual(None, thing2.name)
        self.assertFalse(thing1.name)
        self.assertFalse(thing2.name)

    def test_query_bool_exist(self):
        """BooleanField当使用default时，应该自动赋值存入数据库，并能搜索到"""
        t1 = ThingBool(right=True, wrong=False).save()
        t2 = ThingBool(right=False, wrong=True).save()
        t3 = ThingBool().save()
        # right default=False
        self.assertEqual(True, t1.right)
        self.assertEqual(False, t2.right)
        self.assertEqual(False, t3.right)
        self.assertEqual(1, ThingBool.objects(right=True).count())
        self.assertEqual(2, ThingBool.objects(right=False).count())
        self.assertEqual(1, ThingBool.objects(right__ne=False).count())
        self.assertEqual(2, ThingBool.objects(right__ne=True).count())
        # wrong default=True
        self.assertEqual(False, t1.wrong)
        self.assertEqual(True, t2.wrong)
        self.assertEqual(True, t3.wrong)
        self.assertEqual(1, ThingBool.objects(wrong=False).count())
        self.assertEqual(2, ThingBool.objects(wrong__ne=False).count())
        self.assertEqual(1, ThingBool.objects(wrong__ne=True).count())

    def test_order_skip_limit(self):
        """测试排序和切片的顺序是否会影响结果"""
        Sort(rank=1).save()
        Sort(rank=2).save()
        Sort(rank=3).save()
        Sort(rank=4).save()
        Sort(rank=5).save()
        # 不排序，从第3个开始取2个，为3，4
        self.assertEqual(
            [3, 4], [item.rank for item in Sort.objects.skip(2).limit(2)]
        )
        # 先倒序，从第3个开始取2个，为3，2
        self.assertEqual(
            [3, 2],
            [
                item.rank
                for item in Sort.objects.order_by("-rank").skip(2).limit(2)
            ],
        )
        # 先从第3个取2个，再倒序
        # 因为排序永远在第一优先级，所以和上面结果一样为3，2，而不是4，3
        self.assertEqual(
            [3, 2],
            [
                item.rank
                for item in Sort.objects.skip(2).limit(2).order_by("-rank")
            ],
        )

    def test_order_false_first(self):
        """测试布尔值排序正序False在前"""
        ThingBool(right=True).save()
        ThingBool(right=False).save()
        ThingBool(right=False).save()
        ThingBool(right=True).save()
        self.assertEqual(
            [False, False, True, True],
            [item.right for item in ThingBool.objects.order_by("right")],
        )
        self.assertEqual(
            [True, True, False, False],
            [item.right for item in ThingBool.objects.order_by("-right")],
        )
