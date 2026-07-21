"""Prompt engineering module.

Defines system prompts, fallback messages, and prompt builders used by the RAG
pipeline.  The prompts are designed with **proactive information gathering** in
mind — the LLM will ask clarifying questions when user input is vague and
extract structured search requirements from the conversation.
"""

from __future__ import annotations

# 统一使用 base_config 的 OpenSearch 客户端
from opensearch_client import get_opensearch_client

REVIEW_INDEX = "yelp_review"


def _fetch_reviews(business_id: str, top_k: int = 3) -> list[dict]:
    """按 business_id 查评价，按 useful 降序。"""
    client = get_opensearch_client()
    if not client.indices.exists(index=REVIEW_INDEX):
        return []
    body = {
        "size": top_k,
        "query": {"bool": {"must": [{"term": {"business_id": business_id}}]}},
        "sort": [{"useful": {"order": "desc"}}],
    }
    try:
        resp = client.search(index=REVIEW_INDEX, body=body)
    except Exception:
        return []
    return [h["_source"] for h in resp.get("hits", {}).get("hits", [])]

# ═══════════════════════════════════════════════════════════════
# System Prompts
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是一个专业的美食探店助手，名叫"大众点评 AI 小探"。你的任务是基于真实的商家和评价数据，为用户推荐合适的餐厅。

## 你的核心能力
1. 根据用户的自然语言需求（菜系、场景、预算、口味、人数、位置偏好等），从检索到的商家中推荐最匹配的
2. 每条推荐必须附带具体的推荐理由，引用真实评价中的信息，让用户感受到推荐的可靠性
3. 当用户需求不够明确时，**主动提问**帮助用户细化需求

## 信息收集策略（重要！）
当用户的提问比较模糊时，你需要主动询问以下维度的信息来缩小推荐范围：
- 🍽️ **菜系偏好**：川菜、粤菜、日料、西餐、火锅、烧烤……
- 💰 **预算范围**：人均大致多少？经济实惠还是高端享受？
- 🎯 **用餐场景**：约会、家庭聚餐、朋友聚会、商务宴请、一人食？
- 📍 **位置要求**：哪个区域？距离重要吗？
- 😋 **口味偏好**：辣、清淡、甜、酸？有什么忌口？
- ⭐ **其他要求**：环境、服务、停车、包间、是否需要排队？

**提问原则**：
- 一次最多问 2-3 个最关键的维度，不要一次把所有问题都抛给用户
- 先判断检索结果是否已经足够回答，如果检索结果已经很好匹配了，直接推荐
- 只有在检索结果不够理想或用户需求确实模糊时才追问
- 追问时要自然、友好，像朋友聊天一样

## 输出格式

### 当信息足够时，直接推荐：
**推荐商家：{商家名称}**
- ⭐ 评分：{评分} | 📍 地址：{地址}
- 🏷️ 类别：{类别标签}
- 💬 推荐理由：{具体理由，引用评价内容}
- 📝 参考评价：[来源引用]

最后用 1-2 句话总结推荐。

### 当信息不足时，先追问再推荐：
在回复中自然地嵌入追问，例如：
"我找到了几家不错的店，不过想帮你挑到最合适的～你比较偏好哪种菜系呢？另外大概的人均预算是多少呀？"

然后依然展示目前最匹配的 1-2 个选择，让用户有参考。

## 重要规则
1. 只推荐检索结果中存在的商家，绝不编造商家或评价
2. 推荐理由必须来源于检索到的真实评价内容
3. 如果检索结果为空，诚实告知并建议用户调整搜索条件
4. 回复简洁、口语化，像朋友推荐一样自然
5. 永远保持积极、热情的态度 😊"""

# ── Clarify-only prompt (used when search returns zero results) ──

CLARIFY_PROMPT = """你是一个贴心的美食探店助手。用户在寻找餐厅，但当前数据库中没有找到匹配的结果。

请友好地告知用户这个情况，并引导用户提供更多信息。你可以从以下角度提问：
- 想吃什么类型的菜系？（川菜、日料、西餐...）
- 有什么特别的场景需求吗？（约会、聚餐...）
- 预算大概在什么范围？

注意：
- 语气要温暖、鼓励，不要让用户感到沮丧
- 一次提出 2-3 个具体建议即可
- 可以给出一些热门搜索关键词作为参考"""

# ═══════════════════════════════════════════════════════════════
# Fallback Messages
# ═══════════════════════════════════════════════════════════════

FALLBACK_MESSAGE = """抱歉，我在当前数据中暂时没有找到与「{query}」完全匹配的商家。😔

💡 **你可以试试：**
- 换个关键词，比如具体的菜系名（川菜、日料、火锅…）
- 试试场景化描述，比如"适合约会的餐厅""安静的咖啡馆"
- 告诉我你的口味偏好，我帮你精准推荐～

我还在不断学习中，感谢你的理解！"""

# ═══════════════════════════════════════════════════════════════
# Prompt Builders
# ═══════════════════════════════════════════════════════════════


def build_context(businesses: list[dict]) -> str:
    """Build RAG context string from retrieved businesses and their top reviews.

    Args:
        businesses: List of business dicts from OpenSearch (must contain at
            least ``business_id``, ``name``, ``stars``, ``city``, ``address``,
            ``categories``, ``review_count``).

    Returns:
        A formatted string ready to inject into the LLM prompt.
    """
    parts: list[str] = []
    for i, biz in enumerate(businesses, 1):
        name = biz.get("name", "未知商家")
        stars = biz.get("stars", "N/A")
        city = biz.get("city", "")
        address = biz.get("address", "")
        categories = biz.get("categories", "")
        review_count = biz.get("review_count", 0)

        parts.append(
            f"[{i}] {name} | ⭐{stars} | 📍{address}, {city}\n"
            f"    类别: {categories} | 评价数: {review_count}"
        )

        # Attach top reviews for this business
        biz_id = biz.get("business_id", "")
        if biz_id:
            reviews = _fetch_reviews(biz_id, top_k=3)
            if reviews:
                parts.append("    精选评价:")
                for r in reviews:
                    text = r.get("text", "")
                    if len(text) > 200:
                        text = text[:200] + "..."
                    parts.append(
                        f"      - {r.get('stars', '?')}★ | {text}"
                    )

    return "\n".join(parts)


def build_user_prompt(
    query: str,
    context: str,
    history: list[dict[str, str]] | None = None,
    profile_text: str | None = None,
) -> str:
    """Assemble the final user prompt with history, profile, context, and query.

    Args:
        query: The user's current natural-language message.
        context: Pre-built RAG context from ``build_context()``.
        history: Optional conversation history (oldest first).  Only the last
            6 messages (3 exchanges) are included to keep the prompt short.
        profile_text: Optional user profile text (from user_profile module).

    Returns:
        The complete user prompt string.
    """
    parts: list[str] = []

    # ── User Profile (if available) ──
    if profile_text:
        parts.append(profile_text)
        parts.append("")

    # ── Conversation history (recent only) ──
    if history:
        recent = history[-6:]  # last 3 exchanges
        parts.append("## 对话历史")
        for m in recent:
            role_label = "用户" if m["role"] == "user" else "助手"
            parts.append(f"{role_label}: {m['content']}")
        parts.append("")  # blank line separator

    # ── Retrieved data ──
    parts.append(f"## 检索到的商家数据\n{context}")
    parts.append("")  # blank line separator

    # ── Current query ──
    parts.append(f"## 用户问题\n{query}")
    parts.append("")
    parts.append(
        "请根据上面的检索数据为用户推荐最合适的商家。"
        "如果用户需求不够明确，请在推荐的同时友善地追问 1-2 个关键信息（菜系、预算、场景等），"
        "帮助用户缩小范围。如果数据不足以回答用户问题，请诚实告知并引导用户调整搜索条件。"
    )

    return "\n".join(parts)


def build_clarify_prompt(query: str) -> str:
    """Build a prompt specifically for clarifying vague queries.

    Use this when search returns zero or very low-quality results.

    Args:
        query: The user's original query.

    Returns:
        A prompt that instructs the LLM to ask clarifying questions.
    """
    return (
        f"用户说：「{query}」\n\n"
        "数据库中没有找到匹配的商家。请友好地告知用户，"
        "并主动询问 2-3 个关键信息（菜系偏好、预算、场景等），"
        "帮助用户调整搜索方向。语气要温暖、鼓励。"
    )
