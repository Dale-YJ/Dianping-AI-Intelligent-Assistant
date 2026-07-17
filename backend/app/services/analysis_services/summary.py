"""评价智能总结服务

对应 US-2.1 + US-2.2（溯源）
接口: GET /api/v1/businesses/{id}/summary

使用 B 提供的 get_llm 异步客户端。
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from app.services.llm_client import get_llm
from app.services.analysis_services.retrieval import get_business_by_id, vector_search_reviews

logger = logging.getLogger(__name__)

# 摘要缓存（避免重复调用 LLM）
_summary_cache: Dict[str, dict] = {}


async def generate_summary(business_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """生成商家口碑摘要（异步版本）

    Args:
        business_id: 商家ID
        force_refresh: 是否强制刷新缓存

    Returns:
        摘要结果字典
    """
    start_time = time.time()

    # 检查缓存
    if not force_refresh and business_id in _summary_cache:
        logger.info(f"使用缓存摘要: business_id={business_id}")
        return _summary_cache[business_id]

    # 获取商家信息
    business = get_business_by_id(business_id)
    if not business:
        return {"error": "商家不存在", "code": 404}

    business_name = business.get("name", "未知商家")

    # 获取评价（使用向量检索接口）
    reviews = vector_search_reviews(business_id, top_k=30)
    if not reviews:
        return {
            "error": "该商家暂无评价",
            "code": 1001,
            "business_id": business_id,
            "business_name": business_name,
        }

    # 准备评价文本
    review_texts = []
    for r in reviews:
        stars = r.get("stars", 3)
        text = r.get("text", "")[:300]  # 限制长度
        date = r.get("date", "")[:10]
        review_id = r.get("review_id", "")
        user_id = r.get("user_id", "")[:8]
        review_texts.append(f"[{date} | {'★' * int(stars)} | {review_id}] {text}")

    reviews_content = "\n---\n".join(review_texts)

    # 构建 Prompt
    prompt = f"""请根据以下商家的评价数据，生成口碑摘要。

商家名称：{business_name}
评价数量：{len(reviews)} 条

评价内容：
{reviews_content}

请生成 JSON 格式的摘要，包含以下字段：
{{
  "highlights": {{
    "title": "👍 大家普遍推荐",
    "items": [
      {{
        "point": "观点描述",
        "mention_count": 提及次数,
        "sources": [
          {{
            "review_id": "评价ID",
            "user_name": "用户名",
            "date": "日期",
            "snippet": "原文片段",
            "rating": 星级
          }}
        ]
      }}
    ]
  }},
  "concerns": {{
    "title": "⚠️ 大家吐槽较多",
    "items": [...]
  }},
  "recent_trend": {{
    "title": "📊 近期动态",
    "summary": "近期动态描述",
    "period": "时间范围",
    "sources": []
  }}
}}

要求：
1. 摘要内容必须忠实于原始评价，不编造
2. 每个观点需标注 mention_count（提及次数）
3. sources 中填写真实评价的 review_id 和原文片段
4. 如果评价数量较少，在 concerns 中标注"评价数量有限，结论仅供参考"
"""

    # 调用 LLM（使用 B 提供的异步客户端）
    try:
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = get_llm()
        model_name = getattr(llm, "_model_name", "qwen-plus")

        logger.info(f"调用 LLM 生成摘要: model={model_name}, business_id={business_id}")

        # 异步调用 - 使用 LangChain 的正确方式
        messages = [
            SystemMessage(content="你是一个专业的口碑分析助手。请根据评价数据生成准确的口碑摘要。"),
            HumanMessage(content=prompt)
        ]
        response = await llm.ainvoke(messages)
        content = response.content

        # 解析 JSON
        try:
            # 清理可能的 markdown 代码块标记
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"JSON 解析失败，返回原始内容")
            result = {"raw_text": content}

    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        return {"error": f"AI 服务异常: {e}", "code": 1003}

    # 构建响应
    elapsed_ms = int((time.time() - start_time) * 1000)

    response_data = {
        "business_id": business_id,
        "business_name": business_name,
        "generated_at": datetime.now().isoformat(),
        "review_count_used": len(reviews),
        "highlights": result.get("highlights", {"title": "👍 大家普遍推荐", "items": []}),
        "concerns": result.get("concerns", {"title": "⚠️ 大家吐槽较多", "items": []}),
        "recent_trend": result.get("recent_trend", {"title": "📊 近期动态", "summary": "暂无明显动态", "period": ""}),
        "elapsed_ms": elapsed_ms,
    }

    # 缓存结果
    _summary_cache[business_id] = response_data
    logger.info(f"摘要生成完成: business_id={business_id}, elapsed_ms={elapsed_ms}")

    return response_data


def get_cached_summary(business_id: str) -> Optional[Dict[str, Any]]:
    """获取缓存的摘要"""
    return _summary_cache.get(business_id)