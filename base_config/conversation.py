from __future__ import annotations

import json
import uuid
from typing import List, Dict, Any, Optional


from base_config.redis_client import redis_manager


#每个对话最多保存 20 条消息
MAX_HISTORY = 20
#会话key的前缀
CONVERSATION_KEY_PREFIX = "conv:"
#对话过期时间
HISTORY_TTL = 60 * 60 * 24 * 7  # 7 days in seconds


# 辅助函数
#根据会话id生成key
def _get_conversation_key(conversation_id: str) -> str:
    #前缀加id
    return f"{CONVERSATION_KEY_PREFIX}{conversation_id}"

#序列化消息
def _serialize_message(message: Dict[str, str]) -> str:
    """Serialize message dict to JSON string."""
    return json.dumps(message, ensure_ascii=False)

#反序列化消息
def _deserialize_message(data: str) -> Dict[str, str]:
    """Deserialize JSON string to message dict."""
    return json.loads(data)


#创建会话
async def get_or_create_conversation(conversation_id: str | None = None) -> str:

    await redis_manager.initialize()
    async with redis_manager.get_client() as client:
        if conversation_id:
            # 检查这个id是否已经存在
            key = _get_conversation_key(conversation_id)
            exists = await client.exists(key)
            if exists:
                #刷新过期时间
                await client.expire(key, HISTORY_TTL)
                return conversation_id

        # 新生成一个
        new_id = uuid.uuid4().hex[:12]
        key = _get_conversation_key(new_id)

        #创建新list
        await client.lpush(key, "init")
        #清空
        await client.ltrim(key, 0, 0)
        await client.expire(key, HISTORY_TTL)

        return new_id


async def add_message(conversation_id: str, role: str, content: str) -> None:

    await redis_manager.initialize()
    async with redis_manager.get_client() as client:
        key = _get_conversation_key(conversation_id)

        # Check if conversation exists, create if not
        exists = await client.exists(key)
        if not exists:
            # Initialize with TTL
            await client.lpush(key, "init")
            await client.ltrim(key, 0, 0)
            await client.expire(key, HISTORY_TTL)


        message = {"role": role, "content": content}
        serialized = _serialize_message(message)

        pipe = client.pipeline()
        pipe.rpush(key, serialized)
        pipe.ltrim(key, -MAX_HISTORY, -1)
        pipe.expire(key, HISTORY_TTL)
        await pipe.execute()


async def get_history(conversation_id: str) -> List[Dict[str, str]]:
    await redis_manager.initialize()
    async with redis_manager.get_client() as client:
        key = _get_conversation_key(conversation_id)
        messages = await client.lrange(key, 0, -1)

        history = []
        for msg_str in messages:
            try:
                msg = _deserialize_message(msg_str)
                history.append(msg)
            except json.JSONDecodeError:
                # Skip malformed entries
                continue

        if history:
            await client.expire(key, HISTORY_TTL)

        return history


async def get_recent_history(
        conversation_id: str, n: int = 6
) -> List[Dict[str, str]]:
    await redis_manager.initialize()
    async with redis_manager.get_client() as client:
        key = _get_conversation_key(conversation_id)
        #获取最新的n条消息
        messages = await client.lrange(key, -n, -1)
        history = []
        for msg_str in messages:
            try:
                msg = _deserialize_message(msg_str)
                history.append(msg)
            except json.JSONDecodeError:
                continue

        if history:
            await client.expire(key, HISTORY_TTL)

        return history


async def clear_conversation(conversation_id: str) -> None:
    await redis_manager.initialize()
    async with redis_manager.get_client() as client:
        key = _get_conversation_key(conversation_id)
        await client.delete(key)


async def conversation_count() -> int:
    await redis_manager.initialize()
    async with redis_manager.get_client() as client:
        count = 0
        cursor = 0
        pattern = f"{CONVERSATION_KEY_PREFIX}*"

        while True:
            cursor, keys = await client.scan(cursor, match=pattern, count=100)
            count += len(keys)
            if cursor == 0:
                break

        return count

async def list_conversations() -> list[dict[str, Any]]:
    """List all conversations with id, title, message_count, updated_at."""
    import time

    await redis_manager.initialize()
    async with redis_manager.get_client() as client:
        conversations = []
        cursor = 0
        pattern = f"{CONVERSATION_KEY_PREFIX}*"

        while True:
            cursor, keys = await client.scan(cursor, match=pattern, count=100)
            for key in keys:
                conv_id = key.decode("utf-8").removeprefix(CONVERSATION_KEY_PREFIX)

                pipe = client.pipeline()
                pipe.llen(key)
                pipe.lrange(key, 1, 6)  # skip init marker, grab up to 6 real msgs for title
                pipe.ttl(key)
                results = await pipe.execute()

                msg_count = results[0]
                if msg_count == 0:
                    continue  # expired or empty, skip

                raw_msgs = results[1]
                ttl = results[2]

                # Derive title from first user message
                title = "新对话"
                for raw in raw_msgs:
                    try:
                        msg = _deserialize_message(
                            raw.decode("utf-8") if isinstance(raw, bytes) else raw
                        )
                        if msg.get("role") == "user":
                            title = msg.get("content", "新对话")[:50]
                            break
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue

                # Approximate updated_at from remaining TTL
                now_ts = int(time.time())
                if ttl > 0:
                    updated_at = now_ts - (HISTORY_TTL - ttl)
                else:
                    updated_at = now_ts
                    await client.expire(key, HISTORY_TTL)

                conversations.append({
                    "id": conv_id,
                    "title": title,
                    "message_count": msg_count,
                    "updated_at": updated_at,
                })

            if cursor == 0:
                break

        conversations.sort(key=lambda c: c["updated_at"], reverse=True)
        return conversations


async def close_redis():
    await redis_manager.close()


