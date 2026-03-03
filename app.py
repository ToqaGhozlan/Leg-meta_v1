import streamlit as st
import json
import html as html_lib
from datetime import datetime
import random
import os
import yaml
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# ────────────────────────────────────────────────
#  Google Sheets Setup
# ────────────────────────────────────────────────
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        creds = Credentials.from_service_account_info(st.secrets["gspread"], scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error("مشكلة في الاتصال بحساب Google → تحقق من st.secrets['gspread']")
        st.stop()

client = get_gspread_client()

SPREADSHEET_NAME = "تعديلات_التشريعات_2025"   # ← غيّر الاسم إذا أردت

@st.cache_resource
def get_or_create_spreadsheet():
    try:
        return client.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        return client.create(SPREADSHEET_NAME)

spreadsheet = get_or_create_spreadsheet()

def get_user_worksheet(username, kind):
    sheet_title = f"{username} - {kind}"
    try:
        return spreadsheet.worksheet(sheet_title)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_title, rows=2000, cols=20)
        # إنشاء العناوين مرة واحدة
        headers = [
            "leg_number", "leg_name", "year", "magazine_number", 
            "magazine_page", "magazine_date", "is_amendment",
            "articles_json", "amended_articles_json", "last_updated"
        ]
        ws.append_row(headers)
        return ws

# ────────────────────────────────────────────────
#  CONSTANTS (نفس السابق)
# ────────────────────────────────────────────────
AMEND_TYPES = ["تعديل مادة", "إضافة مادة", "إلغاء مادة"]
AMEND_BADGE_CSS = {
    "تعديل مادة": "badge-edit",
    "إضافة مادة": "badge-add",
    "إلغاء مادة": "badge-del",
}
LAW_KINDS = ["قانون ج1", "قانون ج2"]

SAVE_MESSAGES = [
    "تم الحفظ ✓", "كفو عليك!", "محفوظ بنجاح", "تمام يا بطل", "عاش!"
]

# ────────────────────────────────────────────────
#  AUTH (نفس السابق تقريباً)
# ────────────────────────────────────────────────
credentials_str = os.environ.get("CREDENTIALS_YAML")
if not credentials_str:
    st.error("لم يتم العثور على CREDENTIALS_YAML")
    st.stop()

try:
    config = yaml.safe_load(credentials_str)
except Exception as e:
    st.error(f"خطأ في yaml: {e}")
    st.stop()

authenticator = stauth.Authenticate(
    credentials=config['credentials'],
    cookie_name=config['cookie']['name'],
    cookie_key=config['cookie']['key'],
    cookie_expiry_days=config['cookie']['expiry_days'],
)

name, authentication_status, username = authenticator.login('تسجيل الدخول', 'main')

if authentication_status:
    st.session_state.user_name = name or username
elif authentication_status is False:
    st.error('اسم المستخدم أو كلمة المرور غير صحيحة')
    st.stop()
elif authentication_status is None:
    st.warning('الرجاء إدخال اسم المستخدم وكلمة المرور')
    st.stop()

# ────────────────────────────────────────────────
#  STYLES (نفس الديزاين الذي أعجبك)
# ────────────────────────────────────────────────
def apply_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&family=Tajawal:wght@300;400;600;700;900&display=swap');
    :root {
        --navy:#0f1e3d;
        --navy-mid:#1a2f5a;
        --gold:#c9a84c;
        --gold-light:#e5c97a;
        --cream:#f8f4ed;
    }
    * {font-family:'Tajawal',sans-serif!important; direction:rtl; text-align:right;}
    .stApp {background:var(--navy);}
    .block-container {max-width:980px!important; padding:2rem 3rem!important;}
    .law-card {background:rgba(255,255,255,.05); border:1px solid rgba(201,168,76,.3); border-radius:14px; padding:1.5rem; margin:1.2rem 0;}
    .article-text {color:var(--cream); line-height:1.9; white-space:pre-wrap;}
    .amend-section {background:rgba(201,168,76,.08); border:1px solid rgba(201,168,76,.4); border-radius:10px; padding:1rem; margin:0.8rem 0;}
    .badge-edit {background:rgba(59,130,246,.2); color:#93c5fd;}
    .badge-add {background:rgba(34,197,94,.2); color:#86efac;}
    .badge-del {background:rgba(239,68,68,.2); color:#fca5a5;}
    .amend-badge {padding:4px 12px; border-radius:20px; font-size:.75rem; font-weight:700;}
    </style>
    """, unsafe_allow_html=True)

apply_styles()

# ────────────────────────────────────────────────
#  Data Helpers
# ────────────────────────────────────────────────
def row_to_law(row):
    return {
        "leg_number": row["leg_number"],
        "leg_name": row["leg_name"],
        "year": row["year"],
        "magazine_number": row["magazine_number"],
        "magazine_page": row["magazine_page"],
        "magazine_date": row["magazine_date"],
        "is_amendment": row["is_amendment"],
        "Articles": json.loads(row["articles_json"] or "[]"),
        "amended_articles": json.loads(row["amended_articles_json"] or "[]")
    }

def load_laws(kind):
    ws = get_user_worksheet(st.session_state.user_name, kind)
    data = ws.get_all_records()
    
    # إذا الورقة فارغة → تهيئة من JSON
    if len(data) <= 1:  # فقط header
        json_filename = "V02_Laws_P1.json" if kind == "قانون ج1" else "V02_Laws_P2.json"
        json_path = f"app/{json_filename}"   # ← تأكد من المسار
        
        if not os.path.exists(json_path):
            st.error(f"ملف JSON غير موجود: {json_path}")
            return []
            
        with open(json_path, encoding="utf-8-sig") as f:
            raw_data = json.load(f)
            
        rows_to_add = []
        for law in raw_data:
            row = [
                law.get("Leg_Number", ""),
                law.get("Leg_Name", ""),
                law.get("Year", ""),
                law.get("Magazine_Number", ""),
                law.get("Magazine_Page", ""),
                law.get("Magazine_Date", ""),
                law.get("is_amendment", False),
                json.dumps(law.get("Articles", []), ensure_ascii=False),
                json.dumps(law.get("amended_articles", []), ensure_ascii=False),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ]
            rows_to_add.append(row)
        
        if rows_to_add:
            ws.append_rows(rows_to_add)
            st.success(f"تم تهيئة {kind} من الملف الأصلي ({len(rows_to_add)} قانون)")
            # إعادة قراءة بعد الإضافة
            data = ws.get_all_records()
    
    laws = [row_to_law(r) for r in data if r.get("leg_number")]
    return laws

def save_law(law, kind):
    ws = get_user_worksheet(st.session_state.user_name, kind)
    data = ws.get_all_records()
    
    leg_number = law["leg_number"]
    row_index = None
    
    for i, row in enumerate(data, start=2):  # +1 لأن get_all_records يتجاهل header
        if row.get("leg_number") == leg_number:
            row_index = i
            break
    
    row_data = [
        law["leg_number"],
        law["leg_name"],
        law["year"],
        law["magazine_number"],
        law["magazine_page"],
        law["magazine_date"],
        law["is_amendment"],
        json.dumps(law["Articles"], ensure_ascii=False),
        json.dumps(law["amended_articles"], ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ]
    
    if row_index:
        ws.update(f"A{row_index}:J{row_index}", [row_data])
    else:
        ws.append_row(row_data)
    
    st.toast(random.choice(SAVE_MESSAGES), icon="✅")

# ────────────────────────────────────────────────
#  UI Functions (نفس السابق مع تعديل طفيف)
# ────────────────────────────────────────────────
def show_law(idx, laws, kind):
    law = laws[idx]
    st.markdown(f"""
    <div class="law-card">
        <h3>{html_lib.escape(law["leg_name"])}</h3>
        <p>رقم: {law["leg_number"]}  |  سنة: {law["year"]}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📜 المواد")
    articles = law["Articles"]
    if not articles:
        if st.button("➕ إضافة أول مادة"):
            add_article(law, kind, position=0)
        return
    
    options = [f"المادة {a['article_number']}" for a in articles]
    art_idx = st.selectbox("", range(len(options)), format_func=lambda i: options[i], key=f"art_{idx}")
    art = articles[art_idx]
    
    st.markdown(f"""
    <div class="law-card">
        <b>{art["title"]}</b>
        <div class="article-text">{html_lib.escape(art["text"])}</div>
        <small>تاريخ النفاذ: {art["enforcement_date"]}</small>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✏️ تعديل المادة"):
            edit_article(law, art_idx, kind)
    with col2:
        if st.button("➕ إضافة مادة بعد هذه"):
            add_article(law, kind, position=art_idx + 1)
    with col3:
        if st.button("➕ إضافة مادة في النهاية"):
            add_article(law, kind, position=len(articles))
    
    st.markdown("### 🔄 التعديلات التشريعية")
    amended = law["amended_articles"]
    if amended:
        for amend in amended:
            badge_class = AMEND_BADGE_CSS.get(amend["type"], "")
            st.markdown(f"""
            <div class="amend-section">
                <span class="amend-badge {badge_class}">{amend["type"]}</span>
                <b>المادة: {amend.get("article_number", "")}</b>
                <div>{html_lib.escape(amend.get("text", ""))}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("لا توجد تعديلات تشريعية بعد.")
    
    if st.button("➕ إضافة تعديل تشريعي"):
        add_amendment(law, kind)

# ────────────────────────────────────────────────
#  نماذج الإضافة / التعديل (نفس السابق)
# ────────────────────────────────────────────────
def add_article(law, kind, position):
    with st.form(key=f"add_art_{kind}_{position}"):
        st.subheader("إضافة مادة جديدة")
        articles = law["Articles"]
        suggested = str(len(articles) + 1) if position == len(articles) else ""
        num = st.text_input("الرقم", value=suggested)
        title = st.text_input("العنوان", value=f"المادة {num}")
        date = st.text_input("تاريخ النفاذ", value=datetime.now().strftime("%d-%m-%Y"))
        text = st.text_area("النص", height=280)
        col1, col2 = st.columns(2)
        if col1.form_submit_button("💾 حفظ"):
            new_art = {"article_number": num, "title": title, "enforcement_date": date, "text": text}
            law["Articles"].insert(position, new_art)
            save_law(law, kind)
            st.rerun()
        if col2.form_submit_button("إلغاء"):
            st.rerun()

def edit_article(law, idx, kind):
    art = law["Articles"][idx]
    with st.form(key=f"edit_art_{kind}_{idx}"):
        st.subheader("تعديل المادة")
        num = st.text_input("الرقم", art["article_number"])
        title = st.text_input("العنوان", art["title"])
        date = st.text_input("تاريخ النفاذ", art["enforcement_date"])
        text = st.text_area("النص", art["text"], height=280)
        col1, col2 = st.columns(2)
        if col1.form_submit_button("💾 حفظ"):
            law["Articles"][idx] = {"article_number": num, "title": title, "enforcement_date": date, "text": text}
            save_law(law, kind)
            st.rerun()
        if col2.form_submit_button("إلغاء"):
            st.rerun()

def add_amendment(law, kind):
    with st.form(key=f"add_amend_{kind}"):
        st.subheader("إضافة تعديل تشريعي")
        amend_type = st.selectbox("نوع التعديل", AMEND_TYPES)
        article_num = st.text_input("رقم المادة المعدلة")
        text = st.text_area("نص التعديل", height=180)
        col1, col2 = st.columns(2)
        if col1.form_submit_button("💾 حفظ"):
            new_amend = {"type": amend_type, "article_number": article_num, "text": text}
            law["amended_articles"].append(new_amend)
            save_law(law, kind)
            st.rerun()
        if col2.form_submit_button("إلغاء"):
            st.rerun()

# ────────────────────────────────────────────────
#  MAIN
# ────────────────────────────────────────────────
def main():
    st.set_page_config("مراجعة التشريعات", layout="wide", page_icon="⚖️")
    
    st.sidebar.markdown(f"👤 {st.session_state.user_name}")
    authenticator.logout("تسجيل الخروج", "sidebar")
    
    st.sidebar.markdown("### نوع القانون")
    kind = st.sidebar.radio("", LAW_KINDS)
    
    laws = load_laws(kind)
    if not laws:
        st.warning(f"لا توجد بيانات لـ {kind}")
        return
    
    if "current_idx" not in st.session_state:
        st.session_state.current_idx = 0
    
    idx = st.session_state.current_idx
    show_law(idx, laws, kind)
    
    col1, col2 = st.columns(2)
    with col1:
        if idx > 0 and st.button("◄ السابق"):
            st.session_state.current_idx -= 1
            st.rerun()
    with col2:
        if idx < len(laws)-1 and st.button("التالي ►", type="primary"):
            st.session_state.current_idx += 1
            st.rerun()

if __name__ == "__main__":
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    main()
