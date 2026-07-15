from typing import Any
from config import settings
from opensearch_client import get_opensearch_client
from ingest_to_opensearch import ModelSingleton


def embed_query(query: str) -> list[float]:
    """把用户查询转成向量"""
    model = ModelSingleton().get_model()
    return model.encode(query, convert_to_numpy=True).tolist()

def _format_hits(resp: dict) -> list[dict]:
    """把 OpenSearch 原始响应格式化成简洁的 dict 列表"""
    hits = []
    for hit in resp["hits"]["hits"]:
        item = dict(hit["_source"])
        item["_score"] = hit["_score"]
        hits.append(item)
    return hits


#向量检索
def vector_search(
    query: str,
    k: int =20,
    index_name: str = None,
) -> list[dict]:
    """
    向量检索：把 query embedding 出来，在 OpenSearch 里找最相似的 k 个 记录
    返回：list of dict
    """
    client = get_opensearch_client()

    query_vec = embed_query(query)

    body = {
        "size": k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_vec,
                    "k": k,
                }
            }
        },
        # 显式排除 embedding，返回结果里不带向量字段
        "_source": ["chunk_id", "document_id", "source_file", "chunk_index", "text"],
    }

    resp = client.search(index=index_name, body=body)
    return _format_hits(resp)




