"""CPE KKC Smart Academic & Student Concierge RAG Chatbot (S3).

Run locally: streamlit run app.py
Deploy: push to GitHub then Actions deploys to HuggingFace Space
"""

import base64
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


def generate_answer(query: str, context_chunks: list[str], is_first_interaction: bool = False) -> str:
    """ส่ง query + context ไปยัง Gemini API พร้อม Guardrails ที่รัดกุม:
    1. หากไม่มีข้อมูลใน context: ตอบอย่างสุภาพว่าไม่ทราบจริงๆ โดยไม่ตอบมั่ว (No hallucination)
    2. หากคำถามกว้างเกินไป: ถามเจาะจงเพื่อจำแนกแบบคำร้อง รายวิชา หรือบริการที่นักศึกษาต้องการ
    3. หากเป็นคำถามเกี่ยวกับความเครียด/สุขภาพจิต: ให้คำแนะนำด้วยความเห็นอกเห็นใจ และแนะนำสายด่วนสุขภาพจิต 1323
    4. หลีกเลี่ยงการกล่าวสวัสดีซ้ำซากหากเป็นการสนทนาต่อเนื่อง
    5. มีระบบ Model Fallback และ Error Handling รองรับกรณี 429 Quota Exceeded
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in env")

    context = "\n\n".join(context_chunks)
    greeting_instruction = (
        "- ข้อความนี้คือการสนทนาเริ่มต้นข้อความแรก: สามารถกล่าวทักทาย 'สวัสดีครับพี่นักศึกษา...' ได้อย่างสุภาพ"
        if is_first_interaction
        else "- ข้อความนี้เป็นการสนทนาต่อเนื่อง: ห้ามกล่าว 'สวัสดีครับ', 'ยินดีต้อนรับ' หรือแนะนำตัวซ้ำโดยเด็ดขาด ให้เข้าสู่เนื้อหาคำตอบตรงประเด็นอย่างสุภาพและเป็นมิตรทันที"
    )

    prompt = f"""\
คุณคือ "น้อง Byte" (Nong Byte) หุ่นยนต์ผู้ช่วยอัจฉริยะประจำระบบ "ECP RMUTI KKC Smart Academic & Student Concierge" สาขาวิชาวิศวกรรมคอมพิวเตอร์และอิเล็กทรอนิกส์ (ECP) คณะวิศวกรรมศาสตร์ มหาวิทยาลัยเทคโนโลยีราชมงคลอีสาน วิทยาเขตขอนแก่น (มทร.อีสาน ขอนแก่น)

[บุคลิกและลักษณะนิสัยของน้อง Byte]:
- น่ารัก สุภาพ เป็นมิตร อบอุ่น กระตือรือร้น และพร้อมช่วยเหลือพี่ๆ และเพื่อนๆ นักศึกษาเสมอ
- แทนตัวเองว่า "น้อง Byte" หรือ "ผม" และเรียกผู้ใช้ว่า "พี่นักศึกษา" หรือ "คุณ" อย่างสุภาพและน่ารัก
- ตอบคำถามโดยใช้ข้อมูลจาก Context ด้านล่างนี้อย่างถูกต้อง แม่นยำ และชัดเจน

[กฎการทักทายและการสนทนา]:
{greeting_instruction}

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
    candidate_models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.7-flash", "gemini-flash-lite-latest"]

    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            if response.text:
                return response.text
        except Exception as err:
            err_str = str(err)
            # If rate limited (429) or unavailable (503), try next model in fallback list
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str:
                continue
            # For other unrecoverable errors, raise or handle
            return f"ขออภัยด้วยนะครับ เกิดข้อผิดพลาดในการเชื่อมต่อ: {err}"

    return "⚠️ ขออภัยครับ ขณะนี้ระบบมีผู้ใช้งานเป็นจำนวนมากจนเกินโควตาชั่วคราว (Rate Limit / Quota Exceeded) กรุณารอสักครู่ (ประมาณ 30-60 วินาที) แล้วลองสอบถามใหม่อีกครั้งนะครับ"


def main():
    st.set_page_config(
        page_title="ECP RMUTI KKC Smart Academic & Student Concierge | น้อง Byte",
        page_icon="🎓",
        layout="centered"
    )

    avatar_path = "assets/byte_avatar.png" if os.path.exists("assets/byte_avatar.png") else "🤖"

    # Centered Header & Welcome Layout
    if os.path.exists("assets/byte_avatar.png"):
        with open("assets/byte_avatar.png", "rb") as f:
            encoded_avatar = base64.b64encode(f.read()).decode()
        avatar_html = f'<img src="data:image/png;base64,{encoded_avatar}" width="90" style="display: block; margin: 0 auto 0.5rem auto;" />'
    else:
        avatar_html = '<div style="font-size: 3.5rem; text-align: center; margin-bottom: 0.5rem;">🤖</div>'

    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            {avatar_html}
            <h1 style="margin: 0; font-size: 2.2rem;">ECP RMUTI KKC Concierge</h1>
            <p style="opacity: 0.85; font-size: 0.95rem; margin: 0.25rem 0 0.75rem 0;">
                🤖 ผู้ช่วยอัจฉริยะประจำสาขา: <b>น้อง Byte</b> (Smart Academic & Student Assistant)
            </p>
            <p style="font-size: 1rem; line-height: 1.6; max-width: 620px; margin: 0 auto;">
                สวัสดีครับ! ผมคือ <b>น้อง Byte</b> ยินดีต้อนรับพี่ๆ นักศึกษาวิศวกรรมคอมพิวเตอร์ มทร.อีสาน วิทยาเขตขอนแก่น ทุกคนครับ ถามข้อมูลหลักสูตร แบบคำร้อง หรือปรึกษาปัญหาการเรียนได้เลยครับ ✨
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Quick Prompt Starter Chips (Action Buttons)
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    quick_prompt = None
    if btn_col1.button("📋 ขั้นตอนยื่นคำร้อง RE", use_container_width=True):
        quick_prompt = "📋 ขั้นตอนยื่นคำร้อง RE"
    if btn_col2.button("📚 ข้อมูลหลักสูตร ECP", use_container_width=True):
        quick_prompt = "📚 ข้อมูลหลักสูตร ECP"
    if btn_col3.button("📅 กำหนดการลงทะเบียน", use_container_width=True):
        quick_prompt = "📅 กำหนดการลงทะเบียน"

    # Sidebar: Form Downloader & Contact Shortcuts
    st.sidebar.title("📥 คลังแบบคำร้อง RE")
    st.sidebar.caption("ดาวน์โหลดไฟล์แบบคำร้อง มทร.อีสาน ขอนแก่น")
    
    forms_dir = Path("forms")
    if forms_dir.exists():
        form_files = sorted([f.name for f in forms_dir.iterdir() if f.is_file()])
        if form_files:
            selected_form = st.sidebar.selectbox("เลือกแบบคำร้องที่ต้องการ:", form_files)
            selected_path = forms_dir / selected_form
            mime_type = "application/pdf" if selected_form.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            with open(selected_path, "rb") as f:
                st.sidebar.download_button(
                    label=f"⬇️ ดาวน์โหลด {selected_form.split('.')[0]}",
                    data=f.read(),
                    file_name=selected_form,
                    mime=mime_type,
                    use_container_width=True
                )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📞 เบอร์ติดต่อด่วน")
    st.sidebar.markdown("""\
- **งานทะเบียน:** `043-283700 กด 8 กด 1610`
- **ขอ Transcript/ใบรับรอง:** `043-283709`
- **งานกองทุน กยศ.:** `095-7158783`
- **ฝ่ายวิชาการคณะวิศวะ:** `064-9384767`
- **💚 สายด่วนสุขภาพจิต:** `1323` (ฟรี 24 ชม.)
""")

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

    chat_input_val = st.chat_input("สอบถามน้อง Byte เกี่ยวกับหลักสูตร ECP, แบบคำร้อง RE, การลงทะเบียน หรือบริการนักศึกษา...")
    prompt = quick_prompt or chat_input_val

    if prompt:
        is_first_interaction = len(st.session_state.messages) == 0
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant", avatar=avatar_path):
            with st.spinner("น้อง Byte กำลังค้นหาข้อมูลให้อยู่นะครับ..."):
                context = retrieve_top_k(prompt, model, index, chunks)
                answer = generate_answer(prompt, context, is_first_interaction=is_first_interaction)
            st.write(answer)
            with st.expander("แหล่งข้อมูลอ้างอิง (Source Chunks)"):
                for i, c in enumerate(context, 1):
                    st.markdown(f"**[{i}]** {c}")
        st.session_state.messages.append({"role": "assistant", "content": answer})



if __name__ == "__main__":
    main()