"""商家口碑分析数据模型

包含：
1. 关键特征词提取相关模型
2. 评价情感分析相关模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field


# ── 关键特征词提取 ──────────────────────────────────────────

class KeywordTag(BaseModel):
    """关键词标签"""
    keyword: str = Field(..., description="关键词文本")
    count: int = Field(0, ge=0, description="提及次数")
    score: float = Field(0.0, ge=0.0, le=1.0, description="重要性分数")
    dimension: str = Field(..., description="维度分类: dish/environment/service/price")
    sentiment: Optional[str] = Field(None, description="情感倾向: positive/negative/neutral")


class KeywordGroup(BaseModel):
    """关键词分组（按维度）"""
    dimension: str = Field(..., description="维度标识")
    label: str = Field(..., description="维度显示名称")
    icon: str = Field(..., description="维度图标")
    tags: List[KeywordTag] = Field(default_factory=list, description="关键词列表")


class KeywordExtractionResponse(BaseModel):
    """关键词提取响应"""
    business_id: str
    business_name: str
    total_reviews_analyzed: int = Field(..., description="分析的评价总数")
    total_keywords: int = Field(..., description="提取的关键词总数")
    keyword_groups: List[KeywordGroup] = Field(default_factory=list, description="按维度分组的关键词")
    generated_at: str = Field(..., description="生成时间")


# ── 评价情感分析 ────────────────────────────────────────────

class Sentiment(BaseModel):
    """情感分析结果"""
    label: str = Field(..., description="情感标签: positive/neutral/negative")
    label_cn: str = Field(..., description="中文标签: 正面/中性/负面")
    icon: str = Field(..., description="情感图标: 😊/😐/😞")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")


class SentimentStats(BaseModel):
    """情感统计"""
    total_reviews: int = Field(..., description="评价总数")
    positive_count: int = Field(0, description="正面评价数量")
    neutral_count: int = Field(0, description="中性评价数量")
    negative_count: int = Field(0, description="负面评价数量")
    positive_ratio: float = Field(0.0, ge=0.0, le=1.0, description="正面评价占比")
    neutral_ratio: float = Field(0.0, ge=0.0, le=1.0, description="中性评价占比")
    negative_ratio: float = Field(0.0, ge=0.0, le=1.0, description="负面评价占比")


class ReviewWithSentiment(BaseModel):
    """带情感分析的评价"""
    review_id: str
    user_name: str = Field(..., description="用户名（脱敏）")
    rating: int = Field(..., ge=1, le=5, description="评分")
    text: str = Field(..., description="评价内容")
    date: str = Field(..., description="评价日期")
    useful: int = Field(0, description="有用数")
    funny: int = Field(0, description="有趣数")
    cool: int = Field(0, description="酷数")
    sentiment: Sentiment = Field(..., description="情感分析结果")


class SentimentAnalysisResponse(BaseModel):
    """情感分析响应"""
    business_id: str
    business_name: str
    total_reviews: int = Field(..., description="评价总数")
    sentiment_stats: SentimentStats = Field(..., description="情感统计")
    reviews: List[ReviewWithSentiment] = Field(default_factory=list, description="带情感分析的评价列表")
    generated_at: str = Field(..., description="生成时间")