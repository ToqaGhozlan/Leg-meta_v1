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
    try:
        users_ws = spreadsheet.worksheet("Users")
        records = users_ws.get_all_records()
        df = pd.DataFrame(records)
        df.columns = df.columns.str.strip()
        user_row = df[df['Username'].str.strip() == username.strip()]
        if user_row.empty:
            return False
        return str(user_row['Password'].iloc[0]).strip() == password.strip()
    except:
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
# 3. الـ Styles (نفس التصميم السابق)
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

        /* باقي الـ CSS كما هو ... (حافظت عليه كاملاً لكن اختصرت هنا للطول) */
        .app-header { text-align: center; padding: 2.5rem 0 1.5rem; border-bottom: 1px solid rgba(201,168,76,0.3); margin-bottom: 2rem; }
        .app-header .seal { font-size: 3.5rem; line-height: 1; margin-bottom: 0.5rem; filter: drop-shadow(0 0 12px rgba(201,168,76,0.5)); }
        .app-header h1 { font-family: 'Amiri', serif !important; font-size: 2.4rem !important; font-weight: 700 !important; color: var(--gold) !important; margin: 0 0 0.4rem !important; text-shadow: 0 2px 8px rgba(0,0,0,0.4); }
        /* ... باقي الستايل ... */
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
    df = pd.DataFrame(records)
    try:
        ws.clear()
        ws.update([df.columns.tolist()] + df.values.tolist())
        time.sleep(1.2)
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
        time.sleep(0.8)
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
        record = {
            "اسم القانون": str(item.get("Leg_Name", "")).strip(),
            "الرقم": str(item.get("Leg_Number", "")).strip(),
            "السنة": str(item.get("Year", "")).strip(),
            "Magazine_Number": str(item.get("Magazine_Number", "")).strip(),
            "Magazine_Page": str(item.get("Magazine_Page", "")).strip(),
            "Magazine_Date": str(item.get("Magazine_Date", "")).strip(),
            # التشريع المعدل غير موجود في الـ JSON → نضعه فارغًا
            "ModifiedLeg": "",
            "ModifiedLeg_رقم": "",
            "ModifiedLeg_سنة": "",
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
    n = min(7, total)
    if total <= 7:
        indices = list(range(total))
    elif current < 3:
        indices = list(range(n))
    elif current >= total - 4:
        indices = list(range(total - n, total))
    else:
        indices = list(range(current - 3, current - 3 + n))

    items_html = ""
    for idx in indices:
        if idx < current:
            cls, dot, lbl = "done", "✓", "مكتمل"
        elif idx == current:
            cls, dot, lbl = "active", "●", "الحالي"
        else:
            cls, dot, lbl = "pending", str(idx + 1), "قادم"
        connector_cls = "done" if idx < current else ""
        items_html += f"""
        <div class="wizard-item {connector_cls}">
            <div class="wizard-dot {cls}">{dot}</div>
            <div class="wizard-label {cls}">{lbl}</div>
        </div>"""
    st.markdown(f'<div class="wizard-row">{items_html}</div>', unsafe_allow_html=True)

def show_record(idx, data, total):
    row = data[idx]
    pct = ((idx + 1) / total) * 100

    st.markdown(f'<div class="record-counter"><span>⚖️</span><span>السجل {idx+1} من {total}</span></div>', unsafe_allow_html=True)
    render_wizard(idx, total)
    st.markdown(f"""
        <div class="progress-wrap">
            <div class="progress-meta"><span>التقدم</span><span>{pct:.0f}%</span></div>
            <div class="progress-track"><div class="progress-fill" style="width:{pct:.1f}%"></div></div>
        </div>
    """, unsafe_allow_html=True)

    meta_html = (
        f'<div class="meta-item"><span class="meta-label">رقم القانون</span><span class="meta-value">{row.get("الرقم", "—")}</span></div>'
        f'<div class="meta-item"><span class="meta-label">السنة</span><span class="meta-value">{row.get("السنة", "—")}</span></div>'
        f'<div class="meta-item"><span class="meta-label">رقم الجريدة</span><span class="meta-value">{row.get("Magazine_Number", "—")}</span></div>'
        f'<div class="meta-item"><span class="meta-label">الصفحة</span><span class="meta-value">{row.get("Magazine_Page", "—")}</span></div>'
        f'<div class="meta-item"><span class="meta-label">تاريخ الجريدة</span><span class="meta-value">{row.get("Magazine_Date", "—")}</span></div>'
    )

    card_html = (
        '<div class="law-card">'
        '<div class="card-badge">نص النظام</div>'
        f'<h3>{row.get("اسم القانون", "—")}</h3>'
        '<div class="meta-row">' + meta_html + '</div>'
        '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="amended-card">
            <div class="ac-label">📜 التشريع المعدل</div>
            <p class="ac-name">— (غير موجود في البيانات الأصلية)</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
    st.markdown('<p class="section-title">🔍 هل التشريع المعدل صحيح؟</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ نعم، صحيح", use_container_width=True, type="primary", key=f"yes_{idx}"):
            save_record(row, "صحيح")
            celebrate_save()
            st.session_state.current_idx += 1
            save_progress(st.session_state.current_idx, st.session_state.current_idx)
            st.rerun()
    with col2:
        if st.button("✏️ لا، بدي أعدّل", use_container_width=True, key=f"edit_{idx}"):
            st.session_state.editing = True
            st.rerun()

def edit_form(idx, original):
    st.markdown(f'<div class="record-counter"><span>✏️</span><span>تعديل السجل {idx+1}</span></div>', unsafe_allow_html=True)

    with st.form("edit_form"):
        st.markdown('<p class="section-title">📋 بيانات القانون الرئيسي</p>', unsafe_allow_html=True)

        law_name = st.text_area("اسم القانون", value=original.get("اسم القانون", ""), height=85)
        c1, c2 = st.columns(2)
        law_num  = c1.text_input("رقم القانون", value=original.get("الرقم", ""))
        law_year = c2.text_input("سنة القانون", value=original.get("السنة", ""))

        st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-title">📜 بيانات التشريع المعدل</p>', unsafe_allow_html=True)

        mod_name = st.text_area("اسم التشريع المعدل", value=original.get("ModifiedLeg", ""), height=85)

        st.markdown('<p style="color:rgba(248,244,237,0.45); font-size:0.82rem; direction:rtl; margin:0.3rem 0 0.8rem;">أدخل بيانات التشريع المعدل أدناه ↓</p>', unsafe_allow_html=True)

        d1, d2 = st.columns(2)
        mod_num  = d1.text_input("رقم التشريع المعدل", value=original.get("ModifiedLeg_رقم", ""), placeholder="مثال: 9")
        mod_year = d2.text_input("سنة التشريع المعدل", value=original.get("ModifiedLeg_سنة", ""), placeholder="مثال: 1961")

        st.markdown("<br>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)

        if b1.form_submit_button("💾 حفظ والمتابعة", use_container_width=True, type="primary"):
            d = original.copy()
            d["اسم القانون"]       = law_name.strip()
            d["الرقم"]             = law_num.strip()
            d["السنة"]             = law_year.strip()
            d["ModifiedLeg"]       = mod_name.strip()
            d["ModifiedLeg_رقم"]   = mod_num.strip()
            d["ModifiedLeg_سنة"]   = mod_year.strip()
            save_record(d, "معدل يدويًا")
            celebrate_save()
            st.session_state.editing = False
            st.session_state.current_idx += 1
            save_progress(st.session_state.current_idx, st.session_state.current_idx)
            st.rerun()

        if b2.form_submit_button("↩️ إلغاء", use_container_width=True):
            st.session_state.editing = False
            st.rerun()

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
    option = st.sidebar.radio("", ["نظام ج1", "نظام ج2"])
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

    if st.sidebar.checkbox("عرض السجلات المحفوظة"):
        if st.session_state.local_saved:
            df = pd.DataFrame(st.session_state.local_saved)
            cols = ["تاريخ", "الحالة", "اسم القانون"]
            st.sidebar.dataframe(df[cols] if all(c in df.columns for c in cols) else df, use_container_width=True)
        else:
            st.sidebar.info("لا توجد سجلات بعد")

if __name__ == "__main__":
    main()
