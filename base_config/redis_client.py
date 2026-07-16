from __future__ import annotations
import asyncio
from typing import List, Dict, Any, Optional
import redis.asyncio as redis
from contextlib import asynccontextmanager

from config import settings


class RedisManager:
    """Manages Redis connection pool."""

    def __init__(self):
        #连接池
        self._pool: Optional[redis.ConnectionPool] = None
        #客户端实例
        self._client: Optional[redis.Redis] = None
        #锁
        self._init_lock = asyncio.Lock()

    #异步初始化
    async def initialize(self):
        if self._pool is None:
            async with self._init_lock:
                if self._pool is None:
                    self._pool = redis.ConnectionPool(
                        host=settings.redis_host,
                        port=settings.redis_port,
                        db=settings.redis_db,
                        password=settings.redis_password,
                        decode_responses=True,
                        max_connections=settings.redis_max_connections,
                    )
                    self._client = redis.Redis(connection_pool=self._pool)


    async def close(self):
        async with self._init_lock:  # 关闭加锁
            if self._pool:
                await self._pool.disconnect()
                self._pool = None
                self._client = None


    @asynccontextmanager
    async def get_client(self):
        async with self._init_lock:
            if self._client is None:
                await self.initialize()
            try:
                yield self._client
            except Exception as e:
                # Log error here if needed
                raise

# 全局实例
redis_manager = RedisManager()


async def main():
    # 1. 初始化连接池
    await redis_manager.initialize()
    # 2. 获取客户端
    async with redis_manager.get_client() as db:
        # 设置键值对
        await db.set('name', '张三')

        # 获取键值对
        value = await db.get('name')
        print(value)

    # 3. 关闭连接
    await redis_manager.close()


# 运行异步主函数
if __name__ == "__main__":
    #main()
    asyncio.run(main())



