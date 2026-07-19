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
#项目的根路径
BASE_DIR = os.path.dirname(current_script_dir)
#数据的路径
DATA_DIR = os.path.join(BASE_DIR, "knowledge_base", "small_data")

#数据文件名
CHENGDU_FILE = os.path.join(DATA_DIR, "chengdu.json")
BEIJING_FILE = os.path.join(DATA_DIR, "beijing.json")
GUANGZHOU_FILE = os.path.join(DATA_DIR, "guangzhou.json")
SHANGHAI_FILE= os.path.join(DATA_DIR, "shanghai.json")

# 索引名称
BEIJING_INDEX="beijing"
CHENGDU_INDEX="chengdu"
GUANGZHOU_INDEX="guangzhou"
SHANGHAI_INDEX="shanghai"


# 向量维度 (BAAI/bge-base-zh-v1.5 模型)
VECTOR_DIM = 768

# 批量处理大小（写入 OpenSearch 的批次大小）
BATCH_SIZE = 500

# 编码批次大小（GPU 批量推理的批次大小，根据显存调整）
ENCODING_BATCH_SIZE = 64


class ModelSingleton:
    """线程安全的 SentenceTransformer 单例，自动检测 GPU"""

    _model = None
    _lock = threading.Lock()
    _model_path = settings.embedding_model_dir
    _device = None  # 缓存检测到的设备

    @classmethod
    def _detect_device(cls):
        """检测可用设备：CUDA > MPS > CPU，并打印设备信息"""
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
                print(f"   💡 提示: 如需 GPU 加速，请安装 CUDA 版 PyTorch:")
                print(f"      pip install torch --index-url https://download.pytorch.org/whl/cu121")
        except ImportError:
            cls._device = "cpu"
            print(f"   ⚠️ torch 未安装，回退到 CPU")

        return cls._device

    @classmethod
    def get_model(cls):
        """返回模型单例，首次调用时自动检测设备并加载模型"""
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    device = cls._detect_device()
                    print(f"   📦 加载模型 {cls._model_path} -> {device} ...")
                    cls._model = SentenceTransformer(
                        cls._model_path,
                        device=device,
                    )
                    print(f"   ✅ 模型加载完成")
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
    """批量导入数据（优化版：分两阶段 — 先批量编码，再批量写入）"""
    print(f"\n📥 导入数据到 {index_name}")
    create_knn_index(client, index_name)

    model = ModelSingleton.get_model()
    overall_start = time.time()

    # ═══════════════════════════════════════════════════════════
    # 第一阶段：读取文件，解析 JSON，准备待编码文本
    # ═══════════════════════════════════════════════════════════
    documents: list[tuple[dict, str,str| None]] = []  # (doc, text, doc_id)
    parse_errors = 0

    print(f"   📖 读取并解析 JSON 文件...")
    with open(file_path, 'r', encoding='utf-8') as f:
        docs = json.load(f)
        for doc in docs:
            text=traverse_json(doc)
            doc_id=doc.get("keyword")
            documents.append((doc, text,doc_id))



    total_count = len(documents)
    if total_count == 0:
        print(f"   ❌ 没有有效数据，跳过 {index_name}")
        return

    read_elapsed = time.time() - overall_start
    print(f"   ✅ 读取完成: {total_count} 条文档 ({read_elapsed:.1f}s)"
          + (f", 解析失败 {parse_errors} 行" if parse_errors else ""))

    # ═══════════════════════════════════════════════════════════
    # 第二阶段：批量编码（关键优化！一次性批量推理）
    # ═══════════════════════════════════════════════════════════
    all_texts = [text for _, text,_ in documents]
    print(f"   🔢 开始批量编码 {total_count} 条文本 "
          f"(encoding_batch={ENCODING_BATCH_SIZE})...")
    encode_start = time.time()

    # 使用 model.encode 的批量推理，充分利用 GPU
    all_embeddings = model.encode(
        all_texts,
        batch_size=ENCODING_BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    encode_elapsed = time.time() - encode_start
    encode_rate = total_count / encode_elapsed if encode_elapsed > 0 else 0
    print(f"   ✅ 编码完成: {encode_elapsed:.1f}s ({encode_rate:.0f} 条/秒)")

    # ═══════════════════════════════════════════════════════════
    # 第三阶段：构建 action 并批量写入 OpenSearch
    # ═══════════════════════════════════════════════════════════
    success_count = 0
    error_count = 0
    batch_actions: list[dict] = []
    write_start = time.time()

    for idx, (doc, text,doc_id) in enumerate(documents):
        # 把向量填入文档
        doc["embedding"] = convert_vector_to_list(all_embeddings[idx])
        doc["text_for_embedding"] = text

        action = {
            "_index": index_name,
            "_id":doc_id,
            "_source": doc,
        }
        batch_actions.append(action)

        if len(batch_actions) >= BATCH_SIZE:
            success, errors = bulk(
                client,
                batch_actions,
                chunk_size=BATCH_SIZE,
                raise_on_error=False,
            )
            success_count += success
            if errors:
                error_count += len(errors)

            elapsed = time.time() - write_start
            rate = success_count / elapsed if elapsed > 0 else 0
            print(f"   已写入: {success_count}/{total_count} | "
                  f"失败: {error_count} | 速率: {rate:.0f} 条/秒")

            batch_actions = []

    # 处理剩余的数据
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
    total_elapsed = time.time() - overall_start
    print(f"\n✅ {index_name} 导入完成!")
    print(f"   总处理: {total_count} 条")
    print(f"   成功: {success_count} 条")
    print(f"   失败: {error_count} 条")
    print(f"   编码耗时: {encode_elapsed:.1f}s | 写入耗时: {write_elapsed:.1f}s | 总耗时: {total_elapsed:.1f}s")
    print(f"   平均速度: {success_count / total_elapsed:.1f} 条/秒")


def verify_data(client):
    """验证导入的数据"""
    print("\n🔍 验证导入结果...")

    # 检查索引是否存在
    for index_name in [BEIJING_INDEX, CHENGDU_INDEX,GUANGZHOU_INDEX,SHANGHAI_INDEX]:
        if client.indices.exists(index=index_name):
            count = client.count(index=index_name)['count']
            print(f"   {index_name}: {count}条记录")

    # 随机查询几条数据
    print("\n   随机查询商家示例:")
    res = client.search(
        index=BEIJING_INDEX,
        body={
            "size": 3,
            "query": {"match_all": {}}
        }
    )

    for hit in res["hits"]["hits"]:
        source = hit["_source"]
        name = source.get("餐厅名称", "N/A")
        type = source.get("菜系", "N/A")
        stars = source.get("综合评分", "N/A")
        print(f"   - {name} ({type}) ★{stars}")



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
    if not os.path.exists(BEIJING_FILE):
        print(f"❌ 找不到北京的数据文件: {BEIJING_FILE}")

        return
    if not os.path.exists(CHENGDU_FILE):
        print(f"❌ 找不到成都数据文件: {CHENGDU_FILE}")
        return
    if not os.path.exists(GUANGZHOU_FILE):
        print(f"❌ 找不到广州数据文件: {GUANGZHOU_FILE}")
        return
    if not os.path.exists(SHANGHAI_FILE):
        print(f"❌ 找不到tip数据文件: {SHANGHAI_FILE}")
        return


    print(f"\n数据文件检查通过:")

    # 导入商家数据
    bulk_import(
        client=client,
        file_path=BEIJING_FILE,
        index_name=BEIJING_INDEX,
    )
    # # 导入评论数据
    bulk_import(
        client=client,
        file_path=CHENGDU_FILE,
        index_name=CHENGDU_INDEX,
    )
    bulk_import(
        client=client,
        file_path=GUANGZHOU_FILE,
        index_name=GUANGZHOU_INDEX,
    )
    bulk_import(
        client=client,
        file_path=SHANGHAI_FILE,
        index_name=SHANGHAI_INDEX,
    )

    # 验证数据
    verify_data(client)

    print("\n" + "=" * 60)
    print("🎉🎉🎉 数据导入完成!")
    print("=" * 60)



if __name__ == "__main__":
    main()