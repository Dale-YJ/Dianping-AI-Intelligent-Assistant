"""User profile management — Redis-backed user preferences.

Manages user profile data including location, cuisine preferences,
dining scenarios, budget level, and other extracted keywords.

All data is stored in Redis with 30-day TTL.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import Redis client from base_config
from base_config.redis_client import redis_manager

logger = logging.getLogger(__name__)

# Redis key prefix for user profiles
PROFILE_KEY_PREFIX = "profile:"
# Profile TTL (30 days in seconds)
PROFILE_TTL = 60 * 60 * 24 * 30


def _get_profile_key(conversation_id: str) -> str:
    """Generate Redis key for user profile."""
    return f"{PROFILE_KEY_PREFIX}{conversation_id}"


class UserProfile:
    """User profile data structure.
    
    Attributes:
        locations: List of mentioned locations/cities
        cuisine_preferences: Preferred cuisine types
        taste_preferences: Taste preferences (spicy, mild, sweet, etc.)
        dining_scenarios: Dining scenarios (date, gathering, business, etc.)
        budget_level: Budget preference (budget, mid-range, luxury)
        other_keywords: Other extracted keywords
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        locations: Optional[List[str]] = None,
        cuisine_preferences: Optional[List[str]] = None,
        taste_preferences: Optional[List[str]] = None,
        dining_scenarios: Optional[List[str]] = None,
        budget_level: Optional[str] = None,
        other_keywords: Optional[List[str]] = None,
        updated_at: Optional[str] = None,
    ):
        self.locations = locations or []
        self.cuisine_preferences = cuisine_preferences or []
        self.taste_preferences = taste_preferences or []
        self.dining_scenarios = dining_scenarios or []
        self.budget_level = budget_level
        self.other_keywords = other_keywords or []
        self.updated_at = updated_at or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "locations": self.locations,
            "cuisine_preferences": self.cuisine_preferences,
            "taste_preferences": self.taste_preferences,
            "dining_scenarios": self.dining_scenarios,
            "budget_level": self.budget_level,
            "other_keywords": self.other_keywords,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserProfile":
        """Create from dictionary."""
        return cls(
            locations=data.get("locations", []),
            cuisine_preferences=data.get("cuisine_preferences", []),
            taste_preferences=data.get("taste_preferences", []),
            dining_scenarios=data.get("dining_scenarios", []),
            budget_level=data.get("budget_level"),
            other_keywords=data.get("other_keywords", []),
            updated_at=data.get("updated_at"),
        )
    
    def merge_with(self, new_data: Dict[str, Any]) -> "UserProfile":
        """Merge new data into existing profile.
        
        Args:
            new_data: New extracted data from profile analyzer
        
        Returns:
            Updated UserProfile instance
        """
        # Merge lists (deduplicate)
        if new_data.get("locations"):
            self.locations = list(set(self.locations + new_data["locations"]))
        
        if new_data.get("cuisine_preferences"):
            self.cuisine_preferences = list(
                set(self.cuisine_preferences + new_data["cuisine_preferences"])
            )
        
        if new_data.get("taste_preferences"):
            self.taste_preferences = list(
                set(self.taste_preferences + new_data["taste_preferences"])
            )
        
        if new_data.get("dining_scenarios"):
            self.dining_scenarios = list(
                set(self.dining_scenarios + new_data["dining_scenarios"])
            )
        
        if new_data.get("budget_level"):
            self.budget_level = new_data["budget_level"]
        
        if new_data.get("other_keywords"):
            self.other_keywords = list(
                set(self.other_keywords + new_data["other_keywords"])
            )
        
        # Remove keywords if specified
        if new_data.get("remove_keywords"):
            for kw in new_data["remove_keywords"]:
                self.locations = [x for x in self.locations if x != kw]
                self.cuisine_preferences = [x for x in self.cuisine_preferences if x != kw]
                self.taste_preferences = [x for x in self.taste_preferences if x != kw]
                self.dining_scenarios = [x for x in self.dining_scenarios if x != kw]
                self.other_keywords = [x for x in self.other_keywords if x != kw]
        
        self.updated_at = datetime.now().isoformat()
        return self


async def get_user_profile(conversation_id: str) -> UserProfile:
    """Get user profile from Redis.
    
    Args:
        conversation_id: Conversation ID
    
    Returns:
        UserProfile instance (empty if not exists)
    """
    await redis_manager.initialize()
    async with redis_manager.get_client() as client:
        key = _get_profile_key(conversation_id)
        
        try:
            data = await client.get(key)
            
            if data:
                profile_dict = json.loads(data)
                logger.info(f"Loaded user profile for conversation {conversation_id}")
                return UserProfile.from_dict(profile_dict)
            
        except Exception as e:
            logger.warning(f"Failed to load user profile: {e}")
        
        # Return empty profile
        return UserProfile()


async def save_user_profile(conversation_id: str, profile: UserProfile) -> None:
    """Save user profile to Redis.
    
    Args:
        conversation_id: Conversation ID
        profile: UserProfile instance to save
    """
    await redis_manager.initialize()
    async with redis_manager.get_client() as client:
        key = _get_profile_key(conversation_id)
        
        try:
            data = json.dumps(profile.to_dict(), ensure_ascii=False)
            await client.set(key, data)
            await client.expire(key, PROFILE_TTL)
            logger.info(f"Saved user profile for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")


async def update_user_profile(
    conversation_id: str,
    new_data: Dict[str, Any],
) -> UserProfile:
    """Update user profile with new extracted data.
    
    Args:
        conversation_id: Conversation ID
        new_data: New extracted data from profile analyzer
    
    Returns:
        Updated UserProfile instance
    """
    profile = await get_user_profile(conversation_id)
    updated_profile = profile.merge_with(new_data)
    await save_user_profile(conversation_id, updated_profile)
    return updated_profile


async def clear_user_profile(conversation_id: str) -> None:
    """Clear user profile from Redis.
    
    Args:
        conversation_id: Conversation ID
    """
    await redis_manager.initialize()
    async with redis_manager.get_client() as client:
        key = _get_profile_key(conversation_id)
        await client.delete(key)
        logger.info(f"Cleared user profile for conversation {conversation_id}")


def format_profile_for_prompt(profile: UserProfile) -> str:
    """Format user profile for LLM prompt.
    
    Args:
        profile: UserProfile instance
    
    Returns:
        Formatted string for prompt injection
    """
    if not any([
        profile.locations,
        profile.cuisine_preferences,
        profile.taste_preferences,
        profile.dining_scenarios,
        profile.budget_level,
        profile.other_keywords,
    ]):
        return ""
    
    parts = ["## 用户画像（历史偏好）"]
    
    if profile.locations:
        parts.append(f"- 关注地区：{', '.join(profile.locations)}")
    
    if profile.cuisine_preferences:
        parts.append(f"- 菜系偏好：{', '.join(profile.cuisine_preferences)}")
    
    if profile.taste_preferences:
        parts.append(f"- 口味偏好：{', '.join(profile.taste_preferences)}")
    
    if profile.dining_scenarios:
        parts.append(f"- 用餐场景：{', '.join(profile.dining_scenarios)}")
    
    if profile.budget_level:
        parts.append(f"- 预算水平：{profile.budget_level}")
    
    if profile.other_keywords:
        parts.append(f"- 其他特征：{', '.join(profile.other_keywords)}")
    
    parts.append("")
    parts.append("（注意：当前用户提出的新需求权重更高，请优先满足新需求，用户画像仅供参考）")
    
    return "\n".join(parts)