import requests
import json
import os
from datetime import datetime

# ==== Notion 设置 ====
NOTION_API_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

notion_headers = {
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# ==== Keep 账号 ====
KEEP_MOBILE = os.getenv("KEEP_MOBILE")
KEEP_PASSWORD = os.getenv("KEEP_PASSWORD")

# ==== 本地存储 ====
SYNC_FILE = "last_sync.json"

# ========== 登录 Keep（模拟） ==========
def login_keep(mobile, password):
    # TODO：替换为真实 Keep 登录接口
    print(f"🔐 登录 Keep 账号：{mobile}")
    return "mocked_token_123"

# ========== 获取 Keep 历史记录（模拟） ==========
def fetch_keep_records(token):
    # TODO：替换为真实 Keep 接口，拿到所有记录（可分页）
    return [
        {
            "type": "跑步",
            "distance": 5.21,
            "duration": 33,
            "date": "2025-04-11",
            "track_image_url": "https://example.com/track1.jpg",
        },
        {
            "type": "骑行",
            "distance": 9.42,
            "duration": 50,
            "date": "2025-04-12",
            "track_image_url": "https://example.com/track2.jpg",
        }
    ]

# ========== 工具函数 ==========
def get_last_sync_time():
    if os.path.exists(SYNC_FILE):
        with open(SYNC_FILE, 'r') as f:
            data = json.load(f)
            return datetime.strptime(data["last_sync"], "%Y-%m-%d")
    return datetime.strptime("2025-01-01", "%Y-%m-%d")

def save_last_sync_time():
    with open(SYNC_FILE, 'w') as f:
        json.dump({"last_sync": datetime.now().strftime("%Y-%m-%d")}, f)

def get_new_records(records, last_sync_time):
    new_data = []
    for item in records:
        record_time = datetime.strptime(item["date"], "%Y-%m-%d")
        if record_time > last_sync_time:
            new_data.append(item)
    return new_data

# ========== 同步到 Notion ==========
def add_to_notion(data):
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "运动类型": {"title": [{"text": {"content": data["type"]}}]},
            "距离": {"number": data["distance"]},
            "时长": {"number": data["duration"]},
            "日期": {"date": {"start": data["date"]}},
            "轨迹图": {
                "files": [{
                    "name": "track_image",
                    "external": {"url": data["track_image_url"]}
                }]
            }
        }
    }

    response = requests.post(url, headers=notion_headers, json=payload)
    if response.status_code == 200:
        print(f"✅ 成功同步：{data['date']} - {data['type']}")
    else:
        print(f"❌ 同步失败：{data['date']} 状态码 {response.status_code}")
        print("错误内容：", response.text)

# ========== 主程序 ==========
def main():
    print("🚀 正在开始同步 Keep 数据...")
    token = login_keep(KEEP_MOBILE, KEEP_PASSWORD)
    records = fetch_keep_records(token)
    last_sync = get_last_sync_time()
    new_records = get_new_records(records, last_sync)

    if not new_records:
        print("📭 无需同步，新数据为空。")
        return

    print(f"📌 本次需要同步 {len(new_records)} 条记录")
    for record in new_records:
        add_to_notion(record)

    save_last_sync_time()
    print("🎉 同步完成！")

if __name__ == "__main__":
    main()
