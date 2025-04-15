import requests
import json

# Notion API 信息
NOTION_DATABASE_ID = "1d6bca045b5f80419b7aeef0048d9711"
NOTION_API_TOKEN = "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"

# Keep API 信息
KEEP_MOBILE = "18179467704"
KEEP_PASSWORD = "wdsr0522Q"

# Notion 请求头
notion_headers = {
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2021-05-13",
}

# 示例：从 Keep 获取数据的函数
def get_keep_data():
    # 模拟获取 Keep 数据
    keep_data = {
        "运动类型": "跑步",
        "距离": 5.3,
        "时长": 30,
        "日期": "2025-04-15",
        "轨迹图": "https://example.com/track_image.jpg",
    }
    return keep_data

# 将数据添加到 Notion 数据库
def add_to_notion(data):
    url = f"https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "运动类型": {"title": [{"text": {"content": data["运动类型"]}}]},
            "距离": {"number": data["距离"]},
            "时长": {"number": data["时长"]},
            "日期": {"date": {"start": data["日期"]}},
            "轨迹图": {"files": [{"name": "轨迹图", "external": {"url": data["轨迹图"]}}]},
        }
    }

    try:
        response = requests.post(url, headers=notion_headers, json=payload)
        response.raise_for_status()  # 会抛出异常如果请求失败
        print("数据同步到 Notion 成功！")
    except requests.exceptions.HTTPError as errh:
        print(f"HTTP 错误: {errh}")
        print("错误响应内容：", response.text)
    except requests.exceptions.RequestException as err:
        print(f"请求错误: {err}")

# 主程序
def main():
    keep_data = get_keep_data()
    add_to_notion(keep_data)

if __name__ == "__main__":
    main()
