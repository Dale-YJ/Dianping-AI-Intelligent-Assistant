"""评价分析 API 路由

对应接口文档模块 C：评价智能理解
- C.1 评价智能总结 (US-2.1 + US-2.2)
- C.2 评价列表（含情感筛选）
- C.3 单条评价详情
- B.1 商家列表
- B.2 商家详情
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.services.analysis_services.summary import generate_summary
from app.services.analysis_services.retrieval import (
    get_business_by_id,
    get_all_businesses,
    vector_search_reviews,
    search_businesses_local,
    get_businesses_with_reviews,  # 新增：高效查询函数
)

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


# ── B.1 商家列表 ────────────────────────────────────────

@router.get("/businesses")
async def api_businesses(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
    keyword: str = Query("", description="关键词搜索"),
    category: str = Query("", description="分类筛选"),
    min_rating: float = Query(0, ge=0, le=5, description="最低评分"),
    sort_by: str = Query("rating", pattern="^(rating|review_count)$", description="排序字段"),
):
    """商家列表"""
    try:
        items, total = search_businesses_local(
            keyword=keyword,
            category=category,
            min_rating=min_rating,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
        )

        # 格式化输出
        formatted_items = []
        for biz in items:
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
        logger.error(f"商家列表查询失败: {e}")
        return make_response(500, message=str(e))


# ── B.1.1 高效商家列表（仅返回有评价的商家）────────────────

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
    logger.info(f"🔥 api_businesses_with_reviews 被调用: page={page}, page_size={page_size}, min_reviews={min_reviews}")
    try:
        logger.info(f"开始调用 get_businesses_with_reviews...")
        items, total = get_businesses_with_reviews(
            keyword=keyword,
            category=category,
            min_rating=min_rating,
            min_reviews=min_reviews,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
        )
        logger.info(f"✅ 查询成功: total={total}, items={len(items)}")

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


# ── B.2 商家详情 ────────────────────────────────────────

@router.get("/businesses/{business_id}")
async def api_business_detail(business_id: str):
    """商家详情"""
    try:
        biz = get_business_by_id(business_id)
        if not biz:
            return make_response(404, message="商家不存在")

        photos = biz.get("photos") if isinstance(biz.get("photos"), list) else []
        if not photos and biz.get("image_url"):
            photos = [biz["image_url"]]
        return make_response(0, {
            "business_id": biz.get("business_id", ""),
            "name": biz.get("name", ""),
            "address": f"{biz.get('address', '')}, {biz.get('city', '')}, {biz.get('state', '')} {biz.get('postal_code', '')}",
            "latitude": biz.get("latitude", 0),
            "longitude": biz.get("longitude", 0),
            "rating": biz.get("stars", 0),
            "review_count": biz.get("review_count", 0),
            "categories": biz.get("categories", "").split(", ") if biz.get("categories") else [],
            "hours": biz.get("hours", {}),
            "attributes": biz.get("attributes", {}),
            "photos": photos,
        })
    except Exception as e:
        logger.error(f"商家详情查询失败: {e}")
        return make_response(500, message=str(e))


# ── C.1 评价智能总结 ────────────────────────────────────

@router.get("/businesses/{business_id}/summary")
async def api_summary(
    business_id: str,
    force: bool = Query(False, description="是否强制刷新缓存"),
):
    """评价智能总结

    对应 US-2.1 + US-2.2（溯源）

    返回商家的 AI 口碑摘要（好评亮点 + 差评槽点 + 近期动态）
    """
    try:
        # 使用异步函数
        result = await generate_summary(business_id, force_refresh=force)

        if "error" in result:
            code = result.get("code", 500)
            return make_response(code, message=result["error"])

        return make_response(0, result)
    except Exception as e:
        logger.error(f"摘要生成失败: {e}")
        return make_response(500, message=str(e))


# ── C.2 评价列表 ──────────────────────────────────────────

@router.get("/businesses/{business_id}/reviews")
async def api_reviews(
    business_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    min_rating: int = Query(0, ge=0, le=5),
    sort_by: str = Query("date", pattern="^(date|rating|useful)$"),
):
    """评价列表（含情感筛选）"""
    try:
        biz = get_business_by_id(business_id)
        if not biz:
            return make_response(404, message="商家不存在")

        # 使用向量检索获取评价
        reviews = vector_search_reviews(business_id, top_k=1000)

        # 过滤
        if min_rating > 0:
            reviews = [r for r in reviews if r.get("stars", 0) >= min_rating]

        # 排序
        if sort_by == "rating":
            reviews.sort(key=lambda r: r.get("stars", 0), reverse=True)
        elif sort_by == "useful":
            reviews.sort(key=lambda r: r.get("useful", 0), reverse=True)
        else:
            reviews.sort(key=lambda r: r.get("date", ""), reverse=True)

        total = len(reviews)
        start = (page - 1) * page_size
        end = start + page_size
        items = reviews[start:end]

        # 格式化
        formatted_items = []
        for r in items:
            formatted_items.append({
                "review_id": r.get("review_id", ""),
                "user_name": r.get("user_id", "")[:8] + "...",  # 匿名化
                "rating": int(r.get("stars", 3)),
                "text": r.get("text", ""),
                "date": r.get("date", "")[:10],
                "useful": r.get("useful", 0),
                "funny": r.get("funny", 0),
                "cool": r.get("cool", 0),
            })

        return make_response(0, {
            "business_id": business_id,
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": formatted_items,
        })
    except Exception as e:
        logger.error(f"评价列表查询失败: {e}")
        return make_response(500, message=str(e))


# ── C.3 单条评价详情 ─────────────────────────────────────

@router.get("/reviews/{review_id}")
async def api_review_detail(review_id: str):
    """单条评价详情（用于溯源弹窗）"""
    # 遍历所有评价查找
    all_businesses = get_all_businesses()
    for biz in all_businesses:
        reviews = vector_search_reviews(biz.get("business_id", ""), top_k=100)
        for r in reviews:
            if r.get("review_id") == review_id:
                return make_response(0, {
                    "review_id": r.get("review_id", ""),
                    "business_id": biz.get("business_id", ""),
                    "business_name": biz.get("name", ""),
                    "user_name": r.get("user_id", "")[:8] + "...",
                    "rating": int(r.get("stars", 3)),
                    "text": r.get("text", ""),
                    "date": r.get("date", "")[:10],
                    "useful": r.get("useful", 0),
                    "funny": r.get("funny", 0),
                    "cool": r.get("cool", 0),
                })

    return make_response(404, message="评价不存在")