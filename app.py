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
import re

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
# 3. الـ Styles
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

        .app-header {
            text-align: center; padding: 2.5rem 0 1.5rem;
            border-bottom: 1px solid rgba(201,168,76,0.3); margin-bottom: 2rem;
        }
        .app-header .seal {
            font-size: 3.5rem; line-height: 1; margin-bottom: 0.5rem;
            filter: drop-shadow(0 0 12px rgba(201,168,76,0.5));
        }
        .app-header h1 {
            font-family: 'Amiri', serif !important; font-size: 2.4rem !important;
            font-weight: 700 !important; color: var(--gold) !important;
            margin: 0 0 0.4rem !important; text-shadow: 0 2px 8px rgba(0,0,0,0.4);
        }
        .app-header .subtitle {
            color: rgba(248,244,237,0.55) !important; font-size: 0.95rem;
            font-weight: 300; letter-spacing: 2px;
        }

        [data-testid="stAppViewContainer"] {
            flex-direction: row-reverse !important;
        }
        [data-testid="stSidebar"] {
            background: var(--navy-mid) !important;
            border-left: 2px solid rgba(201,168,76,0.3) !important;
            border-right: none !important;
        }
        [data-testid="stSidebarCollapsedControl"] {
            right: 0 !important; left: auto !important;
        }
        [data-testid="stSidebar"] { color: var(--cream) !important; }
        [data-testid="stSidebar"] * {
            color: var(--cream) !important;
            direction: rtl !important;
            text-align: right !important;
        }
        .sidebar-title {
            color: var(--gold) !important; font-family: 'Amiri', serif !important;
            font-size: 1.25rem !important; font-weight: 700 !important;
            border-bottom: 1px solid rgba(201,168,76,0.35);
            padding-bottom: 0.7rem; margin-bottom: 1rem; text-align: right;
        }
        .sidebar-user {
            color: var(--gold) !important; font-weight: 700; font-size: 1.1rem;
            margin: 1rem 0; text-align: center;
        }

        .progress-wrap { margin: 1.5rem 0; }
        .progress-meta {
            display: flex; justify-content: space-between;
            color: rgba(248,244,237,0.6); font-size: 0.82rem;
            margin-bottom: 0.5rem; direction: rtl;
        }
        .progress-track {
            background: rgba(255,255,255,0.08); height: 6px;
            border-radius: 3px; overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--gold), var(--gold-light));
            border-radius: 3px; transition: width 0.5s cubic-bezier(0.4,0,0.2,1);
        }

        .wizard-row {
            display: flex; justify-content: center; align-items: flex-start; gap: 0;
            margin: 1.5rem 0 2rem; direction: ltr;
        }
        .wizard-item {
            display: flex; flex-direction: column; align-items: center;
            position: relative; flex: 1;
        }
        .wizard-item:not(:last-child)::after {
            content: ''; position: absolute; top: 22px; left: 50%;
            width: 100%; height: 2px; background: rgba(255,255,255,0.1); z-index: 0;
        }
        .wizard-item.done::after { background: var(--gold); }
        .wizard-dot {
            width: 44px; height: 44px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 1rem; font-weight: 700; position: relative; z-index: 1;
            border: 2px solid transparent;
        }
        .wizard-dot.done    { background: var(--gold); color: var(--navy); border-color: var(--gold); }
        .wizard-dot.active  { background: transparent; color: var(--gold); border-color: var(--gold); box-shadow: 0 0 0 4px rgba(201,168,76,0.2); }
        .wizard-dot.pending { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.25); border-color: rgba(255,255,255,0.1); }
        .wizard-label { font-size: 0.72rem; margin-top: 6px; font-weight: 500; }
        .wizard-label.done    { color: var(--gold); }
        .wizard-label.active  { color: var(--gold-light); }
        .wizard-label.pending { color: rgba(255,255,255,0.2); }

        .law-card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(201,168,76,0.2); border-radius: 14px;
            padding: 2rem 2rem 1.6rem; margin: 1.2rem 0; direction: rtl;
        }
        .law-card:hover { border-color: rgba(201,168,76,0.45); }
        .law-link-wrap {
            margin-top: 0.9rem; padding-top: 0.7rem;
            border-top: 1px solid rgba(255,255,255,0.07);
        }
        a.law-link {
            color: #e5c97a; font-size: 0.82rem; text-decoration: none; font-weight: 600;
            transition: color 0.2s;
        }
        a.law-link:hover { color: #c9a84c; text-decoration: underline; }
        .law-card .card-badge {
            display: inline-block; background: var(--gold); color: var(--navy);
            font-size: 0.72rem; font-weight: 800; padding: 3px 12px;
            border-radius: 20px; margin-bottom: 0.9rem;
        }
        .law-card h3 {
            font-family: 'Amiri', serif !important; font-size: 1.35rem !important;
            color: var(--cream) !important; font-weight: 700 !important;
            line-height: 1.55; margin: 0 0 1rem !important; text-align: right !important;
        }
        .law-card .meta-row {
            display: flex; gap: 1.5rem; flex-wrap: wrap;
            direction: rtl; justify-content: flex-start;
            margin-top: 0.8rem; padding-top: 0.8rem;
            border-top: 1px solid rgba(255,255,255,0.07);
        }
        .meta-item { display: flex; flex-direction: column; gap: 2px; }
        .meta-label { font-size: 0.72rem; color: rgba(248,244,237,0.4); letter-spacing: 1px; }
        .meta-value { font-size: 0.95rem; color: var(--gold-light); font-weight: 600; }

        .amended-card {
            background: rgba(201,168,76,0.06);
            border: 1px solid rgba(201,168,76,0.3);
            border-right: 4px solid var(--gold); border-radius: 10px;
            padding: 1.5rem 1.8rem; margin: 1.2rem 0; direction: rtl;
        }
        .amended-card .ac-label {
            font-size: 0.75rem; letter-spacing: 1.5px; color: var(--gold);
            font-weight: 700; margin-bottom: 0.8rem; text-align: right !important;
        }
        .amended-card .ac-name {
            color: var(--cream) !important; font-family: 'Amiri', serif !important;
            font-size: 1.1rem !important; line-height: 1.75 !important;
            margin: 0 0 1rem !important; text-align: right !important;
            white-space: pre-wrap !important;
            word-break: break-word !important;
        }

        .record-counter {
            display: inline-flex; align-items: center; gap: 8px;
            background: rgba(201,168,76,0.12); border: 1px solid rgba(201,168,76,0.3);
            border-radius: 30px; padding: 6px 18px;
            color: var(--gold); font-size: 0.9rem; font-weight: 700;
            margin-bottom: 1.2rem; direction: rtl;
        }

        .gold-divider {
            height: 1px; background: linear-gradient(90deg, transparent, var(--gold), transparent);
            margin: 2rem 0; opacity: 0.35;
        }

        .section-title {
            color: var(--cream) !important; font-size: 1rem !important;
            font-weight: 600 !important; margin: 1.5rem 0 0.8rem !important;
            display: flex; align-items: center; gap: 8px; direction: rtl;
        }

        .stButton > button {
            border-radius: 10px !important; font-weight: 700 !important;
            font-size: 1rem !important; padding: 0.65rem 1.2rem !important;
            transition: all 0.2s ease !important; border: none !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--gold) 0%, #b8943d 100%) !important;
            color: var(--navy) !important;
            box-shadow: 0 4px 15px rgba(201,168,76,0.35) !important;
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(201,168,76,0.5) !important;
        }
        .stButton > button:not([kind="primary"]) {
            background: rgba(255,255,255,0.07) !important;
            color: var(--cream) !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
        }
        .stButton > button:not([kind="primary"]):hover {
            background: rgba(255,255,255,0.12) !important;
            border-color: rgba(201,168,76,0.4) !important;
        }

        .stTextInput input, .stTextArea textarea, .stNumberInput input {
            background: rgba(15, 30, 61, 0.8) !important;
            color: #f8f4ed !important;
            border: 1px solid rgba(201,168,76,0.4) !important;
            border-radius: 8px !important;
            direction: rtl !important;
            font-size: 1rem !important;
            caret-color: var(--gold) !important;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
            border-color: var(--gold) !important;
            box-shadow: 0 0 0 3px rgba(201,168,76,0.15) !important;
        }
        .stTextInput label, .stTextArea label, .stNumberInput label {
            color: rgba(248,244,237,0.8) !important;
            font-size: 0.88rem !important; font-weight: 600 !important;
            direction: rtl !important; text-align: right !important;
        }

        [data-testid="stForm"] {
            background: rgba(26,47,90,0.5);
            border: 1px solid rgba(201,168,76,0.2);
            border-radius: 14px; padding: 1.5rem 1.8rem;
        }

        .finish-screen {
            text-align: center; padding: 4rem 2rem; direction: rtl;
        }
        .finish-screen .trophy { font-size: 5rem; margin-bottom: 1rem; }
        .finish-screen h2 {
            font-family: 'Amiri', serif !important; font-size: 2rem !important;
            color: var(--gold) !important; margin-bottom: 0.5rem !important;
        }
        .finish-screen p { color: rgba(248,244,237,0.65) !important; font-size: 1.1rem; }

        #MainMenu, footer, header { visibility: hidden; }
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

def parse_jarida(publication_text: str) -> tuple:
    text = str(publication_text).strip()
    if not text:
        return "—", "—", "—"

    mag_num = "—"
    mag_page = "—"
    mag_date = "—"

    match = re.search(r'رقم\s*(\d+).*?صفحة\s*(\d+).*?بتاريخ\s*([\d-]+)', text, re.IGNORECASE | re.UNICODE)
    if match:
        mag_num, mag_page, mag_date = match.groups()
        return mag_num, mag_page, mag_date

    numbers = re.findall(r'\b\d{3,6}\b', text)
    pages   = re.findall(r'\b\d{1,4}\b', text)
    dates   = re.findall(r'\d{2}-\d{2}-\d{4}', text)

    if numbers:
        mag_num = numbers[0]
    if len(numbers) > 1:
        mag_page = numbers[1]
    elif pages:
        mag_page = pages[-1]

    if dates:
        mag_date = dates[0]

    return mag_num, mag_page, mag_date

@st.cache_data(ttl=300)
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
        publication = str(item.get("Publication", "")).strip()

        # ─── إصلاح المشكلة ───────────────────────────────────────────
        # Bylaws2 يحتوي على مفاتيح جاهزة Magazine_Number / Magazine_Page / Magazine_Date
        # نقرأها مباشرة، وإن لم تكن موجودة نرجع لـ parse_jarida كـ fallback
        mag_num_raw  = str(item.get("Magazine_Number", "")).strip()
        mag_page_raw = str(item.get("Magazine_Page", "")).strip()
        mag_date_raw = str(item.get("Magazine_Date", "")).strip()

        if mag_num_raw or mag_page_raw or mag_date_raw:
            # البيانات موجودة مباشرة في الـ JSON (مثل Bylaws2)
            mag_num  = mag_num_raw  or "—"
            mag_page = mag_page_raw or "—"
            mag_date = mag_date_raw or "—"
        else:
            # fallback لـ parse_jarida (مثل Bylaws1 اللي ما عنده هذه المفاتيح)
            mag_num, mag_page, mag_date = parse_jarida(publication)

        # قراءة ModifiedLeg - نجرب كل الاحتمالات الممكنة للاسم
        modified_leg = (
            str(item.get("ModifiedLeg", "")).strip()
            or str(item.get("modifiedLeg", "")).strip()
            or str(item.get("modified_leg", "")).strip()
            or str(item.get("Modified_Leg", "")).strip()
            or ""
        )
        # ─────────────────────────────────────────────────────────────

        record = {
            "اسم القانون":      str(item.get("Leg_Name", "")).strip(),
            "الرقم":            str(item.get("Leg_Number", "")).strip(),
            "السنة":            str(item.get("Year", "")).strip(),
            "الجريدة الرسمية":  publication,
            "ModifiedLeg":      modified_leg,
            "magazine_number":  mag_num,
            "magazine_page":    mag_page,
            "magazine_date":    mag_date,
            "ModifiedLeg_رقم":  "",
            "ModifiedLeg_سنة":  "",
            "ModifiedLeg_جريدة":"",
            "ModifiedLeg_صفحة": "",
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

    link = row.get("الرابط", "").strip()
    link_html = (
        '<div class="law-link-wrap">'
        f'<a href="{link}" target="_blank" class="law-link">🔗 عرض النص الكامل</a>'
        '</div>'
    ) if link else ""

    meta_html = (
        f'<div class="meta-item"><span class="meta-label">رقم القانون</span><span class="meta-value">{row.get("الرقم", "—")}</span></div>'
        f'<div class="meta-item"><span class="meta-label">السنة</span><span class="meta-value">{row.get("السنة", "—")}</span></div>'
        f'<div class="meta-item"><span class="meta-label">رقم الجريدة</span><span class="meta-value">{row.get("magazine_number", "—")}</span></div>'
        f'<div class="meta-item"><span class="meta-label">الصفحة</span><span class="meta-value">{row.get("magazine_page", "—")}</span></div>'
        f'<div class="meta-item"><span class="meta-label">تاريخ الجريدة</span><span class="meta-value">{row.get("magazine_date", "—")}</span></div>'
    )

    card_html = (
        '<div class="law-card">'
        '<div class="card-badge">نص القانون</div>'
        f'<h3>{row.get("اسم القانون", "—")}</h3>'
        '<div class="meta-row">' + meta_html + '</div>'
        + link_html +
        '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # عرض التشريع المعدل - مع رسالة واضحة إذا كان فارغاً
    modified_leg_value = row.get('ModifiedLeg', '').strip()
    display_value = modified_leg_value if modified_leg_value else "⚠️ لا يوجد تشريع معدل لهذا القانون"

    st.markdown(f"""
        <div class="amended-card">
            <div class="ac-label">📜 التشريع المعدل</div>
            <p class="ac-name">{display_value}</p>
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

    if st.sidebar.button("↻ إعادة تحميل البيانات"):
        st.cache_data.clear()
        st.rerun()

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

