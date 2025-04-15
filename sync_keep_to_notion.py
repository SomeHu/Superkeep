import os
import requests
import pendulum
from dotenv import load_dotenv

# ====== 配置 ======
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
KEEP_MOBILE = os.getenv("KEEP_MOBILE")
KEEP_PASSWORD = os.getenv("KEEP_PASSWORD")

# ====== Notion headers ======
notion_headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ====== Keep API config ======
LOGIN_API = "https://api.gotokeep.com/v1.1/users/login"
DATA_API = "https://api.gotokeep.com/pd/v3/stats/detail?dateUnit=all&type=all&lastDate={last_date}"
LOG_API = "https://api.gotokeep.com/pd/v3/{type}log/{id}"

keep_headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
}

# ====== Keep login ======
def login():
    data = {"mobile": KEEP_MOBILE, "password": KEEP_PASSWORD}
    r = requests.post(LOGIN_API, headers=keep_headers, data=data)
    if r.ok:
        print("✅ Keep 登录成功")
        return r.json()["data"]["token"]
    print("❌ Keep 登录失败", r.text)
    return None

# ====== Get all workout logs (basic) ======
def get_all_logs():
    last_date = 0
    logs = []
    while True:
        r = requests.get(DATA_API.format(last_date=last_date), headers=keep_headers)
        if not r.ok:
            break
        data = r.json().get("data", {})
        last_date = data.get("lastTimestamp")
        for record in data.get("records", []):
            for log in record.get("logs", []):
                if log.get("type") == "stats":
                    logs.append(log.get("stats"))
        if not last_date:
            break
    return logs

# ====== Get detailed workout info ======
def get_workout_detail(log):
    url = LOG_API.format(type=log.get("type"), id=log.get("id"))
    r = requests.get(url, headers=keep_headers)
    if not r.ok:
        return None
    return r.json().get("data")

# ====== Check if page with same ID already exists ======
def check_duplicate(workout_id):
    query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "Id",
            "rich_text": {"equals": workout_id}
        }
    }
    r = requests.post(query_url, headers=notion_headers, json=payload)
    if r.ok and r.json().get("results"):
        return True
    return False

# ====== Push to Notion ======
def push_to_notion(item):
    if check_duplicate(item["id"]):
        print(f"⚠️ 重复记录已存在: {item['id']}")
        return

    notion_payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "运动类型": {"title": [{"text": {"content": item["type"]}}]},
            "距离": {"number": item["distance"]},
            "时长": {"number": item["duration"]},
            "日期": {"date": {"start": item["date"]}},
            "Id": {"rich_text": [{"text": {"content": item["id"]}}]}
        },
        "cover": {"external": {"url": item["track"]}}
    }
    r = requests.post("https://api.notion.com/v1/pages", headers=notion_headers, json=notion_payload)
    if r.ok:
        print(f"✅ 同步成功: {item['date']} - {item['type']}")
    else:
        print(f"❌ 同步失败: {item['date']} - {item['type']}\n{r.text}")

# ====== Main ======
def main():
    token = login()
    if not token:
        return
    keep_headers["Authorization"] = f"Bearer {token}"

    from datetime import datetime

START_DATE = datetime(2025, 1, 1)

logs = get_all_logs()
logs = [log for log in logs if log.get("endTime", 0) / 1000 >= START_DATE.timestamp()]
print(f"📦 获取记录 {len(logs)} 条")
    for log in logs:
        detail = get_workout_detail(log)
        if not detail:
            continue
        item = {
            "id": detail.get("id"),
            "type": log.get("name"),
            "distance": round(detail.get("distance", 0), 2),
            "duration": round(detail.get("duration", 0) / 60, 1),
            "date": pendulum.from_timestamp(detail.get("endTime") / 1000, tz="Asia/Shanghai").to_date_string(),
            "track": detail.get("shareImg") or log.get("trackWaterMark")
        }
        push_to_notion(item)

if __name__ == "__main__":
    main()
