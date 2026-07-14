"""MilkLab Sales Logger (S2).

Usage:
    python sales_logger.py --menu "นมหมีฮอกไกโด" --qty 2 --price 65
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

def append_to_sheet(menu: str, qty: int, price: float) -> dict:
    """เพิ่มข้อมูลลง Google Sheet (6 columns)"""
    
    # Validate
    if not menu or not menu.strip():
        raise ValueError("ชื่อเมนูห้ามว่าง")
    if qty <= 0:
        raise ValueError("จำนวนต้องมากกว่า 0")
    if price < 0:
        raise ValueError("ราคาห้ามติดลบ")

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
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")  # A: Timestamp (วันที่+เวลา)
    date = now.strftime("%Y-%m-%d")                 # B: Date (แค่วันที่)
    service = menu                                  # C: Service
    total = qty * price                             # F: Total

    # เพิ่มแถว: [Timestamp, Date, Service, Price, Quantity, Total]
    sheet.append_row([timestamp, date, service, price, qty, total])

    return {
        "timestamp": timestamp,
        "date": date,
        "service": service,
        "price": price,
        "qty": qty,
        "total": total
    }


def send_notification(message: str) -> str:
    """ส่ง message ไปยัง Telegram bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message})
    resp.raise_for_status()

    return "telegram"


def main() -> int:
    parser = argparse.ArgumentParser(description="MilkLab Sales Logger")
    parser.add_argument("--menu", required=True, help="ชื่อเมนู")
    parser.add_argument("--qty", type=int, required=True, help="จำนวนขวด")
    parser.add_argument("--price", type=float, required=True, help="ราคาต่อขวด")
    args = parser.parse_args()

    try:
        row = append_to_sheet(args.menu, args.qty, args.price)
        total = row["total"]
    except Exception as exc:
        print(f"[ERROR] บันทึก Sheet ล้มเหลว: {exc}", file=sys.stderr)
        return 1

    try:
        provider = send_notification(f"บันทึก {args.menu} x{args.qty} = {total} บาท")
    except Exception as exc:
        print(f"[WARN] บันทึก Sheet สำเร็จแต่ส่งแจ้งเตือนล้มเหลว: {exc}", file=sys.stderr)
        return 0

    print(f"[OK] บันทึกและแจ้งเตือนผ่าน {provider} เรียบร้อย ยอด {total} บาท")
    return 0


if __name__ == "__main__":
    sys.exit(main())