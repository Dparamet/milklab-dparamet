"""ECP RMUTI KKC Student Request Logger (S2).

Usage:
    python sales_logger.py --student_id "66332110001-1" --category "คำร้องเพิ่ม-ถอน" --topic "ขอเพิ่มรายวิชาล่าช้า" --details "วิชา ECP201 เนื่องจากติดปัญหาโอนย้ายสาขา"
"""


import argparse
import json
import os
import sys
from datetime import datetime

import gspread
import requests
from dotenv import load_dotenv

load_dotenv()


def append_to_sheet(student_id: str, category: str, topic: str, details: str) -> dict:
    """บันทึกคำร้องนักศึกษาลง Google Sheet (6 columns: Timestamp, Date, Student_ID, Category, Topic, Details)"""
    
    # Validate
    student_id = str(student_id).strip()
    category = str(category).strip()
    topic = str(topic).strip()
    details = str(details).strip()

    if not student_id:
        raise ValueError("รหัสนักศึกษาห้ามว่าง")
    if not category:
        raise ValueError("หมวดหมู่คำร้องห้ามว่าง")
    if not topic:
        raise ValueError("หัวข้อคำร้องห้ามว่าง")
    if not details:
        raise ValueError("รายละเอียดคำร้องห้ามว่าง")

    # อ่าน JSON จาก Environment Variable
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_json:
        raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS not set in environment")
    
    try:
        creds_dict = json.loads(creds_json)
    except json.JSONDecodeError:
        raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS is not valid JSON")

    # เชื่อมต่อ Sheet
    gc = gspread.service_account_from_dict(creds_dict)
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID not set")
        
    sheet = gc.open_by_key(sheet_id).sheet1

    # คำนวณค่าต่างๆ
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")  # A: Timestamp
    date = now.strftime("%Y-%m-%d")                 # B: Date

    # เพิ่มแถว: [Timestamp, Date, Student_ID, Category, Topic, Details]
    sheet.append_row([timestamp, date, student_id, category, topic, details])

    return {
        "timestamp": timestamp,
        "date": date,
        "student_id": student_id,
        "category": category,
        "topic": topic,
        "details": details
    }


def send_notification(message: str) -> str:
    """ส่งข้อความแจ้งเตือนคำร้องไปยัง Telegram bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message})
    resp.raise_for_status()

    return "telegram"


def main() -> int:
    parser = argparse.ArgumentParser(description="CPE KKC Student Request Logger")
    parser.add_argument("--student_id", required=True, help="รหัสนักศึกษา")
    parser.add_argument("--category", required=True, help="หมวดหมู่คำร้อง")
    parser.add_argument("--topic", required=True, help="หัวข้อคำร้อง")
    parser.add_argument("--details", required=True, help="รายละเอียดคำร้อง")
    args = parser.parse_args()

    try:
        row = append_to_sheet(args.student_id, args.category, args.topic, args.details)
    except Exception as exc:
        print(f"[ERROR] บันทึก Sheet ล้มเหลว: {exc}", file=sys.stderr)
        return 1

    try:
        msg = f"📝 [คำร้องนักศึกษาใหม่]\nรหัส: {args.student_id}\nหมวดหมู่: {args.category}\nเรื่อง: {args.topic}\nรายละเอียด: {args.details}"
        provider = send_notification(msg)
    except Exception as exc:
        print(f"[WARN] บันทึก Sheet สำเร็จแต่ส่งแจ้งเตือนล้มเหลว: {exc}", file=sys.stderr)
        return 0

    print(f"[OK] บันทึกคำร้องรหัส {args.student_id} และแจ้งเตือนผ่าน {provider} เรียบร้อย")
    return 0


if __name__ == "__main__":
    sys.exit(main())