import os
import requests
import pendulum
from dotenv import load_dotenv
from datetime import datetime

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

# ====== 获取图标 ======
def get_icon(activity_type):
    icons = {
        "跑步": "🏃",
        "骑行": "🚴",
        "步行": "🥾",
        "徒步": "🥾",
        "力量训练": "🏋️",
        "瑜伽": "🧘‍♀️",
        "自由训练": "🤸",
    }
    return icons.get(activity_type, "🏃")  # 默认图标

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
# ====== Push to Notion ======
def push_to_notion(item):
    if check_duplicate(item["id"]):
        print(f"⚠️ 重复记录已存在: {item['id']}")
        return

    # 获取封面 URL
    cover = item["track"]
    
    # 处理封面 URL
    if cover and len(cover) <= 2000:
        # URL 有效且长度合适，直接使用
        pass
    else:
        # URL 超长或无效，尝试上传或使用默认 URL
        if cover:
            try:
                # 假设 utils.upload_cover 返回短 URL
                cover = utils.upload_cover(cover)
                if not cover or len(cover) > 2000:
                    # 上传失败或仍超长，使用默认 URL
                    cover = "https://images.unsplash.com/photo-1547483238-f400e65ccd56?q=80&w=2970&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
            except Exception as e:
                print(f"⚠️ 封面上传失败: {e}")
                cover = "https://images.unsplash.com/photo-1547483238-f400e65ccd56?q=80&w=2970&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
        else:
            # 无封面 URL，直接使用默认
            cover = "https://images.unsplash.com/photo-1547483238-f400e65ccd56?q=80&w=2970&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"

    # 调试：输出 cover URL 信息
    print(f"调试: cover 长度={len(cover)}, URL={cover}")

    # 构建 Notion 页面数据
    notion_payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "运动类型": {"title": [{"text": {"content": item["type"]}}]},
            "距离": {"number": item["distance"]},
            "时长": {"number": item["duration"]},
            "日期": {"date": {"start": item["date"]}},
            "Id": {"rich_text": [{"text": {"content": item["id"]}}]}
        },
        "cover": {"external": {"url": cover}},
        "icon": {"emoji": get_icon(item["type"])}
    }

    # 直接调用 Notion API
    r = requests.post("https://api.notion.com/v1/pages", headers=notion_headers, json=notion_payload)
    if r.ok:
        print(f"✅ 同步成功: {item['date']} - {item['type']}")
    else:
        print(f"❌ 同步失败: {item['date']} - {item['type']}\n{r.text}")
    # 调用 Notion API 创建页面
    try:
        # 假设 notion_helper.create_page 是一个封装好的函数
        notion_helper.create_page(parent=notion_payload["parent"], properties=notion_payload["properties"], 
                                cover=notion_payload["cover"], icon=notion_payload["icon"])
        print(f"✅ 同步成功: {item['date']} - {item['type']}")
    except Exception as e:
        print(f"❌ 同步失败: {item['date']} - {item['type']}\n{e}")


    # 检查封面图 URL 是否有效，若无则使用默认封面图
    track_url = item["track"]
    if not track_url:
        track_url = "https://raw.githubusercontent.com/SomeHu/Superkeep/main/151.png"  # 默认封面图 URL

    notion_payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "运动类型": {"title": [{"text": {"content": item["type"]}}]},
            "距离": {"number": item["distance"]},
            "时长": {"number": item["duration"]},
            "日期": {"date": {"start": item["date"]}},
            "Id": {"rich_text": [{"text": {"content": item["id"]}}]}
        },
        "cover": {"external": {"url": track_url}},
        "icon": {"emoji": get_icon(item["type"])}
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
