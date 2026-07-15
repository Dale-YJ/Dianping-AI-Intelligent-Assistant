import ast
import json
import os
import time

import numpy as np
from opensearchpy import OpenSearch, helpers
from opensearchpy.helpers import bulk
from sentence_transformers import SentenceTransformer

from opensearch_client import get_opensearch_client
import threading



# 当前文件路径
current_script_dir = os.path.dirname(os.path.abspath(__file__))
#项目的根路径
BASE_DIR = os.path.dirname(current_script_dir)
#数据的路径
DATA_DIR = os.path.join(BASE_DIR, "knowledge_base", "small_data")

#数据文件名
BUSINESS_FILE = os.path.join(DATA_DIR, "small_business.json")
REVIEW_FILE = os.path.join(DATA_DIR, "small_review.json")
CHECKIN_FILE = os.path.join(DATA_DIR, "small_checkin.json")
TIP_FILE = os.path.join(DATA_DIR, "small_tip.json")
USER_FILE = os.path.join(DATA_DIR, "small_user.json")

# 索引名称
BUSINESS_INDEX = "yelp_business"
REVIEW_INDEX = "yelp_review"
CHECKIN_INDEX="yelp_checkin"
TIP_INDEX="yelp_tip"
USER_INDEX="yelp_user"

# 向量维度 (all-MiniLM-L6-v2模型)
VECTOR_DIM = 384

# 批量处理大小（小批次避免 OpenSearch 压力过大）
BATCH_SIZE = 500



class ModelSingleton:
    """线程安全的 SentenceTransformer 单例"""

    _model = None
    _lock = threading.Lock()
    _model_path = '../models/all-MiniLM-L6-v2'

    @classmethod
    def get_model(cls):
        # 第一次检查（无锁，提升性能）
        if cls._model is None:
            with cls._lock:
                # 第二次检查（防止多线程同时通过第一次检查）
                if cls._model is None:
                    cls._model = SentenceTransformer(cls._model_path)
        return cls._model



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

def convert_vector_to_list(vector):
    """
    将numpy数组转换为Python列表（OpenSearch需要）
    """
    if isinstance(vector, np.ndarray):
        return vector.tolist()
    return vector


def _clean_doc(doc):
    """修正 Yelp 原始数据类型问题"""
    # is_open: 0/1 → True/False
    if "is_open" in doc and isinstance(doc["is_open"], int):
        doc["is_open"] = bool(doc["is_open"])

    # attributes: "True"/"False" → 布尔值, "{...}" → dict
    if "attributes" in doc and isinstance(doc["attributes"], dict):
        for k, v in doc["attributes"].items():
            if isinstance(v, str):
                if v in ("True", "False"):
                    doc["attributes"][k] = (v == "True")
                elif v.startswith("{") and v.endswith("}"):
                    try:
                        doc["attributes"][k] = ast.literal_eval(v)
                    except (ValueError, SyntaxError):
                        pass

    # hours: 值统一为字符串
    if "hours" in doc and isinstance(doc["hours"], dict):
        for k, v in doc["hours"].items():
            if not isinstance(v, str):
                doc["hours"][k] = str(v)


def bulk_import(client, file_path, index_name):
    """批量导入数据"""
    print(f"\n 导入数据到 {index_name}")


    model = ModelSingleton.get_model()
    total_count = 0
    success_count = 0
    error_count = 0
    batch_actions = []
    start_time = time.time()

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                doc = json.loads(line.strip())
                _clean_doc(doc)

                text_for_embedding = traverse_json(doc)
                embedding = model.encode(text_for_embedding, convert_to_numpy=True)
                doc["embedding"] = convert_vector_to_list(embedding)
                doc["text_for_embedding"] = text_for_embedding

                doc_id = doc.get("business_id")
                action = {
                    "_index": index_name,
                    "_id": doc.get("yelp_business"),
                    "_source": doc
                }
                batch_actions.append(action)
                total_count += 1

                if total_count % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = total_count / elapsed if elapsed > 0 else 0
                    print(f"   已生成 embedding: {total_count} 条 | 速率: {rate:.1f} 条/秒")

                if len(batch_actions) >= BATCH_SIZE:
                    ok, err = _send_batch(client, batch_actions, total_count)
                    success_count += ok
                    error_count += err
                    batch_actions = []

            except json.JSONDecodeError as e:
                print(f"   第{line_num}行 JSON 解析错误: {e}")
                error_count += 1
            except Exception as e:
                print(f"   第{line_num}行处理出错: {e}")
                error_count += 1

        if batch_actions:
            ok, err = _send_batch(client, batch_actions, total_count)
            success_count += ok
            error_count += err

    elapsed = time.time() - start_time
    print(f"\n[OK] {index_name} 导入完成!")
    print(f"   总处理: {total_count}条 | 成功: {success_count} | 失败: {error_count}")
    print(f"   耗时: {elapsed:.1f}秒", end="")
    if elapsed > 0:
        print(f" | 平均: {total_count / elapsed:.1f}条/秒")
    else:
        print()


def _send_batch(client, batch, total_count):
    """发送一批数据到 OpenSearch，返回 (成功数, 失败数)"""
    n = len(batch)
    print(f"   >>> 发送 {total_count - n + 1}~{total_count} 条 ...", end="", flush=True)
    t0 = time.time()
    try:
        result = bulk(
            client, batch,
            chunk_size=BATCH_SIZE,
            request_timeout=REQUEST_TIMEOUT,
            raise_on_error=False,
        )
        ok_cnt = result[0]
        err_cnt = len(result[1]) if result[1] else 0
        print(f" 完成 ({time.time() - t0:.1f}s) 成功: {ok_cnt}, 失败: {err_cnt}")
        return ok_cnt, err_cnt
    except Exception as e:
        print(f" 失败 ({time.time() - t0:.1f}s)\n   [ERROR] {e}")
        return 0, n


def verify_data(client):
    """验证导入的数据"""
    print("\n🔍 验证导入结果...")

    # 检查索引是否存在
    for index_name in [BUSINESS_INDEX, REVIEW_INDEX]:
        if client.indices.exists(index=index_name):
            count = client.count(index=index_name)['count']
            print(f"   {index_name}: {count}条记录")

    # 随机查询几条数据
    print("\n   随机查询商家示例:")
    res = client.search(
        index=BUSINESS_INDEX,
        body={
            "size": 3,
            "query": {"match_all": {}}
        }
    )

    for hit in res["hits"]["hits"]:
        source = hit["_source"]
        name = source.get("name", "N/A")
        city = source.get("city", "N/A")
        stars = source.get("stars", "N/A")
        print(f"   - {name} ({city}) ★{stars}")

def main():
    print("=" * 60)
    print("Yelp数据导入OpenSearch工具")
    print("=" * 60)

    # 连接OpenSearch
    client = get_opensearch_client()
    if not client:
        print("❌ 无法连接到OpenSearch，请检查服务是否启动")
        return


    # 检查数据文件
    if not os.path.exists(BUSINESS_FILE):
        print(f"❌ 找不到商家数据文件: {BUSINESS_FILE}")
        print("   请先运行 prepare_data.py")
        return
    if not os.path.exists(REVIEW_FILE):
        print(f"❌ 找不到评论数据文件: {REVIEW_FILE}")
        print("   请先运行 prepare_data.py")
        return
    if not os.path.exists(CHECKIN_FILE):
        print(f"❌ 找不到登录数据文件: {CHECKIN_FILE}")
        print("   请先运行 prepare_data.py")
        return
    if not os.path.exists(TIP_FILE):
        print(f"❌ 找不到tip数据文件: {TIP_FILE}")
        print("   请先运行 prepare_data.py")
        return
    if not os.path.exists(USER_FILE):
        print(f"❌ 找不到user数据文件: {USER_FILE}")
        print("   请先运行 prepare_data.py")
        return

    print(f"\n数据文件检查通过:")

    # 导入商家数据
    bulk_import(
        client=client,
        file_path=BUSINESS_FILE,
        index_name=BUSINESS_INDEX,
    )
    # 导入评论数据
    bulk_import(
        client=client,
        file_path=REVIEW_FILE,
        index_name=REVIEW_INDEX,
    )
    bulk_import(
        client=client,
        file_path=CHECKIN_FILE,
        index_name=CHECKIN_INDEX,
    )
    bulk_import(
        client=client,
        file_path=TIP_FILE,
        index_name=TIP_INDEX,
    )
    bulk_import(
        client=client,
        file_path=USER_FILE,
        index_name=USER_INDEX,
    )


    # 验证数据
    verify_data(client)
    print("\n" + "=" * 60)
    print("🎉🎉🎉 数据导入完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()