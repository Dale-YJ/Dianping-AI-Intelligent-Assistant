"""清空所有 yelp 索引的数据，保留索引结构和 mapping"""
from opensearch_client import get_opensearch_client

INDICES = ["yelp_business", "yelp_review", "yelp_checkin", "yelp_tip", "yelp_user"]

def clear_indices():
    client = get_opensearch_client()
    if not client:
        print("[ERROR] 无法连接到 OpenSearch")
        return

    for idx in INDICES:
        if client.indices.exists(index=idx):
            # delete_by_query 清空所有文档，保留 mapping/settings
            result = client.delete_by_query(
                index=idx,
                body={"query": {"match_all": {}}}
            )
            deleted = result.get("deleted", 0)
            print(f"  {idx}: 已删除 {deleted} 条记录")
        else:
            print(f"  {idx}: 索引不存在，跳过")

    print("\n[OK] 清空完成，索引结构已保留")

if __name__ == "__main__":
    clear_indices()
