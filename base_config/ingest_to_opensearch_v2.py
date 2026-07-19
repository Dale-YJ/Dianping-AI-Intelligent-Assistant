"""
国内城市数据导入 OpenSearch 工具 (V3 - 统一字段映射版)

将北京/成都/广州/上海的大众点评数据导入到 yelp_business 和 yelp_review 索引，
字段名与 Yelp 数据保持一致，确保现有检索代码无需修改即可查到国内数据。

字段映射:
    餐厅名称   → name
    菜系       → categories
    综合评分   → stars
    人均消费   → price
    评价数量   → review_count
    所属商圈   → neighborhood
    餐厅图片   → image_url
    keyword    → business_id
    评价列表   → 拆分导入 yelp_review

使用方法:
    python ingest_to_opensearch_v2.py
"""

import numpy as np
from opensearchpy import OpenSearch, helpers
from opensearchpy.helpers import bulk
from sentence_transformers import SentenceTransformer
import json
import os
import time
import threading
from opensearch_client import get_opensearch_client
from config import settings

# 当前文件路径
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# 项目的根路径
BASE_DIR = os.path.dirname(current_script_dir)
# 数据的路径
DATA_DIR = os.path.join(BASE_DIR, "knowledge_base", "small_data")

# 数据文件名
CHENGDU_FILE = os.path.join(DATA_DIR, "chengdu.json")
BEIJING_FILE = os.path.join(DATA_DIR, "beijing.json")
GUANGZHOU_FILE = os.path.join(DATA_DIR, "guangzhou.json")
SHANGHAI_FILE = os.path.join(DATA_DIR, "shanghai.json")

# 统一使用 Yelp 索引，让现有检索代码直接可用
BUSINESS_INDEX = "yelp_business"
REVIEW_INDEX = "yelp_review"

# 城市文件名 → 城市中文名映射
CITY_NAME_MAP = {
    "beijing.json": "北京",
    "chengdu.json": "成都",
    "guangzhou.json": "广州",
    "shanghai.json": "上海",
}

# 向量维度 (BAAI/bge-base-zh-v1.5 模型)
VECTOR_DIM = 768

# 批量处理大小
BATCH_SIZE = 500
ENCODING_BATCH_SIZE = 64


# ═══════════════════════════════════════════════════════════════
# 字段映射：国内中文字段 → Yelp 英文字段
# ═══════════════════════════════════════════════════════════════

def normalize_business(doc: dict, city_name: str) -> dict:
    """将国内数据字段映射为 Yelp 兼容的字段名。

    保留原始字段（以 _raw_ 前缀），同时添加映射后的标准字段。
    """
    return {
        # ── 标准字段（映射） ──
        "business_id": doc.get("keyword", ""),
        "name": doc.get("餐厅名称", ""),
        "categories": doc.get("菜系", ""),
        "stars": float(doc.get("综合评分") or 0),
        "review_count": int(doc.get("评价数量") or 0),
        "price": doc.get("人均消费 (元)", ""),
        "image_url": doc.get("餐厅图片", ""),
        # ── 扩展字段 ──
        "city": city_name,
        "neighborhood": doc.get("所属商圈", ""),
        "source": "dianping",
        # ── 保留原始字段（方便调试） ──
        "_raw_餐厅名称": doc.get("餐厅名称", ""),
        "_raw_菜系": doc.get("菜系", ""),
        "_raw_综合评分": doc.get("综合评分", ""),
        "_raw_人均消费": doc.get("人均消费 (元)", ""),
        "_raw_所属商圈": doc.get("所属商圈", ""),
    }


def normalize_review(review: dict, business_id: str, idx: int) -> dict:
    """将国内评价映射为 Yelp review 格式。"""
    return {
        "review_id": f"{business_id}_r{idx}",
        "business_id": business_id,
        "stars": float(review.get("评分", 0)),
        "text": review.get("评价", ""),
        "useful": 0,
        "date": "",
        "user_id": f"{business_id}_u{idx}",
    }


def format_text_for_embedding(doc: dict) -> str:
    """构建用于向量嵌入的文本（只用标准字段）。"""
    parts = []
    if doc.get("name"):
        parts.append(f"餐厅名称: {doc['name']}")
    if doc.get("categories"):
        parts.append(f"菜系: {doc['categories']}")
    if doc.get("neighborhood"):
        parts.append(f"商圈: {doc['neighborhood']}")
    if doc.get("city"):
        parts.append(f"城市: {doc['city']}")
    if doc.get("price"):
        parts.append(f"人均: {doc['price']}元")
    if doc.get("stars"):
        parts.append(f"评分: {doc['stars']}")
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# Model Singleton
# ═══════════════════════════════════════════════════════════════

class ModelSingleton:
    """线程安全的 SentenceTransformer 单例，自动检测 GPU"""

    _model = None
    _lock = threading.Lock()
    _model_path = settings.embedding_model_dir
    _device = None

    @classmethod
    def _detect_device(cls):
        if cls._device is not None:
            return cls._device
        try:
            import torch
            if torch.cuda.is_available():
                cls._device = "cuda"
                gpu_name = torch.cuda.get_device_name(0)
                gpu_mem = torch.cuda.get_device_properties(0).total_mem / 1024**3
                print(f"   🚀 GPU 检测成功: {gpu_name} ({gpu_mem:.1f} GB)")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                cls._device = "mps"
                print(f"   🍎 Apple MPS (Metal) 可用")
            else:
                cls._device = "cpu"
                print(f"   ⚠️ 未检测到 GPU，使用 CPU 编码（速度较慢）")
        except ImportError:
            cls._device = "cpu"
        return cls._device

    @classmethod
    def get_model(cls):
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    device = cls._detect_device()
                    print(f"   📦 加载模型 {cls._model_path} -> {device} ...")
                    cls._model = SentenceTransformer(cls._model_path, device=device)
                    print(f"   ✅ 模型加载完成")
        return cls._model


# ═══════════════════════════════════════════════════════════════
# 索引创建 / 导入
# ═══════════════════════════════════════════════════════════════

def ensure_index(client, index_name):
    """确保索引存在，不存在则创建 KNN 索引。"""
    if client.indices.exists(index=index_name):
        print(f"   ✅ 索引已存在: {index_name}")
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
    print(f"   ✅ 创建 KNN 索引: {index_name}")


def convert_vector_to_list(vector):
    """将 numpy 数组转换为 Python 列表（OpenSearch 需要）。"""
    if isinstance(vector, np.ndarray):
        return vector.tolist()
    return vector


def bulk_import_city(client, file_path, city_name):
    """导入单个城市的数据：business → yelp_business, reviews → yelp_review。"""
    filename = os.path.basename(file_path)
    print(f"\n{'='*60}")
    print(f"📥 导入 {city_name} 数据 ({filename})")
    print(f"{'='*60}")

    ensure_index(client, BUSINESS_INDEX)
    ensure_index(client, REVIEW_INDEX)

    model = ModelSingleton.get_model()
    overall_start = time.time()

    # ── 第一阶段：读取文件，解析 JSON ──
    print(f"   📖 读取 JSON 文件...")
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_docs = json.load(f)

    total_raw = len(raw_docs)
    print(f"   ✅ 读取完成: {total_raw} 条原始文档")

    # ── 第二阶段：字段映射 + 准备待编码文本 ──
    businesses: list[tuple[dict, str, str]] = []  # (normalized_doc, text, business_id)
    reviews: list[dict] = []  # normalized reviews

    for raw in raw_docs:
        # 跳过空文档
        if not raw.get("keyword") or not raw.get("餐厅名称"):
            continue
        biz = normalize_business(raw, city_name)
        text = format_text_for_embedding(biz)
        biz_id = biz["business_id"]
        businesses.append((biz, text, biz_id))

        # 提取内联评价
        eval_list = raw.get("评价列表", [])
        for idx, rev in enumerate(eval_list):
            reviews.append(normalize_review(rev, biz_id, idx))

    total_biz = len(businesses)
    total_rev = len(reviews)
    print(f"   📊 商家: {total_biz} 家, 评价: {total_rev} 条")

    if total_biz == 0:
        print(f"   ❌ 没有有效数据，跳过")
        return

    # ── 第三阶段：批量编码 ──
    all_texts = [t for _, t, _ in businesses]
    print(f"   🔢 批量编码 {total_biz} 条商家文本 "
          f"(encoding_batch={ENCODING_BATCH_SIZE})...")
    encode_start = time.time()

    all_embeddings = model.encode(
        all_texts,
        batch_size=ENCODING_BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    encode_elapsed = time.time() - encode_start
    encode_rate = total_biz / encode_elapsed if encode_elapsed > 0 else 0
    print(f"   ✅ 编码完成: {encode_elapsed:.1f}s ({encode_rate:.0f} 条/秒)")

    # ── 第四阶段：写入商家到 yelp_business ──
    success_biz = 0
    error_biz = 0
    batch_actions: list[dict] = []
    write_start = time.time()

    for idx, (biz, text, biz_id) in enumerate(businesses):
        biz["embedding"] = convert_vector_to_list(all_embeddings[idx])
        biz["text_for_embedding"] = text

        action = {
            "_index": BUSINESS_INDEX,
            "_id": biz_id,
            "_source": biz,
        }
        batch_actions.append(action)

        if len(batch_actions) >= BATCH_SIZE:
            success, errors = bulk(
                client, batch_actions,
                chunk_size=BATCH_SIZE,
                raise_on_error=False,
            )
            success_biz += success
            if errors:
                error_biz += len(errors)
            elapsed = time.time() - write_start
            rate = success_biz / elapsed if elapsed > 0 else 0
            print(f"   商家写入: {success_biz}/{total_biz} | "
                  f"失败: {error_biz} | 速率: {rate:.0f} 条/秒")
            batch_actions = []

    if batch_actions:
        success, errors = bulk(client, batch_actions, raise_on_error=False)
        success_biz += success
        if errors:
            error_biz += len(errors)

    biz_elapsed = time.time() - write_start
    print(f"   ✅ 商家写入完成: {success_biz}/{total_biz} ({biz_elapsed:.1f}s)")

    # ── 第五阶段：写入评价到 yelp_review ──
    if reviews:
        rev_start = time.time()
        rev_batch: list[dict] = []
        success_rev = 0
        error_rev = 0

        for rev in reviews:
            action = {
                "_index": REVIEW_INDEX,
                "_id": rev["review_id"],
                "_source": rev,
            }
            rev_batch.append(action)

            if len(rev_batch) >= BATCH_SIZE:
                success, errors = bulk(
                    client, rev_batch,
                    chunk_size=BATCH_SIZE,
                    raise_on_error=False,
                )
                success_rev += success
                if errors:
                    error_rev += len(errors)
                rev_batch = []

        if rev_batch:
            success, errors = bulk(client, rev_batch, raise_on_error=False)
            success_rev += success
            if errors:
                error_rev += len(errors)

        rev_elapsed = time.time() - rev_start
        print(f"   ✅ 评价写入完成: {success_rev}/{total_rev} ({rev_elapsed:.1f}s)")

    total_elapsed = time.time() - overall_start
    print(f"\n✅ {city_name} 导入完成!")
    print(f"   商家: {success_biz} 条 | 评价: {len(reviews)} 条")
    print(f"   总耗时: {total_elapsed:.1f}s")


def verify_data(client):
    """验证导入的数据 — 按城市统计。"""
    print("\n" + "=" * 60)
    print("🔍 验证导入结果")
    print("=" * 60)

    if client.indices.exists(index=BUSINESS_INDEX):
        total = client.count(index=BUSINESS_INDEX)['count']
        print(f"\n   yelp_business 总文档数: {total}")

        # 按城市统计
        for city in ["北京", "成都", "广州", "上海"]:
            try:
                resp = client.search(
                    index=BUSINESS_INDEX,
                    body={
                        "size": 0,
                        "query": {"term": {"city.keyword": city}},
                    }
                )
                count = resp["hits"]["total"]["value"]
                print(f"     {city}: {count} 家")
            except Exception:
                print(f"     {city}: (查询失败)")

    if client.indices.exists(index=REVIEW_INDEX):
        total = client.count(index=REVIEW_INDEX)['count']
        print(f"\n   yelp_review 总文档数: {total}")

    # 随机展示几条北京数据
    print(f"\n   随机查询北京商家示例:")
    try:
        res = client.search(
            index=BUSINESS_INDEX,
            body={
                "size": 3,
                "query": {"term": {"city.keyword": "北京"}},
            }
        )
        for hit in res["hits"]["hits"]:
            s = hit["_source"]
            name = s.get("name", "N/A")
            cat = s.get("categories", "N/A")
            stars = s.get("stars", "N/A")
            city = s.get("city", "N/A")
            nb = s.get("neighborhood", "N/A")
            print(f"   - {name} [{cat}] ★{stars} | {city}·{nb}")
    except Exception as e:
        print(f"   (查询失败: {e})")


def main():
    print("=" * 60)
    print("国内城市数据导入 OpenSearch (统一字段映射版)")
    print("=" * 60)
    print(f"目标索引: {BUSINESS_INDEX} / {REVIEW_INDEX}")
    print()

    # 连接 OpenSearch
    client = get_opensearch_client()
    if not client:
        print("❌ 无法连接到 OpenSearch，请检查服务是否启动")
        return

    # 数据文件 → 城市名
    city_files = {
        BEIJING_FILE: "北京",
        CHENGDU_FILE: "成都",
        GUANGZHOU_FILE: "广州",
        SHANGHAI_FILE: "上海",
    }

    for file_path, city_name in city_files.items():
        if not os.path.exists(file_path):
            print(f"❌ 找不到 {city_name} 数据文件: {file_path}")
            return

    print("✅ 数据文件检查通过")
    print(f"   北京: {os.path.getsize(BEIJING_FILE)/1024:.0f} KB")
    print(f"   成都: {os.path.getsize(CHENGDU_FILE)/1024:.0f} KB")
    print(f"   广州: {os.path.getsize(GUANGZHOU_FILE)/1024:.0f} KB")
    print(f"   上海: {os.path.getsize(SHANGHAI_FILE)/1024:.0f} KB")

    for file_path, city_name in city_files.items():
        bulk_import_city(
            client=client,
            file_path=file_path,
            city_name=city_name,
        )

    # 验证
    verify_data(client)

    print("\n" + "=" * 60)
    print("🎉🎉🎉 国内城市数据导入完成!")
    print("=" * 60)
    print("\n💡 提示：现在可以直接问「北京的烤鸭推荐」「成都的火锅」等")
    print("   数据已导入到 yelp_business / yelp_review，现有检索代码无需修改。")


if __name__ == "__main__":
    main()
