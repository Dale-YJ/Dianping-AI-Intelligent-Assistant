
        if not os.path.exists(file_path):
            print(f"❌ 找不到 {city_name} 数据文件: {file_path}")
            return

    print("✅ 数据文件检查通过")
    print(f"   北京: {os.path.getsize(BEIJING_FILE)/1024:.0f} KB")
    print(f"   成都: {os.path.getsize(CHENGDU_FILE)/1024:.0f} KB")
    print(f"   广州: {os.path.getsize(GUANGZHOU_FILE)/1024:.0f} KB")
    print(f"   上海: {os.path.getsize(SHANGHAI_FILE)/1024:.0f} KB")

    for file_path, city_name in city_files.items():
        bulk_import_city(
            client=client,
            file_path=file_path,
            city_name=city_name,
        )

    # 验证
    verify_data(client)

    print("\n" + "=" * 60)
    print("🎉🎉🎉 国内城市数据导入完成!")
    print("=" * 60)
    print("\n💡 提示：现在可以直接问「北京的烤鸭推荐」「成都的火锅」等")
    print("   数据已导入到 yelp_business / yelp_review，现有检索代码无需修改。")


if __name__ == "__main__":
    main()
