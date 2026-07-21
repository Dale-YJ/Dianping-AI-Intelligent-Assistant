"""用户评价请求/响应模型

用于用户提交、修改评价时的请求体校验。
"""
from typing import Optional
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    """创建评价请求"""
    user_name: str = Field(
        default="匿名用户",
        min_length=1,
        max_length=50,
        description="用户昵称",
    )
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="评分（1-5星）",
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="评价内容",
    )


class ReviewUpdate(BaseModel):
    """修改评价请求（至少提供一个字段）"""
    rating: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="评分（1-5星）",
    )
    text: Optional[str] = Field(
        None,
        min_length=1,
        max_length=2000,
        description="评价内容",
    )
