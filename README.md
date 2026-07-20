---
title: MilkLab RAG
emoji: 🥛
colorFrom: blue
colorTo: pink
sdk: streamlit
sdk_version: "1.59.2"
app_file: app.py
pinned: false
---

# MilkLab° Solopreneur Starter (Course 69-1)

Forked from the original owner’s repository and remade by D paramet (@dparamet).

Template repo สำหรับวิชา 31-407-106-406 : AI for Solopreneurs

## Overview

MilkLab° เป็น starter repository สำหรับงานเรียนและโปรเจกต์ย่อยในรายวิชา โดยแยกฟีเจอร์หลักออกเป็น session เพื่อให้พัฒนาและทดสอบได้เป็นขั้นตอน

## Quick Start

1. **Use this template** then create a new repository ตั้งชื่อ `milklab-<ชื่อ>`
2. เปิด **Codespaces** จาก repo ใหม่
3. ตั้ง user-level Codespaces secret `GOOGLE_API_KEY` ตาม Quickstart
4. รัน `python scripts/verify_setup.py` ใน terminal เพื่อเช็กสภาพแวดล้อม

## Project Structure

| ไฟล์ | Session | คำอธิบาย |
|---|---|---|
| `caption_generator.py` | S1 | สร้างแคปชั่นให้โพสต์ MilkLab |
| `sales_logger.py` | S2 | บันทึกยอดขายลง Google Sheets |
| `agent_harness.py` | S2 | รับคำสั่งภาษาไทยและเรียก tool ที่เกี่ยวข้อง |
| `app.py` | S3 | Streamlit RAG chatbot |

## Tech Stack

- Python 3.11
- Gemini API (`google-genai`)
- Streamlit (S3)
- gspread (S2)

## Notes

- Repository นี้เป็นเวอร์ชันที่ fork มาจากต้นฉบับและปรับแต่งต่อโดย D paramet
- ถ้าจะนำไปใช้งานต่อ สามารถแก้ชื่อโปรเจกต์และรายละเอียด course link ได้ตามต้องการ

## Course Link

[course-691-stsw](https://github.com/<owner>/course-691-stsw) (link จะ update ตอนสร้าง public repo)

##
[Rag LLM](https://milklab-dparamet-4ssjvzyftqghymtappy8qwe.streamlit.app/)