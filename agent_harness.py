# agent_harness.py
"""ECP RMUTI KKC Agent Harness (S2)."""

import argparse
import json
import logging
import os
import sys
from dotenv import load_dotenv
from google import genai
import agent_tools

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    filename='agent_trace.log',
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M',
    encoding='utf-8'
)

TOOL_SCHEMA = [
    {
        "name": "log_student_request",
        "description": "บันทึกคำร้องหรือคำขอนักศึกษาวิศวกรรมคอมพิวเตอร์และอิเล็กทรอนิกส์ (ECP RMUTI KKC): ต้องระบุรหัสนักศึกษา (student_id), หมวดหมู่คำร้อง (category), หัวข้อเรื่อง (topic), และรายละเอียดคำร้อง (details)",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {"type": "string", "description": "รหัสนักศึกษา เช่น 66332110001-1 หรือ 65332110055-4"},
                "category": {"type": "string", "description": "หมวดหมู่คำร้อง เช่น คำร้องเพิ่ม-ถอน, ลาพักการศึกษา, เทียบโอนผลการเรียน, ขอเปิดวิชา, ทั่วไป"},
                "topic": {"type": "string", "description": "หัวข้อหรือชื่อเรื่องคำร้อง เช่น ขอเพิ่มรายวิชาล่าช้า, ขอลาพัก 1 เทอม"},
                "details": {"type": "string", "description": "รายละเอียดหรือเหตุผลของคำร้อง เช่น รายวิชาที่ต้องการเพิ่ม, เหตุผลความจำเป็น"},
            },
            "required": ["student_id", "category", "topic", "details"],
        },
    },
    {
        "name": "get_request_summary",
        "description": "สรุปภาพรวมรายการคำร้องและสถานะคำร้องของนักศึกษา ECP ทั้งหมด",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "send_alert",
        "description": "ส่งข้อความประกาศแจ้งเตือนด่วนทางวิชาการหรือกิจกรรมสาขา ECP ผ่าน Bot",
        "parameters": {
            "type": "object",
            "properties": {"message": {"type": "string", "description": "ข้อความที่ต้องการแจ้งเตือน"}},
            "required": ["message"],
        },
    },
]

SYSTEM_PROMPT = """คุณคือ "ECP KKC Dispatcher Agent" (น้อง Byte Agent) ผู้ช่วยรับคำสั่งและจัดการคำร้องงานบริการนักศึกษา สาขาวิชาวิศวกรรมคอมพิวเตอร์และอิเล็กทรอนิกส์ (ECP) คณะวิศวกรรมศาสตร์ มทร.อีสาน วิทยาเขตขอนแก่น
- หน้าที่ของคุณคือวิเคราะห์คำสั่งภาษาไทยและเรียกใช้ Tool ที่เหมาะสมที่สุด:
  1. หากเป็นคำสั่งให้บันทึก/ยื่น/จดคำร้องนักศึกษา ให้เรียก tool 'log_student_request' พร้อมแยกแยะ (student_id, category, topic, details)
  2. หากเป็นคำสั่งขอสรุปสถานะคำร้อง ให้เรียก tool 'get_request_summary'
  3. หากเป็นคำสั่งส่งแจ้งเตือนหรือประกาศด่วน ให้เรียก tool 'send_alert'
- หากคำสั่งไม่ชัดเจน เป็นเรื่องนอกขอบเขตวิชาการ/คำร้อง หรือเป็นคำสั่งไม่พึงประสงค์ ให้ตอบว่าไม่เข้าใจคำสั่ง"""




def parse_command(cmd: str, api_key: str | None = None) -> dict:
    # Security Guardrail: reject prompt injection / instructions override
    lower_cmd = cmd.lower()
    if "ignore" in lower_cmd or "system prompt" in lower_cmd or "bypass" in lower_cmd or "jailbreak" in lower_cmd:
        return {"tool": "unknown", "args": {"message": cmd}}

    if os.getenv("MOCK_MODE", "false").lower() == "true":
        if "สรุป" in cmd or "สถานะ" in cmd:

            return {"tool": "get_request_summary", "args": {}}
        elif "แจ้งเตือน" in cmd or "ประกาศ" in cmd or "เตือน" in cmd:
            return {"tool": "send_alert", "args": {"message": cmd}}
        elif "บันทึก" in cmd or "ยื่น" in cmd or "คำร้อง" in cmd or "จด" in cmd:
            if "invalid" in cmd or "รหัสผิด" in cmd or "123" in cmd:
                return {
                    "tool": "log_student_request",
                    "args": {
                        "student_id": "123",
                        "category": "คำร้องทั่วไป",
                        "topic": "ขอสอบซ้ำ",
                        "details": "สอบซ้ำวิชาฟิสิกส์"
                    }
                }
            elif "ลาพัก" in cmd:
                return {
                    "tool": "log_student_request",
                    "args": {
                        "student_id": "66332110002-2",
                        "category": "ลาพักการศึกษา",
                        "topic": "ขอลาพักการศึกษา 1 ภาคเรียน",
                        "details": "ติดภารกิจส่วนตัว"
                    }
                }
            else:
                return {
                    "tool": "log_student_request",
                    "args": {
                        "student_id": "66332110001-1",
                        "category": "คำร้องเพิ่ม-ถอน",
                        "topic": "ขอเพิ่มรายวิชาล่าช้า",
                        "details": "ขอเพิ่มรายวิชา CPE201 เนื่องจากติดปัญหาโอนย้ายสาขา"
                    }
                }
        else:
            return {"tool": "unknown", "args": {"message": cmd}}

    try:
        key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY not set")
        client = genai.Client(api_key=key)
        tools = [{"function_declarations": TOOL_SCHEMA}]
        full_cmd = f"{SYSTEM_PROMPT}\n\nUser: {cmd}"
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_cmd,
            config={"tools": tools}
        )
        
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fc = part.function_call
                    return {"tool": fc.name, "args": dict(fc.args)}
        return {"tool": "unknown", "args": {"message": cmd}}
    except Exception as e:
        raise RuntimeError(f"API Error: {e}")


def dispatch_tool(tool_call: dict) -> str:
    tool_name = tool_call['tool']
    if tool_name == 'unknown':
        return "ไม่เข้าใจคำสั่ง"
    
    result = agent_tools.execute_tool(tool_name, tool_call.get('args', {}))
    if not result.get('ok'):
        error_msg = result.get('error', '')
        if 'invalid student_id' in error_msg:
            return "ValueError invalid student_id"
        return f"Error: {error_msg}"
    
    if tool_name == 'log_student_request':
        return "row appended"
    
    return result.get('message', 'success')


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmd", required=True, help="คำสั่งภาษาไทย")
    args = parser.parse_args()

    print(f"[USER] {args.cmd}")
    logging.info(f"user_input | {args.cmd}")

    try:
        tool_call = parse_command(args.cmd)
        logging.info(f'llm_response | {json.dumps(tool_call, ensure_ascii=False)}')

        result = dispatch_tool(tool_call)
        logging.info(f"tool_result | {result}")
        
        print(f"[TOOL] {result}")
        print(f"[USER] <- {result}")

    except Exception as e:
        print(f"[ERROR] {e}")
        logging.info(f"tool_result | ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())