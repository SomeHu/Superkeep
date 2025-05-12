import os
import logging
from typing import Optional, List, Dict, Any
import requests
from requests import Session
import pendulum
from dotenv import load_dotenv
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
NOTION_API_URL = "https://api.notion.com/v1"
KEEP_LOGIN_API = "https://api.gotokeep.com/v1.1/users/login"
KEEP_DATA_API = "https://api.gotokeep.com/pd/v3/stats/detail?dateUnit=all&type=all&lastDate={last_date}"
KEEP_LOG_API = "https://api.gotokeep.com/pd/v3/{type}log/{id}"
DEFAULT_COVER_URL = "https://images.unsplash.com/photo-1547483238-f400e65ccd56?q=80&w=2970&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
START_DATE = datetime(2025, 1, 1)

# Headers
NOTION_HEADERS = {
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}
KEEP_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
}

# Activity icons
ACTIVITY_ICONS = {
    "跑步": "🏃", "骑行": "🚴", "步行": "🥾", "徒步": "🥾",
    "力量训练": "🏋️", "瑜伽": "🧘‍♀️", "自由训练": "🤸"
}

def setup_environment() -> tuple[str, str, str, str]:
    """Load and validate environment variables."""
    load_dotenv()
    required_vars = ["NOTION_TOKEN", "NOTION_DATABASE_ID", "KEEP_MOBILE", "KEEP_PASSWORD"]
    env_vars = {var: os.getenv(var) for var in required_vars}
    
    missing_vars = [var for var, value in env_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")
    
    return tuple(env_vars.values())  # type: ignore

def create_session() -> Session:
    """Create a configured requests session."""
    session = Session()
    session.headers.update(KEEP_HEADERS)
    return session

def login(session: Session, mobile: str, password: str) -> Optional[str]:
    """Login to Keep and return token."""
    try:
        response = session.post(KEEP_LOGIN_API, data={"mobile": mobile, "password": password})
        response.raise_for_status()
        logger.info("Keep login successful")
        return response.json()["data"]["token"]
    except requests.RequestException as e:
        logger.error(f"Keep login failed: {str(e)}")
        return None

def get_workout_logs(session: Session) -> List[Dict[str, Any]]:
    """Fetch all workout logs since START_DATE."""
    last_date = 0
    logs = []
    
    while True:
        try:
            response = session.get(KEEP_DATA_API.format(last_date=last_date))
            response.raise_for_status()
            data = response.json().get("data", {})
            last_date = data.get("lastTimestamp")
            
            for record in data.get("records", []):
                for log in record.get("logs", []):
                    if log.get("type") == "stats":
                        logs.append(log.get("stats"))
            
            if not last_date:
                break
        except requests.RequestException as e:
            logger.error(f"Failed to fetch logs: {str(e)}")
            break
    
    return [
        log for log in logs 
        if log.get("endTime", 0) / 1000 >= START_DATE.timestamp()
    ]

def get_workout_detail(session: Session, log: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Fetch detailed workout information."""
    try:
        url = KEEP_LOG_API.format(type=log.get("type"), id=log.get("id"))
        response = session.get(url)
        response.raise_for_status()
        return response.json().get("data")
    except requests.RequestException as e:
        logger.error(f"Failed to fetch workout detail: {str(e)}")
        return None

def check_duplicate(session: Session, database_id: str, workout_id: str) -> bool:
    """Check if workout already exists in Notion."""
    try:
        payload = {
            "filter": {
                "property": "Id",
                "rich_text": {"equals": workout_id}
            }
        }
        response = session.post(
            f"{NOTION_API_URL}/databases/{database_id}/query",
            json=payload
        )
        response.raise_for_status()
        if response.json().get("results"):
            logger.warning(f"Duplicate record found: {workout_id}")
            return True
        return False
    except requests.RequestException as e:
        logger.error(f"Failed to check duplicate: {str(e)}")
        return False

def process_cover_url(cover: Optional[str]) -> str:
    """Process and validate cover URL."""
    if not cover or len(cover) > 2000:
        return DEFAULT_COVER_URL
    return cover

def push_to_notion(session: Session, database_id: str, item: Dict[str, Any]) -> None:
    """Push workout data to Notion."""
    if check_duplicate(session, database_id, item["id"]):
        return

    cover = process_cover_url(item["track"])
    logger.debug(f"Cover URL: length={len(cover)}, url={cover}")

    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "运动类型": {"title": [{"text": {"content": item["type"]}}]},
            "距离": {"number": item["distance"]},
            "时长": {"number": item["duration"]},
            "日期": {"date": {"start": item["date"]}},
            "Id": {"rich_text": [{"text": {"content": item["id"]}}]}
        },
        "cover": {"external": {"url": cover}},
        "icon": {"emoji": ACTIVITY_ICONS.get(item["type"], "🏃")}
    }

    try:
        response = session.post(f"{NOTION_API_URL}/pages", json=payload)
        response.raise_for_status()
        logger.info(f"Successfully synced: {item['date']} - {item['type']}")
    except requests.RequestException as e:
        logger.error(f"Failed to sync: {item['date']} - {item['type']}: {str(e)}")

def main():
    """Main function to sync Keep workouts to Notion."""
    try:
        notion_token, database_id, mobile, password = setup_environment()
        
        with create_session() as keep_session, create_session() as notion_session:
            NOTION_HEADERS["Authorization"] = f"Bearer {notion_token}"
            notion_session.headers.update(NOTION_HEADERS)
            
            token = login(keep_session, mobile, password)
            if not token:
                return
            
            keep_session.headers["Authorization"] = f"Bearer {token}"
            
            logs = get_workout_logs(keep_session)
            logger.info(f"Retrieved {len(logs)} workout records")
            
            for log in logs:
                detail = get_workout_detail(keep_session, log)
                if not detail:
                    continue
                
                item = {
                    "id": detail.get("id"),
                    "type": log.get("name"),
                    "distance": round(detail.get("distance", 0), 2),
                    "duration": round(detail.get("duration", 0) / 60, 1),
                    "date": pendulum.from_timestamp(
                        detail.get("endTime") / 1000, tz="Asia/Shanghai"
                    ).to_date_string(),
                    "track": detail.get("shareImg") or log.get("trackWaterMark")
                }
                
                push_to_notion(notion_session, database_id, item)
                
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")

if __name__ == "__main__":
    main()
