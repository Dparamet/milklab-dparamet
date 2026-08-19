"""ECP RMUTI KKC Student Requests Daily Report (S2).

Usage:
    python morning_report.py --date 2026-07-14
    python morning_report.py --date 2026-07-14 --dry-run
"""

import argparse
import json
import os
import sys
from datetime import date as date_cls

import gspread
import requests
from dotenv import load_dotenv

load_dotenv()


def summarize_for_date(rows: list[dict], date: str) -> dict:
    """สรุปคำร้องนักศึกษาของวันที่ระบุจาก rows ที่ส่งเข้ามา"""
    matched = [
        r for r in rows
        if str(r.get("Date") or r.get("date") or r.get("Timestamp", "")).startswith(date)
    ]
    by_category: dict[str, int] = {}
    for r in matched:
        cat = r.get("Category") or r.get("category") or "ทั่วไป"
        by_category[cat] = by_category.get(cat, 0) + 1

    return {"date": date, "count": len(matched), "by_category": by_category}


def format_message(summary: dict) -> str:
    """แปลง summary dict เป็นข้อความรายงานสรุปคำร้องนักศึกษา"""
    lines = [f"📊 สรุปรายการคำร้องนักศึกษา ECP RMUTI KKC ประจำวันที่ {summary['date']}", f"จำนวนคำร้องทั้งหมด: {summary['count']} รายการ"]
    if summary["by_category"]:
        lines.append("แยกตามหมวดหมู่:")
        for cat, count in summary["by_category"].items():
            lines.append(f"- {cat}: {count} รายการ")
    else:
        lines.append("ไม่มีรายการคำร้องในวันดังกล่าว")
    return "\n".join(lines)



def fetch_rows() -> list[dict]:
    """เชื่อมต่อ Google Sheet แล้วดึงข้อมูลคำร้องทุกแถวกลับมาเป็น list of dict"""
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not creds_json:
        raise RuntimeError("GOOGLE_SHEETS_CREDENTIALS not set in environment")
    creds_dict = json.loads(creds_json)

    gc = gspread.service_account_from_dict(creds_dict)
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID not set")

    return gc.open_by_key(sheet_id).sheet1.get_all_records()


def send_notification(message: str) -> None:
    """ส่ง message สรุปคำร้องไปยัง Telegram bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message})
    resp.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="CPE KKC Student Requests Daily Report")
    parser.add_argument("--date", default=date_cls.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="พิมพ์ข้อความแทนการส่ง Telegram")
    args = parser.parse_args()

    try:
        rows = fetch_rows()
    except Exception as exc:
        print(f"[ERROR] อ่าน Sheet ล้มเหลว: {exc}", file=sys.stderr)
        return 1

    summary = summarize_for_date(rows, args.date)
    message = format_message(summary)

    if args.dry_run:
        print(f"[DRY-RUN]\n{message}")
        return 0

    try:
        send_notification(message)
    except Exception as exc:
        print(f"[ERROR] ส่งแจ้งเตือนล้มเหลว: {exc}", file=sys.stderr)
        return 1

    print(f"[OK] ส่งรายงานแล้ว\n{message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())