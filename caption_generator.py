"""ECP RMUTI KKC Academic & Motivation Post Generator (S1).

Usage:
    python caption_generator.py

Reads GOOGLE_API_KEY from env. Generates Thai announcements or student motivation posts for ECP RMUTI KKC.
"""

import os
import sys

from dotenv import load_dotenv
from google import genai


PROMPT_TEMPLATE = """\
คุณคือ "น้อง Byte" ผู้ช่วย Content Creator และแอดมินเพจทางการของสาขาวิชาวิศวกรรมคอมพิวเตอร์และอิเล็กทรอนิกส์ คณะวิศวกรรมศาสตร์ มหาวิทยาลัยเทคโนโลยีราชมงคลอีสาน วิทยาเขตขอนแก่น (ECP RMUTI KKC)

หน้าที่ของคุณคือเขียนโพสต์แคปชั่นภาษาไทย 2 ถึง 4 ประโยค เกี่ยวกับหัวข้อ: {topic}

[แนวทางการเขียนตามประเภทเนื้อหา]:
1. 📢 [ประกาศกำหนดการ / วิชาการ / ระบบ ESS]:
   - เช่น วันเพิ่ม-ถอนรายวิชา, กำหนดส่งแบบคำร้อง, กำหนดการสอบ, กำหนดส่ง Senior Project
   - เน้นแจ้งเตือนอย่างชัดเจน กระชับ ระบุวันที่หรือขั้นตอน และเตือนให้นักศึกษาดำเนินการก่อนปิดระบบ
2. 💡 [โพสต์สร้างแรงบันดาลใจ / ให้กำลังใจ]:
   - เช่น ช่วงสอบมิดเทอม-ไฟนอล, ช่วงอดนอนแก้บั๊ก, สัปดาห์ส่งโค้ด
   - โทนเป็นกันเอง อบอุ่น ให้กำลังใจ มีอารมณ์ขันแบบเด็กคอมพ์และอิเล็กทรอนิกส์ ECP
3. ✨ [เงื่อนไขเพิ่มเติม]:
   - มี call-to-action หรือประโยคปิดท้าย เช่น "อย่าลืมตรวจสอบในระบบ ESS นะครับ", "น้อง Byte เอาใจช่วย สู้ๆ นะครับ!", "แท็กเพื่อนมารับทราบด่วน!"
   - ใส่แฮชแท็กที่เกี่ยวข้อง เช่น #ECPRMUTIKKC #ECPKKC #วิศวะคอมขอนแก่น #น้องByte #RMUTIKKC
   - ห้ามใช้ em dash (—)
"""


def generate_caption(topic: str, api_key: str | None = None) -> str:
    """Generate a Thai academic announcement or motivation post for ECP RMUTI KKC students."""
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY not set in env or argument")
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=PROMPT_TEMPLATE.format(topic=topic),
    )

    return response.text or ""


def main() -> int:
    load_dotenv()
    topic = input("หัวข้อประกาศหรือโพสต์สร้างกำลังใจ CPE: ").strip()
    if not topic:
        print("กรุณาระบุหัวข้อประกาศหรือกิจกรรม")
        return 1
    caption = generate_caption(topic)
    print()
    print(caption)
    return 0


if __name__ == "__main__":
    sys.exit(main())

