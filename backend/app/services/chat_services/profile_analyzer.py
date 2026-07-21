"""Profile analyzer — extracts user preferences from conversation.

Uses LLM to analyze user messages and extract keywords including:
- Location preferences
- Cuisine preferences
- Taste preferences
- Dining scenarios
- Budget level
- Other keywords

The analyzer runs after each conversation turn and updates the user profile.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List

from backend.app.services.llm_client import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


PROFILE_ANALYSIS_SYSTEM_PROMPT = """你是一个用户画像分析助手，负责从用户的对话内容中提取关键信息。

你需要分析用户的对话内容，提取以下维度的信息：
1. **地区偏好**：用户提到的城市或地区（如：北京、上海、成都等）
2. **菜系偏好**：用户提到的菜系类型（如：川菜、粤菜、日料、火锅等）
3. **口味偏好**：用户提到的口味特征（如：辣、清淡、甜、酸等）
4. **用餐场景**：用户提到的用餐场景（如：约会、聚会、商务、一人食等）
5. **预算水平**：用户提到的预算偏好（如：经济实惠、中档、高端）
6. **其他关键词**：用户提到的其他特征（如：环境、服务、停车等）

重要规则：
- 只提取用户明确表达的信息，不要推测或猜测
- 如果某个维度没有提及，输出空列表或 null
- 如果用户明确表示不喜欢某个特征，在 "remove_keywords" 字段中列出
- 输出格式必须是 JSON 对象，不要包含其他内容"""

PROFILE_ANALYSIS_USER_PROMPT_TEMPLATE = """请分析以下对话内容，提取用户画像信息。

对话内容：
用户：{user_message}
助手：{assistant_message}

请输出 JSON 格式的分析结果，包含以下字段：
- "locations": 地区列表（如 ["北京", "成都"]）
- "cuisine_preferences": 菜系偏好列表（如 ["川菜", "火锅"]）
- "taste_preferences": 口味偏好列表（如 ["辣", "香"]）
- "dining_scenarios": 用餐场景列表（如 ["约会", "聚会"]）
- "budget_level": 预算水平（"经济实惠" / "中档" / "高端" / null）
- "other_keywords": 其他关键词列表
- "remove_keywords": 需要从用户画像中移除的关键词列表（用户明确表示不喜欢的）

只输出 JSON 对象，不要包含其他内容。"""


async def analyze_conversation_for_profile(
    user_message: str,
    assistant_message: str,
) -> Dict[str, Any]:
    """Analyze conversation to extract user profile keywords.
    
    Args:
        user_message: User's message
        assistant_message: Assistant's response
    
    Returns:
        Dictionary with extracted profile data:
        {
            "locations": List[str],
            "cuisine_preferences": List[str],
            "taste_preferences": List[str],
            "dining_scenarios": List[str],
            "budget_level": Optional[str],
            "other_keywords": List[str],
            "remove_keywords": List[str],
        }
    """
    fallback = {
        "locations": [],
        "cuisine_preferences": [],
        "taste_preferences": [],
        "dining_scenarios": [],
        "budget_level": None,
        "other_keywords": [],
        "remove_keywords": [],
    }
    
    try:
        llm = get_llm()
        
        prompt = PROFILE_ANALYSIS_USER_PROMPT_TEMPLATE.format(
            user_message=user_message,
            assistant_message=assistant_message,
        )
        
        messages = [
            SystemMessage(content=PROFILE_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        
        logger.info(f"Analyzing conversation for profile extraction")
        response = await llm.ainvoke(messages)
        content = response.content or ""
        
        # Parse JSON from response (handle markdown fences)
        content = content.strip()
        if content.startswith("```"):
            # Remove ```json or ``` fences
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        
        result = json.loads(content)
        
        # Validate and normalize
        return {
            "locations": _normalize_list(result.get("locations", [])),
            "cuisine_preferences": _normalize_list(result.get("cuisine_preferences", [])),
            "taste_preferences": _normalize_list(result.get("taste_preferences", [])),
            "dining_scenarios": _normalize_list(result.get("dining_scenarios", [])),
            "budget_level": _normalize_budget(result.get("budget_level")),
            "other_keywords": _normalize_list(result.get("other_keywords", [])),
            "remove_keywords": _normalize_list(result.get("remove_keywords", [])),
        }
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse profile analysis JSON: {e}")
        return fallback
    except Exception as e:
        logger.error(f"Profile analysis failed: {e}")
        return fallback


def _normalize_list(value: Any) -> List[str]:
    """Ensure value is a list of non-empty strings."""
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if v and str(v).strip()]


def _normalize_budget(value: Any) -> Optional[str]:
    """Normalize budget level."""
    if not value:
        return None
    
    budget = str(value).strip()
    valid_budgets = ["经济实惠", "中档", "高端"]
    
    # Map common variations
    budget_mapping = {
        "便宜": "经济实惠",
        "实惠": "经济实惠",
        "经济": "经济实惠",
        "中等": "中档",
        "适中": "中档",
        "贵": "高端",
        "高档": "高端",
        "奢华": "高端",
        "奢侈": "高端",
    }
    
    if budget in valid_budgets:
        return budget
    
    return budget_mapping.get(budget)