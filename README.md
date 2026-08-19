---
title: ECP RMUTI KKC Smart Academic & Student Concierge
emoji: 🎓
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.59.2"
app_file: app.py
pinned: false
---

# ECP RMUTI KKC Smart Academic & Student Concierge (น้อง Byte 🤖)

ระบบผู้ช่วยอัจฉริยะบริการการศึกษา คำร้อง และสนับสนุนนักศึกษา **"น้อง Byte"** สาขาวิชาวิศวกรรมคอมพิวเตอร์และอิเล็กทรอนิกส์ (ECP) คณะวิศวกรรมศาสตร์ มหาวิทยาลัยเทคโนโลยีราชมงคลอีสาน วิทยาเขตขอนแก่น (มทร.อีสาน ขอนแก่น)

![น้อง Byte](assets/byte_avatar.png)

## Overview

**น้อง Byte** ได้รับการพัฒนาขึ้นเพื่อทำหน้าที่เป็น Concierge ดูแลและช่วยเหลือนักศึกษาสาขาวิชาวิศวกรรมคอมพิวเตอร์และอิเล็กทรอนิกส์ (ECP RMUTI KKC) ในด้านต่างๆ:
- ข้อมูลหลักสูตร วศ.บ. และแผนการเรียน
- แบบฟอร์มคำร้องและขั้นตอนทางทะเบียน (RE Forms เช่น R.04, R.14, R.26)
- รับเรื่องและบันทึกคำร้องนักศึกษาลงระบบ Google Sheet + Telegram Alert อัตโนมัติ
- รับฟังและให้คำปรึกษาปัญหาความเครียด หมดไฟในการเรียน พร้อมส่งต่อสายด่วนสุขภาพจิต 1323

## Project Structure & Architecture

| ไฟล์ / โฟลเดอร์ | Session | หน้าที่และคำอธิบาย |
|---|---|---|
| `assets/byte_avatar.png` | UI | ภาพ Avatar ประจำตัว "น้อง Byte" |
| `knowledge_base/` | S3 | Multi-file Knowledge Base (`01_curriculum.md`, `02_re_forms.md`, `03_mental_health.md`) |
| `app.py` | S3 | Streamlit RAG Chatbot ประจำตัวน้อง Byte พร้อมระบบ FAISS Indexing และ Guardrails |
| `caption_generator.py` | S1 | สร้างโพสต์ประกาศกำหนดการทางวิชาการและแคปชั่นสร้างกำลังใจนักศึกษา ECP |
| `agent_harness.py` | S2 | AI Agent วิเคราะห์คำสั่งภาษาไทยและเรียก Tool จัดการคำร้องนักศึกษา |
| `agent_tools.py` | S2 | Tool Registry, Tool Dispatcher และ Validation Guardrails |
| `sales_logger.py` | S2 | บันทึกคำร้องนักศึกษาลง Google Sheets และส่งแจ้งเตือนผ่าน Telegram |
| `morning_report.py` | S2 | สรุปรายงานคำร้องนักศึกษาประจำวัน |
| `run_tests.py` | Dev | ชุดทดสอบ 7 Test Cases สำหรับตรวจสอบความถูกต้องของ Agent & Guardrails |

## Knowledge Base Sources
1. เว็บไซต์นักศึกษา: [https://web.kkc.rmuti.ac.th/p/student](https://web.kkc.rmuti.ac.th/p/student)
2. แบบฟอร์มดาวน์โหลด: [https://web.kkc.rmuti.ac.th/p/download](https://web.kkc.rmuti.ac.th/p/download)
3. ระบบบริการการศึกษา ESS: [https://ess-register.rmuti.ac.th/AppKK/](https://ess-register.rmuti.ac.th/AppKK/)
4. ข้อมูลหลักสูตรคณะวิศวกรรมศาสตร์: [https://www.eng.rmuti.ac.th](https://www.eng.rmuti.ac.th)

## Tech Stack
- Python 3.11+
- Gemini API (`google-genai`)
- Streamlit (UI)
- Sentence-Transformers & FAISS (RAG Vector Search)
- gspread & Google Sheets API
