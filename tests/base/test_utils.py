from app.utils.str import to_underscore
from app.utils.labelplus import load_from_labelplus
from tests import MoeTestCase


class TestUtilsCase(MoeTestCase):
    def test_to_underscore(self):
        self.assertEqual("a_b_c", to_underscore("ABC"))
        self.assertEqual("a_b_c", to_underscore("aBC"))
        self.assertEqual("project_great_set", to_underscore("ProjectGreatSet"))
        self.assertEqual("project_great_set", to_underscore("projectGreatSet"))

    def test_load_from_labelplus(self):
        self.assertEqual(
            load_from_labelplus(
                """1,0
-
框内
框外
-
由MoeTra.com导出
>>>>>>>>[1.jpg]<<<<<<<<
----------------[1]----------------[0.509,0.270,2]
第一行

第三行
----------------[2]----------------[0.725,0.271,2]
第一行


----------------[3]----------------[0.725,0.271,2]

第二行

----------------[4]----------------[0.351,0.225,2]


第三行
----------------[5]----------------[0.107,0.238,2]

----------------[6]----------------[0.000,0.184,1]

>>>>>>>>[2.jpg]<<<<<<<<
----------------[1]----------------[0.144,0.181,1]



----------------[2]----------------[0.511,0.238,2]


----------------[3]----------------[0.858,0.265,1]

----------------[4]----------------[0.472,0.482,2]
>>>>>>>>[3.png]<<<<<<<<
>>>>>>>>[4.jpeg]<<<<<<<<



----------------[1]----------------[0.441,0.223,1]
   
"""  # noqa
            ),
            [
                {
                    "file_name": "1.jpg",
                    "labels": [
                        {
                            "x": 0.509,
                            "y": 0.27,
                            "position_type": 2,
                            "translation": "第一行\n\n第三行",
                        },
                        {
                            "x": 0.725,
                            "y": 0.271,
                            "position_type": 2,
                            "translation": "第一行\n\n",
                        },
                        {
                            "x": 0.725,
                            "y": 0.271,
                            "position_type": 2,
                            "translation": "\n第二行\n",
                        },
                        {
                            "x": 0.351,
                            "y": 0.225,
                            "position_type": 2,
                            "translation": "\n\n第三行",
                        },
                        {
                            "x": 0.107,
                            "y": 0.238,
                            "position_type": 2,
                            "translation": "",
                        },
                        {
                            "x": 0.0,
                            "y": 0.184,
                            "position_type": 1,
                            "translation": "",
                        },
                    ],
                },
                {
                    "file_name": "2.jpg",
                    "labels": [
                        {
                            "x": 0.144,
                            "y": 0.181,
                            "position_type": 1,
                            "translation": "\n\n",
                        },
                        {
                            "x": 0.511,
                            "y": 0.238,
                            "position_type": 2,
                            "translation": "\n",
                        },
                        {
                            "x": 0.858,
                            "y": 0.265,
                            "position_type": 1,
                            "translation": "",
                        },
                        {
                            "x": 0.472,
                            "y": 0.482,
                            "position_type": 2,
                            "translation": "",
                        },
                    ],
                },
                {"file_name": "3.png", "labels": []},
                {
                    "file_name": "4.jpeg",
                    "labels": [
                        {
                            "x": 0.441,
                            "y": 0.223,
                            "position_type": 1,
                            "translation": "   ",
                        }
                    ],
                },
            ],
        )
