# opensearch_client.py
from opensearchpy import OpenSearch
from config import settings
import threading
_opensearch_client = None

#全局单例模式
# def get_opensearch_client() -> OpenSearch:
#     global _opensearch_client
#     if _opensearch_client is None:
#         _opensearch_client = OpenSearch(
#         hosts=[{
#             "host": settings.opensearch_host,
#             "port": settings.opensearch_port,
#         }],
#         http_auth=(settings.opensearch_user, settings.opensearch_password),
#         use_ssl=settings.opensearch_use_ssl,
#         verify_certs=False,  # 本地开发跳过证书校验
#         ssl_show_warn=False,
#     )
#     return _opensearch_client
#


_lock = threading.Lock()  # 创建一把锁，用于控制线程访问


def get_opensearch_client() -> OpenSearch:
    global _opensearch_client

    # 第一层检查：如果已经初始化，直接返回（提高性能，避免等待锁）
    if _opensearch_client is None:
        # 加锁：确保同一时间只有一个线程能进入创建逻辑
        with _lock:
            # 第二层检查：防止在等待锁期间，其他线程已经创建了实例
            if _opensearch_client is None:
                # 构建连接参数
                os_kwargs = {
                    "hosts": [{
                        "host": settings.opensearch_host,
                        "port": settings.opensearch_port,
                    }],
                    "use_ssl": settings.opensearch_use_ssl,
                    "verify_certs": False,
                    "ssl_show_warn": False,
                    "timeout": 30,
                    "max_retries": 3,
                    "retry_on_timeout": True,
                }
                # 仅在配置了用户名/密码时启用认证
                if settings.opensearch_user and settings.opensearch_password:
                    os_kwargs["http_auth"] = (settings.opensearch_user, settings.opensearch_password)

                _opensearch_client = OpenSearch(**os_kwargs)

    return _opensearch_client


if __name__ == "__main__":
    client = get_opensearch_client()
    print(f"OpenSearch 已连接: {client.info()['version']['number']}")
    print(f"yelp_business 文档数: {client.count(index='yelp_business')['count']}")
    res = client.search(
        index="yelp_business",
        body={"size": 3, "query": {"match_all": {}}}
    )
    print("\n示例商家:")
    for hit in res["hits"]["hits"]:
        s = hit["_source"]
        print(f"  - {s['name']} ({s['city']}, {s['state']}) ★{s['stars']}")