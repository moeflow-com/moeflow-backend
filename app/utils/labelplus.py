import re
from typing import List, TypedDict


class LPLabel(TypedDict):
    x: float
    y: float
    position_type: int
    translation: str


class LPFile(TypedDict):
    file_name: str
    labels: List[LPLabel]


def load_from_labelplus(labelplus: str) -> List[LPFile]:
    files: List[LPFile] = []
    lines = labelplus.splitlines()
    file_index = -1
    label_index = -1
    for line in lines:
        # 检测文件行
        file_match = re.match(r".+>>>\[(.+)\]<<<.+", line)
        if file_match and file_match.group(1):
            file_name = file_match.group(1)
            files.append({"file_name": file_name, "labels": []})
            file_index += 1
            label_index = -1
            continue
        # 检测标签行
        label_match = re.match(r".+---\[.+\]---.+\[(.+),(.+),(.+)\]", line)
        if label_match and label_match.group(1):
            label_x = label_match.group(1)
            label_y = label_match.group(2)
            position_type = label_match.group(3)
            files[file_index]["labels"].append(
                {
                    "x": float(label_x),
                    "y": float(label_y),
                    "position_type": int(position_type),
                    "translation": "",
                }
            )
            label_index += 1
            continue
        if file_index > -1 and label_index > -1:
            files[file_index]["labels"][label_index]["translation"] += line + "\n"
    for file in files:
        for label in file["labels"]:
            if label["translation"].endswith("\n"):
                label["translation"] = label["translation"][0:-1]
    return files
