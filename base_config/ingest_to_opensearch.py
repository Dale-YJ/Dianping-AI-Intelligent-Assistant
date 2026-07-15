import numpy as np
from opensearchpy import OpenSearch, helpers
from opensearchpy.helpers import bulk
from sentence_transformers import SentenceTransformer
import json
import os
import time
from opensearch_client import get_opensearch_client

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

# 批量处理大小
BATCH_SIZE = 500


# ============================================
#
# def create_indexes(client):
#     """创建索引"""
#     print("\n 创建索引...")
#
#     # 删除已存在的索引
#     for index_name in [BUSINESS_INDEX, REVIEW_INDEX,CHECKIN_INDEX,TIP_INDEX,USER_INDEX]:
#         if client.indices.exists(index=index_name):
#             print(f"   删除旧索引: {index_name}")
#             client.indices.delete(index=index_name)
#
#     # 商家索引
#     business_mapping = {
#         "settings": {
#             "index": {
#                 "knn": True,
#                 "number_of_shards": 1,
#                 "number_of_replicas": 0
#             }
#         },
#         "mappings": {
#             "properties": {
#                 "business_id": {"type": "keyword"},
#                 "name": {"type": "text"},
#                 "address": {"type": "text"},
#                 "city": {"type": "keyword"},
#                 "state": {"type": "keyword"},
#                 "postal_code": {"type": "keyword"},
#                 "location": {"type": "geo_point"},  # 地理坐标点
#                 "stars": {"type": "float"},
#                 "review_count": {"type": "integer"},
#                 "is_open": {"type": "boolean"},
#                 "attributes": {
#                     "properties": {
#                         "RestaurantsTakeOut": {"type": "boolean"},
#                         "BusinessParking": {
#                             "properties": {
#                                 "garage": {"type": "boolean"},
#                                 "street": {"type": "boolean"},
#                                 "validated": {"type": "boolean"},
#                                 "lot": {"type": "boolean"},
#                                 "valet": {"type": "boolean"}
#                             }
#                         }
#                     }
#                 },
#             "categories": {"type": "keyword"},
#             "hours": {
#                 "properties": {
#                     "Monday": {"type": "keyword"},
#                     "Tuesday": {"type": "keyword"},
#                     "Wednesday": {"type": "keyword"},
#                     "Thursday": {"type": "keyword"},
#                     "Friday": {"type": "keyword"},
#                     "Saturday": {"type": "keyword"},
#                     "Sunday": {"type": "keyword"}
#                 }
#             }
#         }
#     },
#     }
#     client.indices.create(index=BUSINESS_INDEX, body=business_mapping)
#     print(f"创建索引: {BUSINESS_INDEX}")
#

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


def bulk_import(client, file_path, index_name):
    """批量导入数据"""
    print(f"\n 导入数据到 {index_name}")

    # 加载模型
    model = SentenceTransformer(os.path.join(BASE_DIR, 'models', 'all-MiniLM-L6-v2'))
    total_count = 0
    success_count = 0
    error_count = 0
    batch_actions = []
    start_time = time.time()

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                #获取每一行的Json数据
                doc = json.loads(line.strip())
                # 创建用于向量化的文本
                text_for_embedding = traverse_json(doc)
                # 生成向量嵌入
                embedding = model.encode(text_for_embedding, convert_to_numpy=True)
                # 将向量添加到文档中
                doc["embedding"] = convert_vector_to_list(embedding)
                doc["text_for_embedding"] = text_for_embedding

                # 7. 构建 action
                action = {
                    "_index": index_name,
                    "_id": doc.get("yelp_business"),  # 确保这个字段存在
                    "_source": doc
                }
                batch_actions.append(action)
                total_count += 1

                # 批量提交
                if len(batch_actions) >= BATCH_SIZE:
                    success, errors = bulk(
                        client,
                        batch_actions,
                        chunk_size=BATCH_SIZE
                    )
                    success_count += success
                    error_count += len(errors) if errors else 0

                    elapsed = time.time() - start_time
                    rate = success_count / elapsed if elapsed > 0 else 0
                    print(
                        f"   已处理: {total_count}条 | 成功: {success_count} | 失败: {error_count} | 速率: {rate:.1f}条/秒")

                    batch_actions = []

            except json.JSONDecodeError as e:
                print(f"   第{line_num}行JSON解析错误: {e}")
                error_count += 1
                continue
            except Exception as e:
                print(f"   处理第{line_num}行时出错: {e}")
                error_count += 1
                continue

        # 处理剩余的数据
        if batch_actions:
            success, errors = bulk(
                client,
                batch_actions,
            )
            success_count += success
            error_count += len(errors) if errors else 0

    elapsed = time.time() - start_time
    print(f"\n[OK] {index_name} 导入完成!")
    print(f"   总处理: {total_count}条")
    print(f"   成功: {success_count}条")
    print(f"   失败: {error_count}条")
    print(f"   耗时: {elapsed:.1f}秒")
    print(f"   平均速度: {success_count / elapsed:.1f}条/秒")


def verify_data(client):
    """验证导入的数据"""
    print("\n[*] 验证导入结果...")

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
        print("[ERROR] 无法连接到OpenSearch，请检查服务是否启动")
        return

    # 检查数据文件
    if not os.path.exists(BUSINESS_FILE):
        print(f"[ERROR] 找不到商家数据文件: {BUSINESS_FILE}")
        print("   请先运行 prepare_data.py")
        return


    print(f"\n数据文件检查通过:")
    print(f"   商家文件: {BUSINESS_FILE}")



    # 导入商家数据
    bulk_import(
        client=client,
        file_path=BUSINESS_FILE,
        index_name=BUSINESS_INDEX,
    )

    # 导入评论数据
    # bulk_import(
    #     client=client,
    #     file_path=REVIEW_FILE,
    #     index_name=REVIEW_INDEX,
    #     vector_field="text_vector",
    #     text_field="text",  # 使用text字段生成向量
    #     is_business=False
    # )

    # 验证数据
    verify_data(client)

    print("\n" + "=" * 60)
    print("=== 数据导入完成! ===")
    print("=" * 60)
    print("\n下一步建议:")
    print("1. 打开浏览器访问 http://localhost:5601 (Kibana)")
    print("2. 在Dev Tools中执行: GET yelp_business/_search")
    print("3. 开始开发你的RAG查询功能!")


if __name__ == "__main__":
    main()