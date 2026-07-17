"""性能优化查询函数

提供高效的商家查询接口，避免O(n^2)查询复杂度
"""
import logging
import sys
from pathlib import Path
from typing import List, Dict

# 添加 base_config 到路径
BASE_CONFIG_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent / "base_config"
if str(BASE_CONFIG_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_CONFIG_ROOT))

from opensearch_client import get_opensearch_client
from app.core.config import settings

logger = logging.getLogger(__name__)


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