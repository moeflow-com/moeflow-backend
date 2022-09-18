import re


def to_underscore(data: str) -> str:
    """将ProjectGreatSet转换成project_great_set的形式"""
    pattern = re.compile(r"[A-Z]")
    # 在所有大写字母前增加下划线
    data = re.sub(pattern, lambda res: f"_{res.group()}", data)
    # 尝试去掉第一个下划线
    if data.startswith("_"):
        data = data[1:]
    # 全部小写
    data = data.lower()
    return data
