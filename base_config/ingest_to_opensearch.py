import numpy as np
from opensearchpy import OpenSearch, helpers
from opensearchpy.helpers import bulk
from sentence_transformers import SentenceTransformer
import json
import os
import time
import threading
import torch
from opensearch_client import get_opensearch_client

# 当前文件路径
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# 项目的根路径
BASE_DIR = os.path.dirname(current_script_dir)
# 数据的路径
DATA_DIR = os.path.join(BASE_DIR, "knowledge_base", "small_data")

# 数据文件名
BUSINESS_FILE = os.path.join(DATA_DIR, "small_business.json")
REVIEW_FILE = os.path.join(DATA_DIR, "small_review.json")
CHECKIN_FILE = os.path.join(DATA_DIR, "small_checkin.json")
TIP_FILE = os.path.join(DATA_DIR, "small_tip.json")
USER_FILE = os.path.join(DATA_DIR, "small_user.json")

# 索引名称
BUSINESS_INDEX = "yelp_business"
REVIEW_INDEX = "yelp_review"
CHECKIN_INDEX = "yelp_checkin"
TIP_INDEX = "yelp_tip"
USER_INDEX = "yelp_user"

# 向量维度 (bge-base-zh-v1.5 模型)
VECTOR_DIM = 768

# OpenSearch 批量写入大小
BULK_SIZE = 500

# 编码批量大小：GPU 建议 64-128，CPU 建议 8-16
ENCODING_BATCH_SIZE = 16


class ModelSingleton:
    """线程安全的 SentenceTransformer 单例 — 自动检测 GPU 加速"""

    _model = None
    _lock = threading.Lock()
    _model_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "models", "bge-base-zh-v1.5"
    )

    @classmethod
    def _detect_device(cls) -> str:
        """自动检测最佳设备"""
        if torch.cuda.is_available():
            device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_mem / (1024**3)
            print(f"🚀 GPU 已检测到: {gpu_name} ({vram:.1f} GB)")
        else:
            device = "cpu"
            print("💻 未检测到 GPU，使用 CPU 推理")
        return device

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    device = cls._detect_device()
                    print(f"⏳ 加载模型 {cls._model_path} 到 {device} ...")
                    cls._model = SentenceTransformer(
                        cls._model_path,
                        device=device,
                    )
                    cls._model.max_seq_length = 512
                    print(f"✅ 模型加载完成")
        return cls._model


def traverse_json(data, prefix="", result=""):
    """递归遍历JSON数据，将所有字段内容拼接到字符串中"""
    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            result = traverse_json(value, new_prefix, result)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            new_prefix = f"{prefix}[{idx}]"
            result = traverse_json(item, new_prefix, result)
    else:
        result += f"{prefix}: {data}\n"
    return result


def convert_vector_to_list(vector):
    """将numpy数组转换为Python列表（OpenSearch需要）"""
    if isinstance(vector, np.ndarray):
        return vector.tolist()
    return vector


def create_knn_index(client, index_name):
    if client.indices.exists(index=index_name):
        print(f"✅ 索引已存在: {index_name}")
        return

    mapping = {
        "settings": {
            "index": {
                "knn": True
            }
        },
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "knn_vector",
                    "dimension": VECTOR_DIM,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil"
                    }
                },
                "text_for_embedding": {
                    "type": "text"
                }
            }
        }
    }

    client.indices.create(index=index_name, body=mapping)
    print(f"✅ 创建 KNN 索引: {index_name}")


def bulk_import(client, file_path, index_name):
    """批量导入数据（优化版：批量编码 + GPU 自动检测）"""
    print(f"\n📥 导入数据到 {index_name}")
    create_knn_index(client, index_name)

    model = ModelSingleton.get_model()

    # ═══════════════════════════════════════════════════════════
    # 第一步：读取文件，解析 JSON，准备待编码文本
    # ═══════════════════════════════════════════════════════════
    print(f"   📖 读取数据文件...")
    documents = []  # [(doc_dict, text_for_embedding, doc_id), ...]

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                doc = json.loads(line.strip())
                text = traverse_json(doc)

                # 确定文档 ID
                if index_name == REVIEW_INDEX:
                    doc_id = doc.get("review_id")
                elif index_name == CHECKIN_INDEX:
                    doc_id = doc.get("business_id")
                elif index_name == TIP_INDEX:
                    doc_id = doc.get("user_id")
                elif index_name == USER_INDEX:
                    doc_id = doc.get("user_id")
                else:  # BUSINESS_INDEX
                    doc_id = doc.get("business_id")

                documents.append((doc, text, doc_id))

            except json.JSONDecodeError as e:
                print(f"   ⚠️第{line_num}行 JSON 解析错误: {e}")
            except Exception as e:
                print(f"   ⚠️处理第{line_num}行时出错: {e}")

    total_count = len(documents)
    if total_count == 0:
        print(f"   ❌ 没有有效数据，跳过 {index_name}")
        return
    print(f"   ✅ 读取完成，共 {total_count} 条文档")

    # ═══════════════════════════════════════════════════════════
    # 第二步：批量编码（关键优化！）
    # ═══════════════════════════════════════════════════════════
    print(f"   🔢 开始批量编码 (encoding_batch={ENCODING_BATCH_SIZE})...")
    encode_start = time.time()

    all_embeddings = []
    for i in range(0, total_count, ENCODING_BATCH_SIZE):
        chunk = documents[i : i + ENCODING_BATCH_SIZE]
        texts = [text for _, text, _ in chunk]

        embeddings = model.encode(
            texts,
            batch_size=ENCODING_BATCH_SIZE,
            convert_to_numpy=True,
            normalize_embeddings=True,   # 余弦相似度需要归一化
            show_progress_bar=True,
        )
        all_embeddings.extend(embeddings)

    encode_elapsed = time.time() - encode_start
    encode_rate = total_count / encode_elapsed if encode_elapsed > 0 else 0
    print(f"   ✅ 编码完成，耗时 {encode_elapsed:.1f}秒 "
          f"({encode_rate:.0f}条/秒)")

    # ═══════════════════════════════════════════════════════════
    # 第三步：组装文档，批量写入 OpenSearch
    # ═══════════════════════════════════════════════════════════
    print(f"   💾 写入 OpenSearch...")
    write_start = time.time()
    success_count = 0
    error_count = 0
    batch_actions = []

    for (doc, text, doc_id), embedding in zip(documents, all_embeddings):
        doc["embedding"] = convert_vector_to_list(embedding)
        doc["text_for_embedding"] = text

        action = {
            "_index": index_name,
            "_id": doc_id,
            "_source": doc,
        }
        batch_actions.append(action)

        # 积累到 BULK_SIZE 条后提交
        if len(batch_actions) >= BULK_SIZE:
            success, errors = bulk(
                client,
                batch_actions,
                chunk_size=BULK_SIZE,
                raise_on_error=False,
            )
            success_count += success
            if errors:
                error_count += len(errors)

            elapsed = time.time() - write_start
            rate = success_count / elapsed if elapsed > 0 else 0
            print(f"   已写入: {success_count}/{total_count} | "
                  f"失败: {error_count} | 速率: {rate:.0f}条/秒")

            batch_actions = []

    # 处理剩余的
    if batch_actions:
        success, errors = bulk(
            client,
            batch_actions,
            raise_on_error=False,
        )
        success_count += success
        if errors:
            error_count += len(errors)

    write_elapsed = time.time() - write_start

    # ═══════════════════════════════════════════════════════════
    # 汇总
    # ═══════════════════════════════════════════════════════════
    total_elapsed = time.time() - encode_start
    print(f"\n✅ {index_name} 导入完成!")
    print(f"   总文档数: {total_count}条")
    print(f"   成功写入: {success_count}条")
    print(f"   写入失败: {error_count}条")
    print(f"   编码耗时: {encode_elapsed:.1f}秒 ({encode_rate:.0f}条/秒)")
    print(f"   写入耗时: {write_elapsed:.1f}秒")
    print(f"   总耗时:   {total_elapsed:.1f}秒")
    print(f"   整体速率: {success_count / total_elapsed:.0f}条/秒")


def verify_data(client):
    """验证导入的数据"""
    print("\n🔍 验证导入结果...")

    for index_name in [BUSINESS_INDEX, REVIEW_INDEX, CHECKIN_INDEX, TIP_INDEX, USER_INDEX]:
        if client.indices.exists(index=index_name):
            count = client.count(index=index_name)["count"]
            print(f"   {index_name}: {count}条记录")

    print("\n   随机查询商家示例:")
    res = client.search(
        index=BUSINESS_INDEX,
        body={
            "size": 3,
            "query": {"match_all": {}}
        },
    )

    for hit in res["hits"]["hits"]:
        source = hit["_source"]
        name = source.get("name", "N/A")
        city = source.get("city", "N/A")
        stars = source.get("stars", "N/A")
        print(f"   - {name} ({city}) ★{stars}")


def main():
    print("=" * 60)
    print("Yelp数据导入OpenSearch工具 (GPU加速版)")
    print("=" * 60)

    client = get_opensearch_client()
    if not client:
        print("❌ 无法连接到OpenSearch，请检查服务是否启动")
        return

    # 检查数据文件
    data_files = {
        BUSINESS_FILE: "商家",
        REVIEW_FILE: "评论",
        CHECKIN_FILE: "签到",
        TIP_FILE: "Tip",
        USER_FILE: "用户",
    }
    for file_path, name in data_files.items():
        if not os.path.exists(file_path):
            print(f"❌ 找不到{name}数据文件: {file_path}")
            print("   请先运行 prepare_data.py")
            return
    print(f"\n✅ 数据文件检查通过")

    # 逐个导入
    file_index_map = [
        (BUSINESS_FILE, BUSINESS_INDEX),
        (REVIEW_FILE, REVIEW_INDEX),
        (CHECKIN_FILE, CHECKIN_INDEX),
        (TIP_FILE, TIP_INDEX),
        (USER_FILE, USER_INDEX),
    ]

    for file_path, index_name in file_index_map:
        bulk_import(client=client, file_path=file_path, index_name=index_name)

    verify_data(client)

    print("\n" + "=" * 60)
    print("🎉🎉🎉 数据导入完成!")
    print("=" * 60)
    print("\n下一步建议:")
    print("1. 打开浏览器访问 http://localhost:5601 (Kibana)")
    print("2. 在Dev Tools中执行: GET yelp_business/_search")


if __name__ == "__main__":
    main()
