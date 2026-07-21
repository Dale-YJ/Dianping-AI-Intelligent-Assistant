"""数据模型定义

对应接口文档第七章：数据模型
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── 通用响应模型 ──────────────────────────────────────────

class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    code: int = Field(0, description="业务状态码，0 表示成功")
    message: str = Field("success", description="状态描述")
    data: Optional[dict | list] = Field(None, description="响应数据")
    request_id: str = Field("", description="请求唯一标识")


# ── 情感分析结果 ──────────────────────────────────────────

class Sentiment(BaseModel):
    """情感分析结果（7.3）"""
    label: str = Field(..., description="positive/neutral/negative")
    label_cn: str = Field(..., description="正面/中性/负面")
    icon: str = Field(..., description="😊/😐/😞")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")


# ── 溯源引用 ──────────────────────────────────────────────

class Source(BaseModel):
    """溯源引用（7.5）"""
    review_id: str
    user_name: str
    date: str
    snippet: str = Field(..., description="评价原文片段")
    rating: int = Field(..., ge=1, le=5)


# ── 摘要条目 ──────────────────────────────────────────────

class SummaryItem(BaseModel):
    """摘要条目"""
    point: str = Field(..., description="观点描述")
    mention_count: int = Field(0, description="提及次数")
    sources: List[Source] = Field(default_factory=list, description="溯源引用")


class SummarySection(BaseModel):
    """摘要章节"""
    title: str
    items: List[SummaryItem] = Field(default_factory=list)


class RecentTrend(BaseModel):
    """近期动态"""
    title: str = "📊 近期动态"
    summary: str = ""
    period: str = ""
    sources: List[Source] = Field(default_factory=list)


# ── 商家模型 ──────────────────────────────────────────────

class Business(BaseModel):
    """商家模型（7.1）"""
    business_id: str
    name: str
    address: str = ""
    city: str = ""
    state: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    rating: float = Field(0.0, ge=0.0, le=5.0)
    review_count: int = 0
    categories: List[str] = Field(default_factory=list)
    hours: dict = Field(default_factory=dict)
    attributes: dict = Field(default_factory=dict)


# ── 评价模型 ──────────────────────────────────────────────

class Review(BaseModel):
    """评价模型（7.2）"""
    review_id: str
    business_id: str = ""
    business_name: str = ""
    user_name: str = ""
    rating: int = Field(3, ge=1, le=5)
    text: str = ""
    date: str = ""
    useful: int = 0
    funny: int = 0
    cool: int = 0
    sentiment: Optional[Sentiment] = None
    source: str = Field("ingested", description="评价来源: ingested(预导入) / user(用户提交)")


# ── 关键词标签 ────────────────────────────────────────────

class KeywordTag(BaseModel):
    """关键词标签（7.4）"""
    keyword: str
    count: int = 0
    score: float = Field(0.0, ge=0.0, le=1.0)
    dimension: str = Field(..., description="dish/environment/service/price")


class KeywordGroup(BaseModel):
    """关键词分组"""
    dimension: str
    label: str
    icon: str
    tags: List[KeywordTag] = Field(default_factory=list)