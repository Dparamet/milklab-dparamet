"""CPE KKC Smart Academic & Student Concierge RAG Chatbot (S3).

Run locally: streamlit run app.py
Deploy: push to GitHub then Actions deploys to HuggingFace Space
"""

import glob
import os
from pathlib import Path

import faiss
import streamlit as st
from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer

load_dotenv()


@st.cache_resource
def load_index():
    """โหลดไฟล์ทั้งหมดจาก knowledge_base/ (.md), split เป็น chunk ตาม heading '## ',
    encode ด้วย sentence-transformers และสร้าง FAISS index.

    Returns: (model, index, chunks_list)
    """
    kb_dir = Path("knowledge_base")
    md_files = sorted(glob.glob(str(kb_dir / "*.md")))
    if not md_files:
        # Fallback to any markdown files in root if knowledge_base is missing
        md_files = sorted(glob.glob("*.md"))

    all_chunks = []
    for filepath in md_files:
        with open(filepath, encoding="utf-8") as f:
            text = f.read()

        raw_sections = text.split("\n## ")
        file_chunks = [raw_sections[0].strip()]
        file_chunks += ["## " + s.strip() for s in raw_sections[1:]]
        file_chunks = [c for c in file_chunks if c]
        all_chunks.extend(file_chunks)

    if not all_chunks:
        all_chunks = ["ไม่มีข้อมูลใน Knowledge Base"]

    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    embeddings = model.encode(all_chunks, convert_to_numpy=True).astype("float32")

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    return model, index, all_chunks


def retrieve_top_k(query: str, model, index, chunks: list[str], k: int = 3) -> list[str]:
    """Encode query, search index, return top-k context chunks."""
    query_vec = model.encode([query], convert_to_numpy=True).astype("float32")
    _, indices = index.search(query_vec, k)
    return [chunks[i] for i in indices[0] if i != -1]


def generate_answer(query: str, context_chunks: list[str]) -> str:
    """ส่ง query + context ไปยัง Gemini API พร้อม Guardrails ที่รัดกุม:
    1. หากไม่มีข้อมูลใน context: ตอบอย่างสุภาพว่าไม่ทราบจริงๆ โดยไม่ตอบมั่ว (No hallucination)
    2. หากคำถามกว้างเกินไป: ถามเจาะจงเพื่อจำแนกแบบคำร้อง รายวิชา หรือบริการที่นักศึกษาต้องการ
    3. หากเป็นคำถามเกี่ยวกับความเครียด/สุขภาพจิต: ให้คำแนะนำด้วยความเห็นอกเห็นใจ และแนะนำสายด่วนสุขภาพจิต 1323
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in env")

    context = "\n\n".join(context_chunks)
    prompt = f"""\
คุณคือ "น้อง Byte" (Nong Byte) หุ่นยนต์ผู้ช่วยอัจฉริยะประจำระบบ "ECP RMUTI KKC Smart Academic & Student Concierge" สาขาวิชาวิศวกรรมคอมพิวเตอร์และอิเล็กทรอนิกส์ (ECP) คณะวิศวกรรมศาสตร์ มหาวิทยาลัยเทคโนโลยีราชมงคลอีสาน วิทยาเขตขอนแก่น (มทร.อีสาน ขอนแก่น)

[บุคลิกและลักษณะนิสัยของน้อง Byte]:
- น่ารัก สุภาพ เป็นมิตร อบอุ่น กระตือรือร้น และพร้อมช่วยเหลือพี่ๆ และเพื่อนๆ นักศึกษาเสมอ
- แทนตัวเองว่า "น้อง Byte" หรือ "ผม" และเรียกผู้ใช้ว่า "พี่นักศึกษา" หรือ "คุณ" อย่างสุภาพและน่ารัก
- ตอบคำถามโดยใช้ข้อมูลจาก Context ด้านล่างนี้อย่างถูกต้อง แม่นยำ และชัดเจน

[กฎเหล็กและแนวทางการตอบ (Strict Guardrails)]:
1. 🛡️ [ไม่มีข้อมูลใน Context / ข้อมูลไม่เพียงพอ]:
   - ห้ามเดาหรือแต่งข้อมูลขึ้นมาเองโดยเด็ดขาด (Zero Hallucination)
   - ให้ตอบอย่างสุภาพว่า: "เรื่องนี้น้อง Byte ยังไม่มีข้อมูลในระบบจริงๆ ต้องขออภัยด้วยนะครับ..."
   - แนะนำช่องทางติดต่อทางการ: แผนกงานวิชาการและงานทะเบียน คณะวิศวกรรมศาสตร์ มทร.อีสาน วิทยาเขตขอนแก่น (โทร. 043-283707 หรือระบบ ESS: ess-register.rmuti.ac.th)

2. 🔍 [คำถามกว้างเกินไป / คลุมเครือ]:
   - เช่น "ขอคำร้อง", "ลงทะเบียนยังไง", "มีวิชาอะไรบ้าง"
   - ให้น้อง Byte ตอบภาพรวมสั้นๆ พร้อมถามคำถามเจาะจงกลับเพื่อช่วยจำแนกความต้องการ เช่น พี่นักศึกษาต้องการแบบคำร้องเรื่องใด (เช่น R.04 ลาพักการศึกษา, R.14 เพิ่ม-ถอนล่าช้า, R.26 เทียบโอนผลการเรียน) หรือกำลังศึกษาอยู่ชั้นปีไหน

3. 💚 [ความเครียด หมดไฟ หรือปัญหาสุขภาพจิต]:
   - น้อง Byte จะรับฟังด้วยความอบอุ่น เข้าอกเข้าใจ ไม่ตัดสิน และส่งพลังบวกให้เสมอ
   - แนะนำช่องทางช่วยเหลือทันที: สายด่วนสุขภาพจิต 1323 (โทรฟรีตลอด 24 ชั่วโมง), หน่วยแนะแนวกองพัฒนานักศึกษา และอาจารย์ที่ปรึกษาประจำสาขา ECP

4. 📋 [รูปแบบการตอบ]:
   - ใช้ภาษาไทยที่น่ารัก สุภาพ อ่านง่าย มีการจัดหัวข้อย่อย (Bullet points)
   - ระบุรหัสแบบฟอร์ม (เช่น R.04, R.14) หรือชื่อวิชา/ลิงก์ระบบที่เกี่ยวข้องให้ชัดเจน

Context:
{context}

คำถามของนักศึกษา: {query}
คำตอบจากน้อง Byte:"""

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text or ""


def main():
    st.set_page_config(
        page_title="ECP RMUTI KKC Smart Academic & Student Concierge | น้อง Byte",
        page_icon="🎓",
        layout="centered"
    )

    avatar_path = "assets/byte_avatar.png" if os.path.exists("assets/byte_avatar.png") else "🤖"

    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists("assets/byte_avatar.png"):
            st.image("assets/byte_avatar.png", width=95)
        else:
            st.markdown("# 🤖")
    with col2:
        st.title("ECP RMUTI KKC Concierge")
        st.caption("🤖 ผู้ช่วยอัจฉริยะประจำสาขา: **น้อง Byte** (Smart Academic & Student Assistant)")

    st.markdown("สวัสดีครับ! ผมคือ **น้อง Byte** ยินดีต้อนรับพี่ๆ นักศึกษาวิศวกรรมคอมพิวเตอร์และอิเล็กทรอนิกส์ มทร.อีสาน วิทยาเขตขอนแก่น ทุกคนครับ ถามข้อมูลหลักสูตร แบบคำร้อง หรือปรึกษาปัญหาการเรียนได้เลยครับ ✨")

    try:
        model, index, chunks = load_index()
    except Exception as exc:
        st.error(f"Error loading Knowledge Base: {exc}")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        role = msg["role"]
        current_avatar = avatar_path if role == "assistant" else None
        with st.chat_message(role, avatar=current_avatar):
            st.write(msg["content"])

    if prompt := st.chat_input("สอบถามน้อง Byte เกี่ยวกับหลักสูตร ECP, แบบคำร้อง RE, การลงทะเบียน หรือบริการนักศึกษา..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant", avatar=avatar_path):
            with st.spinner("น้อง Byte กำลังค้นหาข้อมูลให้อยู่นะครับ..."):
                context = retrieve_top_k(prompt, model, index, chunks)
                answer = generate_answer(prompt, context)
            st.write(answer)
            with st.expander("แหล่งข้อมูลอ้างอิง (Source Chunks)"):
                for i, c in enumerate(context, 1):
                    st.markdown(f"**[{i}]** {c}")
        st.session_state.messages.append({"role": "assistant", "content": answer})



if __name__ == "__main__":
    main()