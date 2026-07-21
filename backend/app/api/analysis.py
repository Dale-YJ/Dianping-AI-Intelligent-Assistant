"""评价分析 API 路由

对应接口文档模块 C：评价智能理解
- C.1 评价智能总结 (US-2.1 + US-2.2)
- C.2 评价列表（含情感筛选）
- C.3 单条评价详情
- B.1 商家列表
- B.2 商家详情
- C.4 创建用户评价 (NEW)
- C.5 修改用户评价 (NEW)
- C.6 删除用户评价 (NEW)
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Query, Body

from app.services.analysis_services.summary import generate_summary
from app.services.analysis_services.retrieval import (
    get_business_by_id,
    get_all_businesses,
    vector_search_reviews,
    search_businesses_local,
    get_businesses_with_reviews,  # 高效查询函数
)
from app.services.analysis_services.review_service import (
    create_review,
    update_review,
    delete_review,
    get_user_review,
    get_all_reviews_merged,
)
from app.schemas.analysis_schemas.review_schemas import ReviewCreate, ReviewUpdate

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
    source: str = Query("all", pattern="^(all|user|ingested)$", description="评价来源: all/user/ingested"),
):
    """评价列表（含用户评价与预导入评价）

    合并查询 user_review（用户提交）和 yelp_review（预导入）两个索引。
    """
    try:
        biz = get_business_by_id(business_id)
        if not biz:
            return make_response(404, message="商家不存在")

        items, total = get_all_reviews_merged(
            business_id=business_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            min_rating=min_rating,
            source=source,
        )

        return make_response(0, {
            "business_id": business_id,
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        })
    except Exception as e:
        logger.error(f"评价列表查询失败: {e}")
        return make_response(500, message=str(e))


# ── C.3 单条评价详情 ─────────────────────────────────────

@router.get("/reviews/{review_id}")
async def api_review_detail(review_id: str):
    """单条评价详情（用于溯源弹窗）

    优先查询 user_review 索引，未找到再查询 yelp_review 索引。
    """
    try:
        # 优先查询用户评价
        user_review = get_user_review(review_id)
        if user_review:
            return make_response(0, {
                "review_id": user_review.get("review_id", ""),
                "business_id": user_review.get("business_id", ""),
                "user_name": user_review.get("user_name", "匿名用户"),
                "rating": int(user_review.get("rating", 3)),
                "text": user_review.get("text", ""),
                "date": (user_review.get("created_at", "") or "")[:10],
                "useful": 0,
                "funny": 0,
                "cool": 0,
                "source": "user",
            })

        # 回退查询预导入评价（遍历现有逻辑）
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
                        "source": "ingested",
                    })

        return make_response(404, message="评价不存在")
    except Exception as e:
        logger.error(f"评价详情查询失败: {e}")
        return make_response(500, message=str(e))


# ── C.4 创建用户评价 ─────────────────────────────────────

@router.post("/businesses/{business_id}/reviews")
async def api_create_review(
    business_id: str,
    body: ReviewCreate = Body(..., description="评价内容"),
):
    """创建用户评价

    提交对指定商家的星级评分与文字评价，无需审核即展示。
    """
    try:
        # 验证商家是否存在
        biz = get_business_by_id(business_id)
        if not biz:
            return make_response(404, message="商家不存在")

        review = create_review(
            business_id=business_id,
            user_name=body.user_name,
            rating=body.rating,
            text=body.text,
        )

        return make_response(0, {
            "review_id": review["review_id"],
            "business_id": review["business_id"],
            "user_name": review["user_name"],
            "rating": review["rating"],
            "text": review["text"],
            "date": review["created_at"][:10],
            "source": "user",
        }, message="评价发布成功")
    except Exception as e:
        logger.error(f"创建评价失败: {e}")
        return make_response(500, message=str(e))


# ── C.5 修改用户评价 ─────────────────────────────────────

@router.put("/reviews/{review_id}")
async def api_update_review(
    review_id: str,
    body: ReviewUpdate = Body(..., description="要修改的字段"),
):
    """修改用户评价

    仅允许修改 user_review 索引中的用户评价。
    未传入的字段保持不变，至少需要提供一个字段。
    """
    try:
        if body.rating is None and body.text is None:
            return make_response(400, message="至少需要提供 rating 或 text 字段")

        updated = update_review(
            review_id=review_id,
            rating=body.rating,
            text=body.text,
        )

        if not updated:
            return make_response(404, message="评价不存在（仅支持修改用户提交的评价）")

        return make_response(0, {
            "review_id": updated["review_id"],
            "business_id": updated["business_id"],
            "user_name": updated["user_name"],
            "rating": updated["rating"],
            "text": updated["text"],
            "date": updated.get("updated_at", "")[:10],
            "source": "user",
        }, message="评价修改成功")
    except Exception as e:
        logger.error(f"修改评价失败: {e}")
        return make_response(500, message=str(e))


# ── C.6 删除用户评价 ─────────────────────────────────────

@router.delete("/reviews/{review_id}")
async def api_delete_review(review_id: str):
    """删除用户评价

    仅允许删除 user_review 索引中的用户评价。
    """
    try:
        deleted = delete_review(review_id)

        if not deleted:
            return make_response(404, message="评价不存在（仅支持删除用户提交的评价）")

        return make_response(0, {"review_id": review_id}, message="评价删除成功")
    except Exception as e:
        logger.error(f"删除评价失败: {e}")
        return make_response(500, message=str(e))