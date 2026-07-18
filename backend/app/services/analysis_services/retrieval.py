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


# ── 性能优化接口（避免O(n^2)查询）────────────────────────────

def get_businesses_with_reviews(
    keyword: str = "",
    category: str = "",
    min_rating: float = 0,
    min_reviews: int = 1,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "rating"
) -> tuple[List[dict], int]:
    """高效获取有评价的商家列表
    
    使用聚合查询一次性获取所有有评价的商家，避免逐个商家查询
    
    性能对比：
    - 旧方法：O(n) - 每个商家发一次请求
    - 新方法：O(1) - 只发2次请求（聚合+批量查询）
    
    Args:
        keyword: 关键词
        category: 分类
        min_rating: 最低评分
        min_reviews: 最低评价数量
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段
        
    Returns:
        (商家列表, 总数)
    """
    try:
        client = get_opensearch_client()
        
        # 步骤1: 使用聚合获取所有有评价的商家ID及其评价数量
        logger.info("步骤1: 聚合查询有评价的商家ID...")
        
        agg_query = {
            "size": 0,
            "aggs": {
                "businesses_with_reviews": {
                    "terms": {
                        "field": "business_id.keyword",  # 使用 .keyword 字段
                        "size": 10000,  # 最多返回10000个商家
                        "min_doc_count": min_reviews  # 至少有多少条评价
                    },
                    "aggs": {
                        "avg_rating": {
                            "avg": {
                                "field": "stars"
                            }
                        }
                    }
                }
            }
        }
        
        agg_response = client.search(
            index=settings.review_index,
            body=agg_query
        )
        
        # 提取商家ID和评价数量
        business_review_counts = {}
        for bucket in agg_response["aggregations"]["businesses_with_reviews"]["buckets"]:
            business_id = bucket["key"]
            review_count = bucket["doc_count"]
            business_review_counts[business_id] = review_count
        
        logger.info(f"聚合完成: 找到 {len(business_review_counts)} 个有评价的商家")
        
        if not business_review_counts:
            return [], 0
        
        # 步骤2: 批量查询这些商家的详细信息
        logger.info("步骤2: 批量查询商家详细信息...")
        
        business_ids = list(business_review_counts.keys())
        
        # 使用 mget 批量获取（一次请求获取所有商家）
        mget_response = client.mget(
            index=settings.business_index,
            body={
                "ids": business_ids
            }
        )
        
        # 构建商家列表
        all_businesses = []
        for doc in mget_response["docs"]:
            if doc.get("found", False):
                business = doc["_source"]
                business_id = business.get("business_id")
                
                # 添加真实评价数量
                if business_id in business_review_counts:
                    business["real_review_count"] = business_review_counts[business_id]
                    all_businesses.append(business)
        
        logger.info(f"批量查询完成: 返回 {len(all_businesses)} 个商家")
        
        # 步骤3: 应用筛选条件
        filtered_businesses = []
        for biz in all_businesses:
            # 关键词筛选
            if keyword and keyword.lower() not in biz.get("name", "").lower():
                continue
            
            # 分类筛选
            if category and category not in biz.get("categories", ""):
                continue
            
            # 评分筛选
            if min_rating > 0 and biz.get("stars", 0) < min_rating:
                continue
            
            filtered_businesses.append(biz)
        
        logger.info(f"筛选完成: {len(filtered_businesses)}/{len(all_businesses)} 个商家符合条件")
        
        # 步骤4: 排序
        if sort_by == "rating":
            filtered_businesses.sort(key=lambda x: x.get("stars", 0), reverse=True)
        elif sort_by == "review_count":
            filtered_businesses.sort(key=lambda x: x.get("real_review_count", 0), reverse=True)
        
        # 步骤5: 分页
        total = len(filtered_businesses)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_businesses = filtered_businesses[start:end]
        
        logger.info(f"分页返回: {len(paginated_businesses)}/{total} 个商家 (第{page}页)")
        
        return paginated_businesses, total
        
    except Exception as e:
        logger.error(f"高效查询失败: {e}")
        return [], 0