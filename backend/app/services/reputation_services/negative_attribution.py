"""差评归因分析服务

对应 C.6：GET /api/v1/businesses/{id}/negative-attribution

功能：
1. 查询该商家的低分评价（stars <= 2）
2. 用 LLM 按维度分类差评原因：food/service/environment/price/other
3. 统计每个维度的提及次数、占比、代表样例
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

BASE_CONFIG_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent / "base_config"
if str(BASE_CONFIG_ROOT) not in sys.path:
    sys.path.insert(0, str(BASE_CONFIG_ROOT))

from opensearch_client import get_opensearch_client
from langchain_core.messages import SystemMessage, HumanMessage

from app.services.llm_client import get_llm
from app.core.config import settings

logger = logging.getLogger(__name__)

# 跨索引查询：同时搜索 yelp 预导入数据 + 用户提交数据
REVIEW_INDICES = "yelp_review,user_review"


def _fetch_low_star_reviews(business_id: str, max_stars: int = 2, top_k: int = 50) -> List[Dict[str, Any]]:
    """查询低分评价（跨 yelp_review + user_review 两个索引）

    Args:
        business_id: 商家 ID
        max_stars: 最高评分（含），≤此值的评价被视为低分
        top_k: 最多返回条数

    Returns:
        低分评价列表，已处理字段名差异（stars/rating, date/created_at）
    """
    client = get_opensearch_client()

    # 跨索引查询：match 兼容 yelp_review(text) 和 user_review(keyword) 两种类型
    body = {
        "size": top_k,
        "query": {
            "bool": {
                "must": [
                    {"match": {"business_id": business_id}},
                ],
                # 低分筛选：yelp_review 用 stars，user_review 用 rating
                # OpenSearch 对不存在的字段会跳过该文档，所以用 should + minimum_should_match
                "should": [
                    {"range": {"stars": {"lte": max_stars}}},
                    {"range": {"rating": {"lte": max_stars}}},
                ],
                "minimum_should_match": 1,
            }
        },
        # 无 sort 子句：跨索引无公共数值排序字段
    }

    try:
        resp = client.search(index=REVIEW_INDICES, body=body)
    except Exception as e:
        logger.error(f"查询低分评价失败: {e}")
        return []

    reviews = []
    for h in resp.get("hits", {}).get("hits", []):
        src = h["_source"]
        reviews.append({
            "review_id": src.get("review_id", ""),
            "user_id": str(src.get("user_id", ""))[:8],
            "stars": src.get("stars") or src.get("rating", 0),
            "text": src.get("text", "")[:300],
            "date": str(src.get("date") or src.get("created_at", ""))[:10],
        })

    return reviews


async def analyze_negative_attribution(
    business_id: str,
    min_count: int = 3,
) -> Dict[str, Any]:
    """差评归因分析

    查询商家低分评价，用 LLM 按维度分类差评原因。

    Args:
        business_id: 商家 ID
        min_count: 最少评价数阈值，不足时返回提示

    Returns:
        {
            "business_id": "...",
            "total_negative": N,
            "dimensions": [
                {"dimension": "service", "label": "服务", "count": 8, "ratio": 0.53,
                 "examples": ["上菜太慢...", "..."]},
                ...
            ]
        }
    """
    # 1. 获取商家信息
    from app.services.reputation_services.sentiment_analysis import get_business_info
    business = get_business_info(business_id)
    if not business:
        return {"error": "商家不存在", "code": 404}

    business_name = business.get("name", "未知商家")

    # 2. 获取低分评价
    reviews = _fetch_low_star_reviews(business_id, max_stars=2, top_k=50)

    if len(reviews) < min_count:
        return {
            "business_id": business_id,
            "business_name": business_name,
            "total_negative": len(reviews),
            "min_count": min_count,
            "note": f"低分评价数量不足（当前 {len(reviews)} 条，最低要求 {min_count} 条），结论仅供参考",
            "dimensions": [],
        }

    # 3. 构建 LLM prompt
    review_texts = []
    for r in reviews:
        review_texts.append(
            f"[{r['stars']}★ | {r['date']} | {r['review_id']}] {r['text']}"
        )

    prompt = f"""请分析以下商家的差评数据，按维度归因问题。

商家：{business_name}
低分评价数：{len(reviews)} 条

差评内容：
{chr(10).join(review_texts)}

请将每条差评归因到以下维度（一条评价可归入多个维度）：
- food：口味/菜品相关（难吃、份量少、菜品不符等）
- service：服务相关（态度差、上菜慢、响应慢等）
- environment：环境相关（吵闹、脏乱、装修差等）
- price：价格相关（贵、性价比低、隐形消费等）
- other：其他

返回 JSON 格式：
{{
  "dimensions": [
    {{
      "dimension": "service",
      "label": "服务",
      "count": 8,
      "examples": ["原文片段1", "原文片段2", "原文片段3"]
    }},
    ...
  ]
}}

要求：
1. 只返回提及 >= 2 次的维度，按 count 降序排列
2. examples 从原文中摘取最典型的评价片段（最多 3 条，每条 ≤ 80 字）
3. count 等于归入该维度的评价数量
"""

    # 4. 调用 LLM
    try:
        llm = get_llm()
        messages = [
            SystemMessage(content="你是一个专业的餐厅口碑分析专家，擅长从差评中提炼归因维度。请只返回 JSON，不要添加额外解释。"),
            HumanMessage(content=prompt),
        ]
        resp = await llm.ainvoke(messages)
        content = resp.content or ""
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        return {"error": f"AI 服务异常: {e}", "code": 1003}

    # 5. 解析结果
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        result = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("JSON 解析失败")
        return {"error": "LLM 返回格式异常", "code": 1004, "raw": content[:500]}

    # 6. 计算占比
    dimensions = result.get("dimensions", [])
    total = len(reviews)
    for dim in dimensions:
        dim["ratio"] = round(dim["count"] / total, 2)

    return {
        "business_id": business_id,
        "business_name": business_name,
        "total_negative": total,
        "dimensions": dimensions,
    }
