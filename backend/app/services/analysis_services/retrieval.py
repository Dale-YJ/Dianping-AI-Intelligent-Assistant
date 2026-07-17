"""OpenSearch 数据检索服务

使用 base_config 提供的 OpenSearch 客户端，具备线程安全、重试机制、超时设置等特性。
"""
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional

from opensearchpy import OpenSearchException

# 添加 base_config 到 sys.path
BASE_CONFIG_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent / "base_config"
if str(BASE_CONFIG_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_CONFIG_ROOT))

# 导入 base_config 提供的线程安全客户端
from opensearch_client import get_opensearch_client as _get_opensearch_client

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── OpenSearch 客户端（复用 base_config）──────────────────────

def get_opensearch_client():
    """获取 OpenSearch 客户端（复用 base_config 实现）

    特性：
    - 线程安全的单例模式（双重检查锁）
    - 自动重试机制（max_retries=3）
    - 超时设置（timeout=30）
    - SSL证书处理
    """
    return _get_opensearch_client()


# ── 商家查询接口 ───────────────────────────────────────────

def get_business_by_id(business_id: str) -> Optional[dict]:
    """根据 ID 获取商家信息

    Args:
        business_id: 商家ID

    Returns:
        商家信息字典，不存在返回 None
    """
    try:
        client = get_opensearch_client()

        # 使用 get 方法查询单条数据
        res = client.get(
            index=settings.business_index,
            id=business_id,
            ignore=[404]  # 文档不存在时返回 None
        )

        if res.get("found", False):
            logger.info(f"查询商家成功: business_id={business_id}")
            return res["_source"]
        else:
            logger.warning(f"商家不存在: business_id={business_id}")
            return None

    except OpenSearchException as e:
        logger.error(f"查询商家失败: {e}")
        return None


def get_all_businesses(size: int = 1000) -> List[dict]:
    """获取所有商家（match_all 查询）

    Args:
        size: 返回数量，默认 1000

    Returns:
        商家列表
    """
    try:
        client = get_opensearch_client()

        # 使用 match_all 查询所有数据
        res = client.search(
            index=settings.business_index,
            body={
                "size": size,
                "query": {"match_all": {}}
            }
        )

        businesses = [hit["_source"] for hit in res["hits"]["hits"]]
        logger.info(f"查询所有商家成功: 返回 {len(businesses)} 家")
        return businesses

    except OpenSearchException as e:
        logger.error(f"查询所有商家失败: {e}")
        return []


def search_businesses(
    keyword: str = "",
    category: str = "",
    min_rating: float = 0,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "rating"
) -> tuple[List[dict], int]:
    """商家搜索（bool 组合查询）

    Args:
        keyword: 关键词（商家名称）
        category: 分类
        min_rating: 最低评分
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段（rating 或 review_count）

    Returns:
        (结果列表, 总数)
    """
    try:
        client = get_opensearch_client()

        # 构建 bool 查询
        must_clauses = []
        filter_clauses = []

        # 关键词匹配（全文搜索）
        if keyword:
            must_clauses.append({
                "match": {"name": keyword}
            })

        # 分类匹配（精确匹配）
        if category:
            filter_clauses.append({
                "term": {"categories": category}
            })

        # 评分范围（范围查询）
        if min_rating > 0:
            filter_clauses.append({
                "range": {"stars": {"gte": min_rating}}
            })

        # 构建查询体
        query_body = {
            "query": {
                "bool": {}
            },
            "from": (page - 1) * page_size,
            "size": page_size
        }

        if must_clauses:
            query_body["query"]["bool"]["must"] = must_clauses

        if filter_clauses:
            query_body["query"]["bool"]["filter"] = filter_clauses

        # 如果没有任何条件，使用 match_all
        if not must_clauses and not filter_clauses:
            query_body["query"] = {"match_all": {}}

        # 排序
        if sort_by == "rating":
            query_body["sort"] = [{"stars": {"order": "desc"}}]
        elif sort_by == "review_count":
            query_body["sort"] = [{"review_count": {"order": "desc"}}]

        # 执行查询
        res = client.search(
            index=settings.business_index,
            body=query_body
        )

        businesses = [hit["_source"] for hit in res["hits"]["hits"]]
        total = res["hits"]["total"]["value"]

        logger.info(f"商家搜索成功: 关键词={keyword}, 分类={category}, 返回 {len(businesses)}/{total} 家")
        return businesses, total

    except OpenSearchException as e:
        logger.error(f"商家搜索失败: {e}")
        return [], 0


# ── 评价查询接口 ───────────────────────────────────────────

def vector_search_reviews(business_id: str = "", query: str = "", top_k: int = 10) -> List[dict]:
    """查询评价（支持关键词搜索）

    Args:
        business_id: 商家ID（可选，不提供时查询全部）
        query: 查询文本（可选）
        top_k: 返回数量

    Returns:
        评价列表
    """
    try:
        client = get_opensearch_client()

        # 构建 bool 查询
        must_clauses = []
        filter_clauses = []

        # 商家 ID（精确匹配，使用 .keyword 字段） - 仅在提供时过滤
        if business_id:
            filter_clauses.append({
                "term": {"business_id.keyword": business_id}
            })

        # 关键词匹配（全文搜索）
        if query:
            must_clauses.append({
                "match": {"text": query}
            })

        # 构建查询体
        query_body = {
            "query": {
                "bool": {}
            },
            "size": top_k
        }

        if filter_clauses:
            query_body["query"]["bool"]["filter"] = filter_clauses

        if must_clauses:
            query_body["query"]["bool"]["must"] = must_clauses

        # 如果没有任何条件，使用 match_all
        if not filter_clauses and not must_clauses:
            query_body["query"] = {"match_all": {}}

        # 执行查询
        res = client.search(
            index=settings.review_index,
            body=query_body
        )

        reviews = [hit["_source"] for hit in res["hits"]["hits"]]
        if business_id:
            logger.info(f"查询评价成功: business_id={business_id}, 返回 {len(reviews)} 条")
        else:
            logger.info(f"查询全部评价成功: 返回 {len(reviews)} 条")
        return reviews

    except OpenSearchException as e:
        logger.error(f"查询评价失败: {e}")
        return []


def get_reviews_by_rating(
    business_id: str = "",
    min_rating: int = 0,
    max_rating: int = 5,
    size: int = 100
) -> List[dict]:
    """按评分范围查询评价

    Args:
        business_id: 商家ID（可选，不提供时查询全部）
        min_rating: 最低评分
        max_rating: 最高评分
        size: 返回数量

    Returns:
        评价列表
    """
    try:
        client = get_opensearch_client()

        # 构建过滤条件
        filter_clauses = []

        # 商家ID（可选）
        if business_id:
            filter_clauses.append({"term": {"business_id.keyword": business_id}})

        # 评分范围
        filter_clauses.append({"range": {"stars": {"gte": min_rating, "lte": max_rating}}})

        # 组合查询
        query_body = {
            "query": {
                "bool": {
                    "filter": filter_clauses
                }
            },
            "size": size
        }

        res = client.search(
            index=settings.review_index,
            body=query_body
        )

        reviews = [hit["_source"] for hit in res["hits"]["hits"]]
        if business_id:
            logger.info(f"按评分查询评价成功: business_id={business_id}, 评分 {min_rating}-{max_rating}, 返回 {len(reviews)} 条")
        else:
            logger.info(f"按评分查询全部评价成功: 评分 {min_rating}-{max_rating}, 返回 {len(reviews)} 条")
        return reviews

    except OpenSearchException as e:
        logger.error(f"按评分查询评价失败: {e}")
        return []


# ── 兼容旧接口（保持向后兼容）────────────────────────────

def search_businesses_local(
    keyword: str = "",
    category: str = "",
    min_rating: float = 0,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "rating"
) -> tuple[List[dict], int]:
    """本地商家搜索（兼容旧接口）

    Args:
        keyword: 关键词
        category: 分类
        min_rating: 最低评分
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段

    Returns:
        (结果列表, 总数)
    """
    return search_businesses(
        keyword=keyword,
        category=category,
        min_rating=min_rating,
        page=page,
        page_size=page_size,
        sort_by=sort_by
    )