"""关键特征词提取服务

从商家评价中提取关键词标签，按维度分类
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


def get_business_reviews(business_id: str, top_k: int = 100) -> List[Dict[str, Any]]:
    """获取商家评价数据

    复用 base_config 的 OpenSearch 客户端
    
    注意：business_id 字段在评价索引中是 text 类型，使用 match 查询
    """
    client = get_opensearch_client()

    query = {
        "size": top_k,
        "query": {
            "match": {  # 使用 match 查询（text 类型）
                "business_id": business_id
            }
        },
        "_source": ["review_id", "user_id", "stars", "text", "date", "useful", "funny", "cool"]
    }

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


async def extract_keywords(business_id: str) -> Dict[str, Any]:
    """提取商家关键特征词

    Args:
        business_id: 商家ID

    Returns:
        关键词提取结果
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
    reviews = get_business_reviews(business_id, top_k=100)

    if len(reviews) < 3:
        return {
            "error": "评价数量不足3条，无法提取有效特征词",
            "code": 1002,
            "business_id": business_id,
            "business_name": business_name,
        }

    # 准备评价文本
    review_texts = []
    for r in reviews[:50]:  # 最多分析50条评价
        stars = r.get("stars", 3)
        text = r.get("text", "")[:200]  # 限制长度
        review_texts.append(f"[{'★' * int(stars)}] {text}")

    reviews_content = "\n---\n".join(review_texts)

    # 构建提示词
    prompt = f"""请分析以下商家评价，提取关键特征词标签。

商家名称：{business_name}
评价数量：{len(reviews)} 条

评价内容：
{reviews_content}

请提取关键词标签，并按以下维度分类：

1. 🍽️ 菜品相关：招牌菜名、口味描述、菜品质量
2. 🏠 环境相关：安静、嘈杂、装修、卫生、氛围
3. 👨‍🍳 服务相关：态度、上菜速度、专业度、响应
4. 💰 价格相关：实惠、偏贵、性价比、分量

要求：
1. 每个关键词标注提及次数（estimate_count）和情感倾向（positive/negative/neutral）
2. 按提及频次降序排列
3. 只提取真实出现在评价中的关键词，不要编造
4. 返回JSON格式：

{{
  "dish": [
    {{
      "keyword": "关键词",
      "count": 提及次数,
      "sentiment": "positive/negative/neutral",
      "score": 重要性分数(0-1)
    }}
  ],
  "environment": [...],
  "service": [...],
  "price": [...]
}}
"""

    try:
        # 调用 LLM
        llm = get_llm()
        logger.info(f"调用 LLM 提取关键词: business_id={business_id}")

        messages = [
            SystemMessage(content="你是一个专业的口碑分析助手，擅长从评价中提取关键特征词。"),
            HumanMessage(content=prompt)
        ]

        response = await llm.ainvoke(messages)
        content = response.content

        # 解析 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)

        # 构建响应
        dimension_config = {
            "dish": {"label": "菜品相关", "icon": "🍽️"},
            "environment": {"label": "环境相关", "icon": "🏠"},
            "service": {"label": "服务相关", "icon": "👨‍🍳"},
            "price": {"label": "价格相关", "icon": "💰"},
        }

        keyword_groups = []
        total_keywords = 0

        for dimension, keywords in result.items():
            if dimension not in dimension_config:
                continue

            config = dimension_config[dimension]
            tags = []

            for kw in keywords[:10]:  # 每个维度最多10个关键词
                tags.append({
                    "keyword": kw.get("keyword", ""),
                    "count": kw.get("count", 0),
                    "score": kw.get("score", 0.0),
                    "dimension": dimension,
                    "sentiment": kw.get("sentiment", None)
                })
                total_keywords += 1

            keyword_groups.append({
                "dimension": dimension,
                "label": config["label"],
                "icon": config["icon"],
                "tags": sorted(tags, key=lambda x: x["count"], reverse=True)
            })

        return {
            "business_id": business_id,
            "business_name": business_name,
            "total_reviews_analyzed": len(reviews),
            "total_keywords": total_keywords,
            "keyword_groups": keyword_groups,
            "generated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"关键词提取失败: {e}")
        return {
            "error": f"AI 服务异常: {e}",
            "code": 1003
        }