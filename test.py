from idlelib.outwin import file_line_pats

import numpy as np
from opensearchpy import OpenSearch, helpers
from opensearchpy.helpers import bulk
from sentence_transformers import SentenceTransformer
import json
import os
import time
import threading


def traverse_json(data,prefix="", result=""):
    """
    递归遍历JSON数据，将所有字段内容拼接到字符串中

    Args:
        data: JSON数据（dict, list, str, int, float, bool, None）
        result_str: 累积的结果字符串

    Returns:
        str: 拼接后的字符串
    """
    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            result = traverse_json(value, new_prefix, result)

    elif isinstance(data, list):
        for idx, item in enumerate(data):
            new_prefix = f"{prefix}[{idx}]"
            result = traverse_json(item, new_prefix, result)

    else:
        # 基本类型：拼接 key: value
        result += f"{prefix}: {data}\n"

    return result
documents: list[tuple[dict, str| None]] = []  # (doc, text, doc_id)
file_path="knowledge_base/small_data/beijing.json"
with open(file_path, "r", encoding="utf-8") as f:
    items = json.load(f)
    print(type(items))
    for item in items:
        print(type(item))
        text = traverse_json(item)
        documents.append((item, text))
        print(type(text))
        print(text)