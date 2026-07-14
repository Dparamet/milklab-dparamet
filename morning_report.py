"""MilkLab Morning Report (S2).

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
    """สรุปยอดขายของวันที่ระบุจาก rows ที่ส่งเข้ามา (ไม่อ่าน Sheet เอง)"""
    matched = [
        r for r in rows
        if str(r.get("Date") or r.get("date") or r.get("Timestamp", "")).startswith(date)
    ]
    total = sum(float(r.get("Total") or r.get("total") or 0) for r in matched)
    by_menu: dict[str, float] = {}
    for r in matched:
        menu = r.get("Service") or r.get("menu") or "?"
        qty = float(r.get("Quantity") or r.get("qty") or 0)
        by_menu[menu] = by_menu.get(menu, 0) + qty

    return {"date": date, "count": len(matched), "total": total, "by_menu": by_menu}


def format_message(summary: dict) -> str:
    """แปลง summary dict เป็นข้อความ Telegram (pure function, test ได้)"""
    lines = [f"สรุปยอดขายวันที่ {summary['date']}", f"จำนวนบิล: {summary['count']}"]
    for menu, qty in summary["by_menu"].items():
        lines.append(f"- {menu}: {qty:g} ขวด")
    lines.append(f"ยอดรวม: {summary['total']:g} บาท")
    return "\n".join(lines)


def fetch_rows() -> list[dict]:
    """เชื่อมต่อ Google Sheet แล้วดึงข้อมูลทุกแถวกลับมาเป็น list of dict"""
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
    """ส่ง message ไปยัง Telegram bot"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": message})
    resp.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="MilkLab Morning Report")
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