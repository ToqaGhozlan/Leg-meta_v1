import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
import json
import gspread
from google.oauth2.service_account import Credentials
import time
import random

# ────────────────────────────────────────────────
# 1. الاتصال بـ Google Sheets
# ────────────────────────────────────────────────
try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scopes)
    client = gspread.authorize(creds)
    SPREADSHEET_NAME = "Leg_Meta_v2" 
    spreadsheet = client.open(SPREADSHEET_NAME)
except Exception as e:
    st.error("خطأ في الاتصال بـ Google Sheets")
    st.code(str(e))
    st.stop()

# ────────────────────────────────────────────────
# 2. تسجيل الدخول
# ────────────────────────────────────────────────
def authenticate(username: str, password: str) -> bool:
    username = username.strip()
    password = password.strip()
    try:
        users_ws = spreadsheet.worksheet("Users")
        records = users_ws.get_all_records()
        if not records:
            return False
        df = pd.DataFrame(records)
        df.columns = df.columns.str.strip()
        match = df[df['Username'].str.strip() == username]
        if match.empty:
            return False
        stored_pw = str(match['Password'].iloc[0]).strip()
        return stored_pw == password
    except Exception as e:
        st.error("مشكلة في قراءة جدول المستخدمين")
        return False

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_name = None

if not st.session_state.authenticated:
    st.markdown("""
        <div class="app-header">
            <div class="seal">🔐</div>
            <h1>تسجيل الدخول</h1>
            <div class="subtitle">منظومة مراجعة التشريعات</div>
        </div>
    """, unsafe_allow_html=True)

    with st.form("login"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("دخول", use_container_width=True, type="primary"):
            if authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.user_name = username.strip()
                st.rerun()
            else:
                st.error("بيانات الدخول غير صحيحة")
    st.stop()

user_name = st.session_state.user_name

# ────────────────────────────────────────────────
# 3. الـ Styles (باقي كما هو)
# ────────────────────────────────────────────────
def apply_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&family=Tajawal:wght@300;400;500;700;800&display=swap');

        :root {
            --navy:      #0f1e3d;
            --navy-mid:  #1a2f5a;
            --gold:      #c9a84c;
            --gold-light:#e5c97a;
            --cream:     #f8f4ed;
        }

        * { font-family: 'Tajawal', sans-serif !important; }

        .stApp {
            background: var(--navy);
            background-image:
                radial-gradient(ellipse at 80% 10%, rgba(201,168,76,0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 10% 90%, rgba(36,59,110,0.6) 0%, transparent 50%);
            min-height: 100vh;
        }

        .block-container {
            padding: 2rem 3rem !important;
            max-width: 980px !important;
            direction: rtl;
        }

        /* باقي الـ CSS كما هو ... (حذفت التكرار للاختصار) */
        </style>
    """, unsafe_allow_html=True)

apply_styles()

st.sidebar.markdown(f'<div class="sidebar-user">👤 {user_name}</div>', unsafe_allow_html=True)
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.authenticated = False
    st.session_state.user_name = None
    st.rerun()

# ────────────────────────────────────────────────
# 4. دوال Google Sheets
# ────────────────────────────────────────────────
def get_user_worksheet(base_name: str) -> gspread.Worksheet:
    title = f"{user_name}_{base_name}"
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=2000, cols=25)

def save_records(records: list):
    if not records: return
    ws = get_user_worksheet("مراجعة")
    try:
        ws.clear()
        ws.update([list(records[0].keys())] + [list(r.values()) for r in records])
        time.sleep(1.0)
    except Exception as e:
        st.error("خطأ في الحفظ على Google Sheets")
        st.code(str(e))

def load_saved_records() -> list:
    try:
        ws = get_user_worksheet("مراجعة")
        return ws.get_all_records()
    except:
        return []

def save_progress(current: int, max_reached: int):
    ws = get_user_worksheet("تقدم")
    try:
        ws.clear()
        ws.append_row(["current_idx", "max_reached", "last_update"])
        ws.append_row([current, max_reached, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        time.sleep(0.7)
    except:
        pass

def load_progress() -> tuple:
    try:
        ws = get_user_worksheet("تقدم")
        recs = ws.get_all_records()
        if recs:
            last = recs[-1]
            return int(last.get("current_idx", 0)), int(last.get("max_reached", 0))
        return 0, 0
    except:
        return 0, 0

# ────────────────────────────────────────────────
# 5. بيانات JSON + دوال المساعدة
# ────────────────────────────────────────────────
DATA_PATHS = {
    "نظام ج1": r"Bylaws1.json",
    "نظام ج2":  r"Bylaws2.json",
}

def parse_jarida(val: str) -> tuple:
    parts = [p.strip() for p in str(val).split(" - ")]
    if len(parts) >= 3:
        return parts[0], parts[1].replace("ص ", ""), parts[2]
    elif len(parts) == 2:
        return parts[0], parts[1].replace("ص ", ""), "—"
    else:
        return "—", "—", "—"

@st.cache_data
def load_data(kind: str) -> list:
    path = DATA_PATHS.get(kind, "")
    if not path or not os.path.exists(path):
        st.error(f"ملف الداتا غير موجود: {path}")
        st.stop()

    with open(path, encoding="utf-8-sig") as f:
        raw = json.load(f)

    if not isinstance(raw, list) or not raw:
        st.error("الملف فارغ أو ليس list!")
        st.stop()

    records = []
    for item in raw:
        # استخراج بيانات الجريدة
        pub = item.get("Publication", item.get("الجريدة الرسمية", ""))
        mag_num, mag_page, mag_date = parse_jarida(pub)

        record = {
            "اسم القانون": str(item.get("Leg_Name", item.get("اسم القانون", ""))).strip(),
            "الرقم": str(item.get("Leg_Number", item.get("الرقم", ""))).strip(),
            "السنة": str(item.get("Year", item.get("السنة", ""))).strip(),
            "الجريدة الرسمية": pub.strip(),
            
            # التشريع المعدل - الأهم هنا
            "ModifiedLeg": str(item.get("Replaced_By", "")).strip() or 
                           str(item.get("ModifiedLeg", "")).strip() or "",
            
            # الحقول المستخرجة
            "magazine_number": mag_num,
            "magazine_page": mag_page,
            "magazine_date": mag_date,
            
            # حقول التعديل اليدوي (تبدأ فارغة)
            "ModifiedLeg_رقم": "",
            "ModifiedLeg_سنة": "",
            "ModifiedLeg_جريدة": "",
            "ModifiedLeg_صفحة": "",
            "ModifiedLeg_تاريخ": "",
            
            # اختياري
            "الرابط": item.get("Link", item.get("رابط", "")),
        }
        records.append(record)
    
    return records

SAVE_MESSAGES = ["✅ تم الحفظ – كفو!", "✅ شغل نظيف!", "✅ حُفظ بنجاح!", "✅ ممتاز!"]
FINAL_MESSAGES = ["أتممت مراجعة {option} بنجاح", "مراجعة 100% – عمل متقن", "أنجزت المهمة كاملةً"]

def celebrate_save():
    st.success(random.choice(SAVE_MESSAGES))

def celebrate_finish(option):
    st.balloons()
    msg = random.choice(FINAL_MESSAGES).format(option=option)
    st.markdown(f"""
        <div class="finish-screen">
            <div class="trophy">🏛️</div>
            <h2>{msg}</h2>
            <p>جميع السجلات مراجعة ومحفوظة بنجاح</p>
        </div>
    """, unsafe_allow_html=True)

def render_wizard(current, total):
    # باقي الدالة كما هي ...
    pass  # (اختصار)

def show_record(idx, data, total):
    # باقي الدالة كما هي ...
    pass  # (اختصار)

def edit_form(idx, original):
    # باقي الدالة كما هي ...
    pass  # (اختصار)

def save_record(record_dict, status):
    rec = {
        "تاريخ": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "المستخدم": user_name,
        "النوع": st.session_state.get("option", "غير محدد"),
        "الحالة": status,
        **{k: v for k, v in record_dict.items() if v}
    }
    if "local_saved" not in st.session_state:
        st.session_state.local_saved = load_saved_records()
    st.session_state.local_saved.append(rec)
    save_records(st.session_state.local_saved)

# ────────────────────────────────────────────────
# 6. البرنامج الرئيسي
# ────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="منظومة مراجعة التشريعات", layout="wide", page_icon="⚖️")

    st.sidebar.markdown('<div class="sidebar-title">نوع التشريع</div>', unsafe_allow_html=True)
    option = st.sidebar.radio("", ["نظام ج2", "نظام ج1"])
    st.session_state.option = option

    if "current_idx" not in st.session_state:
        st.session_state.current_idx, st.session_state.max_reached = load_progress()
        st.session_state.editing = False
        st.session_state.local_saved = load_saved_records()

    data = load_data(option)
    if not data:
        return

    total = len(data)

    if st.session_state.current_idx >= total:
        celebrate_finish(option)
        if st.button("↺ ابدأ مراجعة جديدة", type="primary"):
            st.session_state.current_idx = 0
            st.session_state.max_reached = 0
            save_progress(0, 0)
            st.session_state.local_saved = []
            save_records([])
            st.rerun()
        return

    if st.session_state.editing:
        edit_form(st.session_state.current_idx, data[st.session_state.current_idx])
    else:
        show_record(st.session_state.current_idx, data, total)

if __name__ == "__main__":
    main()
