"""用户评价 CRUD 服务

提供用户评价的创建、查询、修改、删除功能。
用户评价存储在独立的 OpenSearch 索引 `user_review` 中，
与预导入的 `yelp_review` 索引隔离。
"""
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from opensearchpy import OpenSearchException

# 添加 base_config 到 sys.path
BASE_CONFIG_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent / "base_config"
if str(BASE_CONFIG_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_CONFIG_ROOT))

from opensearch_client import get_opensearch_client as _get_opensearch_client

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── OpenSearch 客户端 ──────────────────────────────────────

def get_client():
    """获取 OpenSearch 客户端"""
    return _get_opensearch_client()


# ── 索引管理 ──────────────────────────────────────────────

USER_REVIEW_MAPPING = {
    "mappings": {
        "properties": {
            "review_id":   {"type": "keyword"},
            "business_id": {"type": "keyword"},
            "user_name":   {"type": "text"},
            "rating":      {"type": "integer"},
            "text":        {"type": "text"},
            "created_at":  {"type": "date"},
            "updated_at":  {"type": "date"},
        }
    }
}


def ensure_user_review_index() -> bool:
    """确保 user_review 索引存在，不存在则创建。

    Returns:
        True 表示索引已就绪，False 表示创建失败。
    """
    try:
        client = get_client()
        if client.indices.exists(index=settings.user_review_index):
            logger.info(f"索引 {settings.user_review_index} 已存在")
            return True

        client.indices.create(
            index=settings.user_review_index,
            body=USER_REVIEW_MAPPING,
        )
        logger.info(f"索引 {settings.user_review_index} 创建成功")
        return True
    except Exception as e:
        logger.error(f"索引 {settings.user_review_index} 创建失败: {e}")
        return False


# ── 评价 CRUD ─────────────────────────────────────────────

def create_review(
    business_id: str,
    user_name: str,
    rating: int,
    text: str,
) -> dict:
    """创建用户评价。

    Args:
        business_id: 商家 ID
        user_name: 用户昵称
        rating: 评分（1-5）
        text: 评价内容

    Returns:
        创建的评价数据（包含生成的 review_id 和时间戳）
    """
    client = get_client()
    review_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    doc = {
        "review_id": review_id,
        "business_id": business_id,
        "user_name": user_name,
        "rating": rating,
        "text": text,
        "created_at": now,
        "updated_at": now,
    }

    try:
        client.index(
            index=settings.user_review_index,
            id=review_id,
            body=doc,
            refresh="wait_for",  # 确保写入后立即可搜索
        )
        logger.info(f"用户评价创建成功: review_id={review_id}, business_id={business_id}")
        return doc
    except OpenSearchException as e:
        logger.error(f"用户评价创建失败: {e}")
        raise


def update_review(
    review_id: str,
    rating: Optional[int] = None,
    text: Optional[str] = None,
) -> Optional[dict]:
    """部分更新用户评价。仅更新传入的非 None 字段。

    Args:
        review_id: 评价 ID
        rating: 新评分（可选）
        text: 新评价内容（可选）

    Returns:
        更新后的完整评价数据，不存在返回 None
    """
    client = get_client()

    # 先检查评价是否存在
    existing = get_user_review(review_id)
    if not existing:
        logger.warning(f"用户评价不存在，无法更新: review_id={review_id}")
        return None

    # 构建更新体（仅包含非 None 字段）
    update_fields = {}
    if rating is not None:
        update_fields["rating"] = rating
    if text is not None:
        update_fields["text"] = text
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    if not update_fields:
        return existing  # 无字段需要更新

    try:
        client.update(
            index=settings.user_review_index,
            id=review_id,
            body={"doc": update_fields},
            refresh="wait_for",
        )
        # 合并返回最新数据
        existing.update(update_fields)
        logger.info(f"用户评价更新成功: review_id={review_id}")
        return existing
    except OpenSearchException as e:
        logger.error(f"用户评价更新失败: {e}")
        raise


def delete_review(review_id: str) -> bool:
    """删除用户评价。

    Args:
        review_id: 评价 ID

    Returns:
        True 表示删除成功，False 表示评价不存在
    """
    client = get_client()

    try:
        # 先检查是否存在
        existing = get_user_review(review_id)
        if not existing:
            logger.warning(f"用户评价不存在，无法删除: review_id={review_id}")
            return False

        client.delete(
            index=settings.user_review_index,
            id=review_id,
            refresh="wait_for",
        )
        logger.info(f"用户评价删除成功: review_id={review_id}")
        return True
    except OpenSearchException as e:
        logger.error(f"用户评价删除失败: {e}")
        raise


# ── 评价查询 ──────────────────────────────────────────────

def get_user_review(review_id: str) -> Optional[dict]:
    """根据 ID 获取单条用户评价。

    Args:
        review_id: 评价 ID

    Returns:
        评价数据字典，不存在返回 None
    """
    client = get_client()
    try:
        res = client.get(
            index=settings.user_review_index,
            id=review_id,
            ignore=[404],
        )
        if res.get("found", False):
            return res["_source"]
        return None
    except OpenSearchException as e:
        logger.error(f"查询用户评价失败: {e}")
        return None


def get_user_reviews_by_business(
    business_id: str,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "date",
) -> Tuple[List[dict], int]:
    """分页查询某商家的用户评价。

    Args:
        business_id: 商家 ID
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段（date / rating）

    Returns:
        (评价列表, 总数)
    """
    client = get_client()

    sort_field = "created_at" if sort_by == "date" else "rating"
    sort_order = "desc"

    query_body = {
        "query": {
            "bool": {
                "filter": [
                    {"term": {"business_id": business_id}}
                ]
            }
        },
        "sort": [{sort_field: {"order": sort_order}}],
        "from": (page - 1) * page_size,
        "size": page_size,
    }

    try:
        res = client.search(
            index=settings.user_review_index,
            body=query_body,
        )
        hits = res["hits"]["hits"]
        reviews = [hit["_source"] for hit in hits]
        total = res["hits"]["total"]["value"]
        logger.info(f"查询用户评价成功: business_id={business_id}, 返回 {len(reviews)}/{total} 条")
        return reviews, total
    except OpenSearchException as e:
        logger.error(f"查询用户评价失败: {e}")
        return [], 0


def get_all_reviews_merged(
    business_id: str,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "date",
    min_rating: int = 0,
    source: str = "all",
) -> Tuple[List[dict], int]:
    """合并查询 yelp_review + user_review 两个索引的评价。

    统一排序字段:
        - date: yelp_review 用 date 字段, user_review 用 created_at 字段
        - rating: 都用 rating/stars 字段
        - useful: 仅 yelp_review 有, user_review 排后面

    Args:
        business_id: 商家 ID
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段（date / rating / useful）
        min_rating: 最低评分过滤
        source: 评价来源过滤（all / user / ingested）

    Returns:
        (评价列表, 总数)
    """
    client = get_client()
    all_reviews = []

    # ── 查询 yelp_review（预导入数据） ──
    if source in ("all", "ingested"):
        try:
            yelp_sort_field = {
                "date": "date",
                "rating": "stars",
                "useful": "useful",
            }.get(sort_by, "date")

            yelp_query = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"business_id.keyword": business_id}}
                        ]
                    }
                },
                "sort": [{yelp_sort_field: {"order": "desc"}}],
                "size": 1000,  # 获取全部再分页
            }

            if min_rating > 0:
                yelp_query["query"]["bool"]["filter"].append({
                    "range": {"stars": {"gte": min_rating}}
                })

            res = client.search(
                index=settings.review_index,
                body=yelp_query,
            )
            for hit in res["hits"]["hits"]:
                src = hit["_source"]
                all_reviews.append({
                    "review_id": src.get("review_id", ""),
                    "business_id": src.get("business_id", business_id),
                    "user_name": (src.get("user_id", "") or "")[:8] + "...",
                    "rating": int(src.get("stars", 3)),
                    "text": src.get("text", ""),
                    "date": (src.get("date", "") or "")[:10],
                    "useful": src.get("useful", 0),
                    "funny": src.get("funny", 0),
                    "cool": src.get("cool", 0),
                    "source": "ingested",
                })
        except OpenSearchException as e:
            logger.error(f"查询 yelp_review 失败: {e}")

    # ── 查询 user_review（用户提交数据） ──
    if source in ("all", "user"):
        try:
            user_sort_field = {
                "date": "created_at",
                "rating": "rating",
                "useful": "created_at",  # user_review 无 useful 字段，按时间排序
            }.get(sort_by, "created_at")

            user_query = {
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"business_id": business_id}}
                        ]
                    }
                },
                "sort": [{user_sort_field: {"order": "desc"}}],
                "size": 1000,
            }

            if min_rating > 0:
                user_query["query"]["bool"]["filter"].append({
                    "range": {"rating": {"gte": min_rating}}
                })

            res = client.search(
                index=settings.user_review_index,
                body=user_query,
            )
            for hit in res["hits"]["hits"]:
                src = hit["_source"]
                all_reviews.append({
                    "review_id": src.get("review_id", ""),
                    "business_id": src.get("business_id", business_id),
                    "user_name": src.get("user_name", "匿名用户"),
                    "rating": int(src.get("rating", 3)),
                    "text": src.get("text", ""),
                    "date": (src.get("created_at", "") or "")[:10],
                    "useful": 0,
                    "funny": 0,
                    "cool": 0,
                    "source": "user",
                })
        except OpenSearchException as e:
            logger.error(f"查询 user_review 失败: {e}")

    # ── 统一排序 ──
    if sort_by == "rating":
        all_reviews.sort(key=lambda r: r.get("rating", 0), reverse=True)
    elif sort_by == "useful":
        all_reviews.sort(key=lambda r: r.get("useful", 0), reverse=True)
    else:  # date
        all_reviews.sort(key=lambda r: r.get("date", ""), reverse=True)

    total = len(all_reviews)

    # ── 分页 ──
    start = (page - 1) * page_size
    end = start + page_size
    paginated = all_reviews[start:end]

    logger.info(
        f"合并查询评价: business_id={business_id}, source={source}, "
        f"sort_by={sort_by}, 返回 {len(paginated)}/{total} 条"
    )
    return paginated, total
