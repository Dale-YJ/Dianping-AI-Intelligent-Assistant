"""评价情感分析服务

分析评价的情感倾向（正面/中性/负面）
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# 添加 base_config 到路径
BASE_CONFIG_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent / "base_config"
if str(BASE_CONFIG_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_CONFIG_ROOT))

from opensearch_client import get_opensearch_client
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_client import get_llm
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_business_reviews(business_id: str, top_k: int = 100, min_rating: int = 0) -> List[Dict[str, Any]]:
    """获取商家评价数据

    复用 base_config 的 OpenSearch 客户端
    
    注意：business_id 字段在评价索引中是 text 类型，使用 match 查询
    """
    client = get_opensearch_client()

    query = {
        "size": top_k,
        "query": {
            "bool": {
                "must": [
                    {"match": {"business_id": business_id}}  # 使用 match 查询（text 类型）
                ]
            }
        },
        "_source": ["review_id", "user_id", "stars", "text", "date", "useful", "funny", "cool"]
    }

    # 添加评分筛选
    if min_rating > 0:
        query["query"]["bool"]["must"].append({"range": {"stars": {"gte": min_rating}}})

    response = client.search(index=settings.review_index, body=query)

    reviews = []
    for hit in response["hits"]["hits"]:
        reviews.append(hit["_source"])

    return reviews


def get_business_info(business_id: str) -> Dict[str, Any]:
    """获取商家基本信息
    
    与 analysis 模块保持一致，使用 client.get() 方法通过文档ID查询
    """
    try:
        client = get_opensearch_client()
        
        # 使用 get 方法查询单条数据（与 analysis 模块一致）
        res = client.get(
            index=settings.business_index,
            id=business_id,
            ignore=[404]
        )
        
        if res.get("found", False):
            return res["_source"]
        else:
            return None
            
    except Exception as e:
        logger.error(f"查询商家失败: {e}")
        return None


async def analyze_sentiment(
    business_id: str,
    min_rating: int = 0,
    sentiment_filter: str = None
) -> Dict[str, Any]:
    """分析评价情感倾向

    Args:
        business_id: 商家ID
        min_rating: 最低评分筛选
        sentiment_filter: 情感筛选 (positive/neutral/negative)

    Returns:
        情感分析结果
    """
    # 获取商家信息
    business = get_business_info(business_id)
    if not business:
        return {
            "error": "商家不存在",
            "code": 404
        }

    business_name = business.get("name", "未知商家")

    # 获取评价
    reviews = get_business_reviews(business_id, top_k=100, min_rating=min_rating)

    if not reviews:
        return {
            "error": "该商家暂无评价",
            "code": 1001,
            "business_id": business_id,
            "business_name": business_name,
        }

    # 批量分析情感（每批10条）
    sentiment_results = []

    for i in range(0, min(len(reviews), 50), 10):  # 最多分析50条
        batch = reviews[i:i+10]
        batch_results = await _analyze_batch_sentiment(batch)
        sentiment_results.extend(batch_results)

    # 统计情感分布
    positive_count = sum(1 for r in sentiment_results if r["sentiment"]["label"] == "positive")
    neutral_count = sum(1 for r in sentiment_results if r["sentiment"]["label"] == "neutral")
    negative_count = sum(1 for r in sentiment_results if r["sentiment"]["label"] == "negative")
    total = len(sentiment_results)

    # 应用情感筛选
    if sentiment_filter:
        sentiment_results = [
            r for r in sentiment_results
            if r["sentiment"]["label"] == sentiment_filter
        ]

    return {
        "business_id": business_id,
        "business_name": business_name,
        "total_reviews": total,
        "sentiment_stats": {
            "total_reviews": total,
            "positive_count": positive_count,
            "neutral_count": neutral_count,
            "negative_count": negative_count,
            "positive_ratio": round(positive_count / total, 2) if total > 0 else 0.0,
            "neutral_ratio": round(neutral_count / total, 2) if total > 0 else 0.0,
            "negative_ratio": round(negative_count / total, 2) if total > 0 else 0.0,
        },
        "reviews": sentiment_results,
        "generated_at": datetime.now().isoformat(),
    }


async def _analyze_batch_sentiment(reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量分析评价情感

    Args:
        reviews: 评价列表（最多10条）

    Returns:
        带情感分析结果的评价列表
    """
    # 准备评价文本
    reviews_data = []
    for r in reviews:
        reviews_data.append({
            "review_id": r.get("review_id", ""),
            "user_id": r.get("user_id", "")[:8],
            "stars": r.get("stars", 3),
            "text": r.get("text", "")[:150],
            "date": r.get("date", "")[:10],
            "useful": r.get("useful", 0),
            "funny": r.get("funny", 0),
            "cool": r.get("cool", 0),
        })

    # 构建提示词
    prompt = f"""请分析以下评价的情感倾向。

评价列表：
{json.dumps(reviews_data, ensure_ascii=False, indent=2)}

请为每条评价标注情感倾向：
- positive: 正面评价（满意、赞扬）
- neutral: 中性评价（客观描述、无明显倾向）
- negative: 负面评价（不满、批评）

返回JSON数组，每个元素包含：
- review_id: 评价ID
- sentiment: 情感分析结果
  - label: positive/neutral/negative
  - label_cn: 正面/中性/负面
  - icon: 😊/😐/😞
  - confidence: 置信度(0-1)

示例：
[
  {{
    "review_id": "xxx",
    "sentiment": {{
      "label": "positive",
      "label_cn": "正面",
      "icon": "😊",
      "confidence": 0.85
    }}
  }}
]
"""

    try:
        llm = get_llm()

        messages = [
            SystemMessage(content="你是一个专业的情感分析助手，擅长分析文本情感倾向。"),
            HumanMessage(content=prompt)
        ]

        response = await llm.ainvoke(messages)
        content = response.content

        # 解析 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        sentiment_data = json.loads(content)

        # 合并结果
        results = []
        for sentiment_item in sentiment_data:
            review_id = sentiment_item.get("review_id")

            # 找到对应的评价
            review_data = next((r for r in reviews_data if r["review_id"] == review_id), None)
            if not review_data:
                continue

            results.append({
                "review_id": review_id,
                "user_name": review_data["user_id"] + "...",
                "rating": review_data["stars"],
                "text": review_data["text"],
                "date": review_data["date"],
                "useful": review_data["useful"],
                "funny": review_data["funny"],
                "cool": review_data["cool"],
                "sentiment": sentiment_item.get("sentiment", {
                    "label": "neutral",
                    "label_cn": "中性",
                    "icon": "😐",
                    "confidence": 0.5
                })
            })

        return results

    except Exception as e:
        logger.error(f"情感分析失败: {e}")

        # 返回默认结果
        results = []
        for r in reviews_data:
            results.append({
                "review_id": r["review_id"],
                "user_name": r["user_id"] + "...",
                "rating": r["stars"],
                "text": r["text"],
                "date": r["date"],
                "useful": r["useful"],
                "funny": r["funny"],
                "cool": r["cool"],
                "sentiment": {
                    "label": "neutral",
                    "label_cn": "中性",
                    "icon": "😐",
                    "confidence": 0.5
                }
            })

        return results