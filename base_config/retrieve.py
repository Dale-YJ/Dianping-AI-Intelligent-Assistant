import threading

from opensearch_client import get_opensearch_client
from ingest_to_opensearch import ModelSingleton
from typing import Literal
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun


# 索引名称
BUSINESS_INDEX = "yelp_business"
REVIEW_INDEX = "yelp_review"
CHECKIN_INDEX="yelp_checkin"
TIP_INDEX="yelp_tip"
USER_INDEX="yelp_user"

BEIJING_INDEX="beijing"
CHENGDU_INDEX="chengdu"
GUANGZHOU_INDEX="guangzhou"
SHANGHAI_INDEX="shanghai"


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
    k: int =5,
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
        "_source": {"excludes": ["embedding"]},
    }

    resp = client.search(index=index_name, body=body)
    return _format_hits(resp)


def bm25_search(
        query: str,
        k: int = 5,
        index_name: str = None,
) -> list[dict]:
    """
    BM25 关键词检索：text_for_embedding字段的全文匹配
    """
    client = get_opensearch_client()

    body = {
        "size": k,
        "query": {
            "match": {
                "text_for_embedding": {
                    "query": query,
                }
            }
        },
        "_source": {"excludes": ["embedding"]},
    }
    resp = client.search(index=index_name, body=body)
    return _format_hits(resp)


def hybrid_search(
        query: str,
        k: int = 5,
        vector_boost: float = 2.0,
        bm25_boost: float = 1.0,
        index_name: str = None,
) -> list[dict]:
    """
    混合检索：向量 + BM25 并行，分数加权融合
    """
    client = get_opensearch_client()


    query_vec = embed_query(query)

    body = {
        "size": k,
        "query": {
            "bool": {
                "should": [
                    {
                        "knn": {
                            "embedding": {
                                "vector": query_vec,
                                "k": k * 4,  # 扩大召回池规模以稳定融合结果
                                "boost": vector_boost,
                            }
                        }
                    },
                    {
                        "match": {
                            "text_for_embedding": {
                                "query": query,
                                "boost": bm25_boost,
                            }
                        }
                    }
                ]
            }
        },
        "_source": {"excludes": ["embedding"]},
    }

    resp = client.search(index=index_name, body=body)
    return _format_hits(resp)

# 全局锁和实例缓存
_retriever_lock = threading.RLock()
_retriever_instances = {}

class OpenSearchRetriever(BaseRetriever):
    """
    OpenSearch 检索器，支持向量/BM25/混合三种模式。
    实现了 LangChain BaseRetriever 接口，可以直接用在 LCEL 管道里。
    """

    mode: Literal["vector", "bm25", "hybrid"] = "hybrid"
    k: int = 5
    vector_boost: float = 2.0
    bm25_boost: float = 1.0
    index_name: str | None = None

    def _get_relevant_documents(
            self,
            query: str,
            *,
            run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        if self.mode == "vector":
            hits = vector_search(query, k=self.k, index_name=self.index_name)
        elif self.mode == "bm25":
            hits = bm25_search(query, k=self.k, index_name=self.index_name)
        elif self.mode == "hybrid":
            hits = hybrid_search(
                query,
                k=self.k,
                vector_boost=self.vector_boost,
                bm25_boost=self.bm25_boost,
                index_name=self.index_name,
            )
        else:
            raise ValueError(f"unknown mode: {self.mode}")

        return [
            Document(
                page_content=h["text_for_embedding"],
            )
            for h in hits
        ]

    @classmethod
    def get_instance(cls, **kwargs) -> "OpenSearchRetriever":
        """线程安全的单例获取方法"""
        # 创建缓存键（基于参数）
        key = (
            kwargs.get("mode", "hybrid"),
            kwargs.get("k", 5),
            kwargs.get("vector_boost", 2.0),
            kwargs.get("bm25_boost", 1.0),
            kwargs.get("index_name"),
        )

        # 双重检查锁
        if key not in _retriever_instances:
            with _retriever_lock:
                if key not in _retriever_instances:
                    _retriever_instances[key] = cls(**kwargs)

        return _retriever_instances[key]

def get_retriever(
        mode: Literal["vector", "bm25", "hybrid"] = "hybrid",
        k: int = 5,
        **kwargs,
) -> OpenSearchRetriever:
    """便捷工厂"""
    return OpenSearchRetriever.get_instance(
        mode=mode,
        k=k,
        **kwargs
    )


if __name__ == "__main__":
    # 用默认混合检索
    retriever = get_retriever(k=2,index_name=BEIJING_INDEX)

    docs = retriever.invoke("我想要吃川菜")
    for doc in docs:
        print(doc)
        print(type(doc))


