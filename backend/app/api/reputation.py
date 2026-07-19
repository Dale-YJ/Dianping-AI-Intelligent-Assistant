"""商家口碑分析 API 路由

功能点：
1. 关键特征词提取
2. 评价情感分析
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.services.reputation_services.keyword_extraction import extract_keywords
from app.services.reputation_services.sentiment_analysis import analyze_sentiment
from app.services.reputation_services.optimized_queries import get_businesses_with_reviews

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


def make_response(code: int, data=None, message: str = "success", request_id: str = "") -> dict:
    """构建标准响应"""
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": request_id or str(uuid.uuid4()),
    }


# ── D.1 关键特征词提取 ─────────────────────────────────────

@router.get("/businesses/{business_id}/keywords")
async def api_extract_keywords(
    business_id: str,
):
    """关键特征词提取

    从商家评价中提取关键词标签，按菜品/环境/服务/价格分类

    Returns:
        {
            "business_id": "商家ID",
            "business_name": "商家名称",
            "total_reviews_analyzed": 分析的评价数,
            "total_keywords": 关键词总数,
            "keyword_groups": [
                {
                    "dimension": "dish",
                    "label": "菜品相关",
                    "icon": "🍽️",
                    "tags": [
                        {
                            "keyword": "关键词",
                            "count": 提及次数,
                            "score": 重要性分数,
                            "dimension": "dish",
                            "sentiment": "positive/negative/neutral"
                        }
                    ]
                }
            ]
        }
    """
    try:
        result = await extract_keywords(business_id)

        if "error" in result:
            code = result.get("code", 500)
            return make_response(code, message=result["error"])

        return make_response(0, result)

    except Exception as e:
        logger.error(f"关键词提取失败: {e}")
        return make_response(500, message=str(e))


# ── D.2 评价情感分析 ───────────────────────────────────────

@router.get("/businesses/{business_id}/sentiment")
async def api_analyze_sentiment(
    business_id: str,
    min_rating: int = Query(0, ge=0, le=5, description="最低评分筛选"),
    sentiment: Optional[str] = Query(None, description="情感筛选: positive/neutral/negative"),
):
    """评价情感分析

    分析商家评价的情感倾向，支持按情感筛选

    Returns:
        {
            "business_id": "商家ID",
            "business_name": "商家名称",
            "total_reviews": 评价总数,
            "sentiment_stats": {
                "total_reviews": 总数,
                "positive_count": 正面数量,
                "neutral_count": 中性数量,
                "negative_count": 负面数量,
                "positive_ratio": 正面占比,
                "neutral_ratio": 中性占比,
                "negative_ratio": 负面占比
            },
            "reviews": [
                {
                    "review_id": "评价ID",
                    "user_name": "用户名",
                    "rating": 评分,
                    "text": "评价内容",
                    "date": "日期",
                    "useful": 有用数,
                    "funny": 有趣数,
                    "cool": 酷数,
                    "sentiment": {
                        "label": "positive/neutral/negative",
                        "label_cn": "正面/中性/负面",
                        "icon": "😊/😐/😞",
                        "confidence": 置信度
                    }
                }
            ]
        }
    """
    try:
        result = await analyze_sentiment(
            business_id,
            min_rating=min_rating,
            sentiment_filter=sentiment
        )

        if "error" in result:
            code = result.get("code", 500)
            return make_response(code, message=result["error"])

        return make_response(0, result)

    except Exception as e:
        logger.error(f"情感分析失败: {e}")
        return make_response(500, message=str(e))


# ── D.3 高效商家列表（仅返回有评价的商家）────────────────

@router.get("/businesses/with-reviews")
async def api_businesses_with_reviews(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=10000, description="每页数量（最大10000）"),
    keyword: str = Query("", description="关键词搜索"),
    category: str = Query("", description="分类筛选"),
    min_rating: float = Query(0, ge=0, le=5, description="最低评分"),
    min_reviews: int = Query(1, ge=1, description="最低评价数量"),
    sort_by: str = Query("rating", pattern="^(rating|review_count)$", description="排序字段"),
):
    """高效商家列表（仅返回有评价的商家）
    
    性能优化：
    - 旧方法：O(n) - 每个商家发一次请求
    - 新方法：O(1) - 只发2次请求（聚合+批量查询）
    
    适用于前端加载大量商家时使用，避免页面崩溃
    """
    try:
        items, total = get_businesses_with_reviews(
            keyword=keyword,
            category=category,
            min_rating=min_rating,
            min_reviews=min_reviews,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
        )

        # 格式化输出
        formatted_items = []
        for biz in items:
            # 国内数据有 image_url，Yelp 数据没有
            photos = biz.get("photos") if isinstance(biz.get("photos"), list) else []
            if not photos and biz.get("image_url"):
                photos = [biz["image_url"]]
            formatted_items.append({
                "business_id": biz.get("business_id", ""),
                "name": biz.get("name", ""),
                "address": f"{biz.get('address', '')}, {biz.get('city', '')}, {biz.get('state', '')} {biz.get('postal_code', '')}",
                "city": biz.get("city", ""),
                "state": biz.get("state", ""),
                "latitude": biz.get("latitude", 0),
                "longitude": biz.get("longitude", 0),
                "rating": biz.get("stars", 0),
                "review_count": biz.get("review_count", 0),
                "real_review_count": biz.get("real_review_count", 0),
                "categories": biz.get("categories", "").split(", ") if biz.get("categories") else [],
                "photos": photos,
            })

        return make_response(0, {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": formatted_items,
        })
    except Exception as e:
        logger.error(f"高效商家列表查询失败: {e}")
        return make_response(500, message=str(e))