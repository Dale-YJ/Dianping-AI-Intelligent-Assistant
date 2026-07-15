import json
import os

#当前脚本所在的文件夹
current_script_dir = os.path.dirname(os.path.abspath(__file__))
#项目的根路径
BASE_DIR = os.path.dirname(current_script_dir)

#原始数据所在的文件夹
RAW_DATA_DIR = os.path.join(BASE_DIR, "knowledge_base", "raw_data")
#处理后的数据所放的文件夹
SMALL_DATA_DIR = os.path.join(BASE_DIR, "knowledge_base", "small_data")




# 原始大文件路径
BUSINESS_RAW = os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_business.json")
REVIEW_RAW = os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_review.json")
CHECK_IN_RAW=os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_checkin.json")
TIP_RAW=os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_tip.json")
USER_RAW=os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_user.json")

# 处理后小文件路径
BUSINESS_SMALL = os.path.join(SMALL_DATA_DIR, "small_business.json")
REVIEW_SMALL = os.path.join(SMALL_DATA_DIR, "small_review.json")
CHECK_IN_SMALL=os.path.join(SMALL_DATA_DIR, "small_checkin.json")
TIP_SMALL=os.path.join(SMALL_DATA_DIR, "small_tip.json")
USER_SMALL=os.path.join(SMALL_DATA_DIR, "small_user.json")


def trim_json_file(source_path, target_path, limit=5000):
    """裁剪JSON文件，只保留前N条记录"""
    print(f"处理文件: {os.path.basename(source_path)}")
    print(f"目标数量: {limit}条")

    count = 0

    with open(source_path, 'r', encoding='utf-8') as f_in:
        with open(target_path, 'w', encoding='utf-8') as f_out:
            for line in f_in:
                if count >= limit:
                    break

                # 验证JSON格式
                try:
                    json_obj = json.loads(line.strip())
                    f_out.write(json.dumps(json_obj) + '\n')
                    count += 1

                    if count % 1000 == 0:
                        print(f"  已处理: {count}条")
                except json.JSONDecodeError as e:
                    print(f"  JSON解析错误，跳过此行: {e}")
                    continue

    print(f"✅ 完成! 共处理 {count} 条数据")
    print(f"   输出文件: {target_path}\n")


if __name__ == "__main__":
    # 检查源文件是否存在

    if not os.path.exists(BUSINESS_RAW):
        print(f"错误: 找不到business数据文件")
        print(f"期望路径: {BUSINESS_RAW}")
        exit(1)
    if not os.path.exists(REVIEW_RAW):
        print(f"错误: 找不到review数据文件")
        print(f"期望路径: {REVIEW_RAW}")
        exit(1)
    if not os.path.exists(CHECK_IN_RAW):
        print(f"错误: 找不到check in文件")
        print(f"期望路径: {CHECK_IN_RAW}")
        exit(1)
    if not os.path.exists(TIP_RAW):
        print(f"错误: 找不到tip文件")
        print(f"期望路径: {TIP_RAW}")
        exit(1)
    if not os.path.exists(USER_RAW):
        print(f"错误: 找不到user文件")
        print(f"期望路径: {USER_RAW}")
        exit(1)

    trim_json_file(BUSINESS_RAW, BUSINESS_SMALL, 5000)
    trim_json_file(REVIEW_RAW, REVIEW_SMALL, 20000)
    trim_json_file(CHECK_IN_RAW, CHECK_IN_SMALL, 20000)
    trim_json_file(TIP_RAW, TIP_SMALL, 20000)
    trim_json_file(USER_RAW, USER_SMALL, 20000)