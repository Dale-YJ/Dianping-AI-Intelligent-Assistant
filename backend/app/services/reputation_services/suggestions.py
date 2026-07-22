"""经营建议生成服务

对应 C.7：GET /api/v1/businesses/{id}/suggestions

功能：
1. 获取该商家的正面评价（≥4 星）和负面评价（≤2 星）
2. 调用 LLM 基于评价数据生成 4 条具体的经营改进建议
3. 每条建议包含：优先级、问题描述、具体措施、预期效果
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

REVIEW_INDICES = "yelp_review,user_review"


def _fetch_reviews_for_suggestions(
    business_id: str,
    top_k: int = 40,
) -> Dict[str, List[Dict[str, Any]]]:
    """查询商家评价，分为好评和差评两组

    Args:
        business_id: 商家 ID
        top_k: 每组最多返回条数

    Returns:
        {"positive": [...], "negative": [...]}
    """
    client = get_opensearch_client()

    def _query(min_stars: int = None, max_stars: int = None) -> List[dict]:
        body = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"business_id": business_id}},
                    ],
                }
            },
        }
        # 添加评分范围（should 子句兼容不同字段名）
        if min_stars is not None or max_stars is not None:
            range_clauses = []
            range_q = {}
            if min_stars is not None:
                range_q["gte"] = min_stars
            if max_stars is not None:
                range_q["lte"] = max_stars
            if range_q:
                range_clauses.append({"range": {"stars": range_q}})
                range_clauses.append({"range": {"rating": range_q}})
                body["query"]["bool"]["should"] = range_clauses
                body["query"]["bool"]["minimum_should_match"] = 1

        try:
            resp = client.search(index=REVIEW_INDICES, body=body)
        except Exception as e:
            logger.warning(f"查询评价失败: {e}")
            return []

        reviews = []
        for h in resp.get("hits", {}).get("hits", []):
            src = h["_source"]
            reviews.append({
                "review_id": src.get("review_id", ""),
                "stars": int(src.get("stars") or src.get("rating", 0)),
                "text": src.get("text", "")[:300],
                "date": str(src.get("date") or src.get("created_at", ""))[:10],
            })
        return reviews

    positive = _query(min_stars=4)
    negative = _query(max_stars=2)

    return {"positive": positive, "negative": negative}


async def generate_suggestions(business_id: str) -> Dict[str, Any]:
    """生成经营改进建议

    基于正面和负面评价，调用 LLM 生成 4 条具体可落地的经营建议。

    Args:
        business_id: 商家 ID

    Returns:
        {
            "business_id": "...",
            "business_name": "...",
            "suggestions": [
                {"priority": "high", "category": "service", "problem": "...",
                 "action": "...", "expected_effect": "..."},
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
    stars = business.get("stars", "N/A")
    categories = business.get("categories", "")

    # 2. 获取评价
    reviews = _fetch_reviews_for_suggestions(business_id)
    positive_reviews = reviews["positive"]
    negative_reviews = reviews["negative"]

    if not positive_reviews and not negative_reviews:
        return {
            "business_id": business_id,
            "business_name": business_name,
            "note": "暂无足够评价数据生成建议",
            "suggestions": [],
        }

    # 3. 构建 prompt
    pos_texts = []
    for r in positive_reviews[:20]:
        pos_texts.append(f"[{r['stars']}★ | {r['date']}] {r['text']}")

    neg_texts = []
    for r in negative_reviews[:20]:
        neg_texts.append(f"[{r['stars']}★ | {r['date']}] {r['text']}")

    prompt = f"""请基于以下商家的评价数据，生成 4 条具体的经营改进建议。

## 商家信息
- 店名：{business_name}
- 评分：⭐{stars}
- 类别：{categories}

## 好评（{len(positive_reviews)} 条）
{chr(10).join(pos_texts) if pos_texts else "（无好评）"}

## 差评（{len(negative_reviews)} 条）
{chr(10).join(neg_texts) if neg_texts else "（无差评）"}

请生成 4 条建议，返回 JSON：
{{
  "suggestions": [
    {{
      "priority": "high",
      "category": "service",
      "problem": "上菜速度被多位顾客提及",
      "action": "在高峰时段增加 1-2 名后厨人手，优化出餐流程，将热门菜品预先备料",
      "expected_effect": "上菜时间预计缩短 30%，差评中关于速度的投诉可减少 50%"
    }},
    ...
  ]
}}

要求：
1. 必须正好 4 条建议
2. priority 设为 "high" / "medium" / "low"
3. category 设为 "service" / "food" / "environment" / "price" / "other"
4. problem：简要描述发现的问题（引用评价中的现象）
5. action：具体可落地的措施（说怎么做，不是为什么）
6. expected_effect：量化或具体描述预期效果
7. 建议必须基于真实评价数据，不能凭空编造
8. 如果某方面没有负面评价，可以基于好评提炼"如何做得更好"的建议
"""

    # 4. 调用 LLM
    try:
        llm = get_llm()
        messages = [
            SystemMessage(content="你是一个资深的餐饮行业经营顾问，擅长从顾客评价中提炼可落地的改进方案。请只返回 JSON，不要添加额外解释。"),
            HumanMessage(content=prompt),
        ]
        resp = await llm.ainvoke(messages)
        content = resp.content or ""
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        return {"error": f"AI 服务异常: {e}", "code": 1003}

    # 5. 解析
    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        result = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("JSON 解析失败")
        return {"error": "LLM 返回格式异常", "code": 1004, "raw": content[:500]}

    suggestions = result.get("suggestions", [])

    return {
        "business_id": business_id,
        "business_name": business_name,
        "positive_review_count": len(positive_reviews),
        "negative_review_count": len(negative_reviews),
        "suggestions": suggestions[:4],
    }
