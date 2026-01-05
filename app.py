"""
نظام مراجعة التشريعات القانونية
مراجعة وتصحيح بيانات قسطاس - مع تسجيل دخول وحفظ دائم على Google Sheets
جاهز للعمل 100% - يناير 2026
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import time
import random

# ==================== ربط Google Sheets ====================
try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["google"], scopes=scopes)
    client = gspread.authorize(creds)
    SPREADSHEET_NAME = "Diwan_Legs"
    st.info("جاري الاتصال بـ Google Sheets...")
    spreadsheet = client.open(SPREADSHEET_NAME)
    st.success("✔️ تم الاتصال بنجاح بـ Google Sheets!")
except gspread.exceptions.SpreadsheetNotFound:
    st.error("❌ الملف 'Diwan_Legs' مش موجود. تأكد من الاسم أو أنشئه يدويًا.")
    st.stop()
except Exception as e:
    st.error("❌ خطأ في الاتصال بـ Google Sheets")
    st.code(str(e))
    st.stop()

# ==================== دوال تسجيل الدخول ====================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username: str, password: str) -> bool:
    try:
        users_ws = spreadsheet.worksheet("Users")
        records = users_ws.get_all_records()
        if not records:
            return False
        users_df = pd.DataFrame(records)
        users_df.columns = users_df.columns.str.strip()
        if 'Username' not in users_df.columns or 'Password' not in users_df.columns:
            return False
        user_row = users_df[users_df['Username'] == username]
        if user_row.empty:
            return False
        stored_password = user_row['Password'].iloc[0]
        return password == stored_password
    except:
        return False

# ==================== جلسة تسجيل الدخول ====================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_name = None

if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center; color: #667eea;'>🔐 تسجيل الدخول</h1>", unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("اسم المستخدم", placeholder="مثال: user1")
        password = st.text_input("كلمة المرور", type="password")
        submit = st.form_submit_button("دخول", use_container_width=True)
        if submit:
            if authenticate(username, password):
                st.session_state.authenticated = True
                st.session_state.user_name = username
                st.success(f"✅ مرحباً {username}!")
                st.rerun()
            else:
                st.error("❌ بيانات الدخول غير صحيحة")
    st.stop()

user_name = st.session_state.user_name
st.sidebar.success(f"👤 المستخدم: {user_name}")
if st.sidebar.button("تسجيل الخروج"):
    st.session_state.authenticated = False
    st.session_state.user_name = None
    st.rerun()

# ==================== إعدادات الصفحة ====================
st.set_page_config(
    page_title="نظام مراجعة التشريعات",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("نوع التشريع")
option = st.sidebar.radio("اختر نوع البيانات:", ["نظام", "قانون"])

# ==================== دوال Google Sheets ====================
def get_worksheet(base_name: str, suffix: str = ""):
    sheet_title = f"{user_name}_{base_name}"
    if suffix:
        sheet_title += f"_{suffix}"
    try:
        return spreadsheet.worksheet(sheet_title)
    except gspread.exceptions.WorksheetNotFound:
        st.info(f"إنشاء ورقة جديدة: {sheet_title}")
        return spreadsheet.add_worksheet(title=sheet_title, rows=1000, cols=30)

def save_to_gsheet(data: list, base_name: str):
    ws = get_worksheet(base_name)
    if not data:
        ws.clear()
        ws.append_row(["لا توجد بيانات محفوظة"])
        return
    df = pd.DataFrame(data)
    df = df.fillna("")
    df = df.astype(str)
    try:
        ws.clear()
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        time.sleep(1.5)
    except Exception as e:
        st.error("خطأ في الحفظ على Google Sheets")
        st.code(str(e))

def load_from_gsheet(base_name: str) -> list:
    try:
        ws = get_worksheet(base_name)
        records = ws.get_all_records()
        return records if records else []
    except:
        return []

def get_progress_worksheet():
    sheet_title = f"{user_name}_تقدم_{option}"
    try:
        return spreadsheet.worksheet(sheet_title)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_title, rows=100, cols=3)
        ws.append_row(["current_index", "max_reached_idx", "last_updated"])
        ws.append_row(["0", "0", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return ws

def save_progress(current_idx: int, max_reached: int):
    ws = get_progress_worksheet()
    try:
        ws.clear()
        ws.append_row(["current_index", "max_reached_idx", "last_updated"])
        ws.append_row([str(current_idx), str(max_reached), datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        time.sleep(1)
    except:
        pass

def load_progress() -> tuple[int, int]:
    try:
        ws = get_progress_worksheet()
        records = ws.get_all_records()
        if records:
            last = records[-1]
            return int(last.get("current_index", 0)), int(last.get("max_reached_idx", 0))
        return 0, 0
    except:
        return 0, 0

# ==================== Session Manager ====================
class SessionManager:
    @staticmethod
    def get_unique_key(base: str) -> str:
        return f"{base}_{option}_{user_name}"

    @staticmethod
    def initialize():
        comp_key = SessionManager.get_unique_key("comparison_data")
        idx_key = SessionManager.get_unique_key("current_index")
        max_key = SessionManager.get_unique_key("max_reached_idx")
        if comp_key not in st.session_state:
            st.session_state[comp_key] = load_from_gsheet(option)
        current_idx, max_reached = load_progress()
        st.session_state[idx_key] = current_idx
        st.session_state[max_key] = max_reached
        st.session_state.show_custom_form = False
        save_progress(current_idx, max_reached)

    @staticmethod
    def save_persistent():
        comp_key = SessionManager.get_unique_key("comparison_data")
        save_to_gsheet(st.session_state[comp_key], option)

def initialize_session_state():
    SessionManager.initialize()

def save_persistent_data():
    SessionManager.save_persistent()

# ==================== تحميل بيانات قسطاس ====================
@st.cache_data
def load_qis_data(kind: str):
    PATHS = {
        'نظام': r'V02_All_Legs/V10_Bylaws.xlsx',
        'قانون': r'V02_All_Legs/V05_Laws.xlsx',
    }
    if kind not in PATHS:
        st.error("النوع غير مدعوم.")
        return None
    path = PATHS[kind]
    if not os.path.exists(path):
        st.error(f"الملف غير موجود: {path}")
        return None
    try:
        df = pd.read_excel(path)
        st.sidebar.success(f"تم تحميل قسطاس - {kind}")
        return df
    except Exception as e:
        st.error(f"خطأ في التحميل: {e}")
        return None

# ==================== التصميم ====================
def apply_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
        * {font-family: 'Cairo', sans-serif; direction: rtl;}
        .main {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem;}
        .stApp {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);}
        .main h1, .main h2, .main h3 {color: white !important;}
        [data-testid="stSidebar"] {background: rgba(255, 255, 255, 0.1) !important;}
        [data-testid="stSidebar"] * {color: white !important;}
        .title-container {background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); text-align: center; margin-bottom: 2rem;}
        .comparison-card {background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); margin: 1rem 0;}
        .stButton>button {width: 100%; background: white !important; color: #667eea !important; border: 3px solid #667eea !important; padding: 1rem; border-radius: 10px; font-weight: 700; font-size: 1.2em;}
        .stButton>button:hover {background: #667eea !important; color: white !important;}
        .wizard-container {background: white; padding: 2rem; border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 5px 20px rgba(0,0,0,0.15);}
        .cmp-wrapper {max-height: 500px; overflow: auto; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.12); border: 1px solid #e2e8f0; background: white; margin: 1.5rem 0;}
        .cmp-table {width: 100%; border-collapse: separate; border-spacing: 0; direction: rtl; background: white;}
        .cmp-table thead tr {background: #1e40af !important;}
        .cmp-table thead th {color: white !important; padding: 16px; text-align: center; font-weight: 700;}
        .cmp-table tbody td {padding: 14px; text-align: center; border-bottom: 1px solid #e2e8f0;}
        .cmp-table tbody td:first-child {text-align: right !important; font-weight: 700; background: #f8fafc !important;}
        .cmp-table tbody tr:nth-child(odd) td {background: #f8fafc !important;}
        .cmp-table tbody tr:hover td {background: #dbeafe !important;}
        </style>
    """, unsafe_allow_html=True)

def render_wizard_steps(current_index: int, total_records: int):
    steps_to_show = min(5, total_records)
    cols = st.columns(steps_to_show)
    for i in range(steps_to_show):
        if total_records <= 5:
            actual_index = i
        else:
            if current_index < 2:
                actual_index = i
            elif current_index >= total_records - 3:
                actual_index = total_records - 5 + i
            else:
                actual_index = current_index - 2 + i
        with cols[i]:
            if actual_index < current_index:
                color, icon, label = '#48bb78', '✓', 'مكتمل'
            elif actual_index == current_index:
                color, icon, label = '#f97316', '▶', 'الحالي'
            else:
                color, icon, label = '#e2e8f0', str(actual_index + 1), 'قادم'
            st.markdown(f"""
                <div style="text-align: center;">
                    <div style="width: 60px; height: 60px; border-radius: 50%; background: {color}; color: white; display: flex; align-items: center; justify-content: center; margin: 0 auto 0.5rem; font-weight: bold; font-size: 1.3em; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
                        {icon}
                    </div>
                    <div style="color: {color}; font-weight: 600;">{label}</div>
                </div>
            """, unsafe_allow_html=True)

FIELD_LABELS = {
    "leg_name": "اسم التشريع", "leg_number": "رقم التشريع", "year": "السنة",
    "magazine_number": "رقم الجريدة", "magazine_page": "صفحة الجريدة", "magazine_date": "تاريخ الجريدة",
    "start_date": "تاريخ السريان", "replaced_for": "يحل محل", "status": "الحالة",
    "cancelled_by": "ألغي بواسطة", "end_date": "تاريخ الانتهاء",
}

# ==================== رسائل تحفيزية أردنية أصيلة ====================
SAVE_MESSAGES = [
    "عييييش! كفو عليك يا أسد 🦁",
    "الله يعطيك العافية يا غالي! شغل نظيف 👏",
    "يا زلمة إبداع! استمر هيك 💪",
    "هيييه! تمام يا بطل الأردن 🇯🇴",
    "والله فخورين فيك! يلا عالتالي 🚀",
    "كفو والله! دير بالك أنت صاروخ ⚡",
    "يا سلام عليك! كل حفظ وأنت طيب 🌟",
    "مبروك الحفظ! أنت الأفضل 😎",
    "عفيه عليك يا نشمي! خلصتها زي المنسف بالجميد 🔥",
    "هيييه يا معلم! لو التشريعات بتفهم كانت صفقلك 👏👏",
    "الله يعطيك العافية يا أسد الديوان! استمر ولا توقف 🦁",
    "كفو يا كبير! أنت أسرع من النت في الكافيهات الأردنية ⚡",
    "يا سلام! حفظتها وكأنك بتاكل كنافة نابلسية ساخنة 😋",
    "والله إنك فنان يا زلمة! يلا عالتشريع الجاي، أنت قادر 💪",
    "هسا خلصت؟ عيييش! أنت أقوى من القهوة السادة الصبح 🇯🇴☕",
    "مبروك يا بطل! شغلك نظيف زي المناظر في البترا 🌟",
    "دير بالك أنت صاروخ! لو كان في ميدالية مراجعة كنت أخذت الذهب 🥇",
    "يا عيني عليك! كل حفظ وأنت بتجنن زي الزار في جرش 🎶",
    "كفووو والله! خلصتها وكأنك طاير فوق وادي رم 🚀",
]

FINAL_MESSAGES = [
    "🎉 يا سلام عليك! خلّصت {option} كلها، والله إنك قوي!",
    "👏 الله يعطيك العافية يا غالي! مراجعة نظيفة 100%!",
    "💪 دير بالك، أنت أسد اليوم! خلّصت كل {option} زي الحلاوة!",
    "🌟 يا زلمة، شغلك فنان! مبروك الانتهاء من {option}!",
    "🚀 والله إنك صاروخ! خلّصت {option} وصرت جاهز للي جاي!",
    "🥳 هييييه! مبروك يا كبير، مراجعة {option} خلصت على أحسن ما يرام!",
    "⚡ بسرعة البرق ودقة الصقر! الله يبارك فيك، خلّصت كل شي!",
    "🎯 هدف في المرمى! يا عيني عليك، {option} كلها مراجعة ومضبوطة!",
    "😎 يا معلم، شغلك نظيف زي الذهب! خلّصت {option} وأنت الأول!",
    "❤️ والله فخورين فيك يا بطل الأردن! استمر هيك!",
]

def celebrate_save():
    """احتفال آمن بعد كل حفظ (بدون confetti عشان التوافق)"""
    st.balloons()
    st.snow()  # ثلج خفيف وحلو كبديل
    msg = random.choice(SAVE_MESSAGES)
    st.markdown(f"""
        <div style="text-align: center; padding: 1.5rem; background: linear-gradient(90deg, #48bb78, #1e40af); 
             color: white; border-radius: 15px; margin: 2rem 0; font-size: 1.8em; font-weight: bold;
             box-shadow: 0 8px 25px rgba(0,0,0,0.2);">
            🎉 {msg} 🎉
        </div>
    """, unsafe_allow_html=True)
    time.sleep(1)
    st.balloons()  # بالونات تانية عشان الفرحة تطول

def celebrate_completion():
    """احتفال كبير عند انتهاء النوع كاملاً - آمن"""
    msg = random.choice(FINAL_MESSAGES).format(option=option)
    st.balloons()
    st.snow()
    time.sleep(1)
    st.balloons()
    time.sleep(1)
    st.balloons()  # ثلاث مرات عشان الاحتفال يكون أسطوري
    
    st.markdown(f"""
        <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #667eea, #764ba2); 
             border-radius: 25px; margin: 3rem 0; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
            <h1 style="color: white; font-size: 3em; margin-bottom: 1rem;">{msg}</h1>
            <p style="color: white; font-size: 1.8em;">يلا، نكمل اللي جاي... أنت قادر على كل شي! 🇯🇴💪</p>
        </div>
    """, unsafe_allow_html=True)

# باقي الكود زي ما هو (من render_law_comparison للآخر) بدون تغيير
# ... (نفس الكود اللي بعثته قبل كده بالضبط، بس مع الدالتين الجديدتين أعلاه)

def render_law_comparison(qistas_df: pd.DataFrame, current_index: int, total_records: int):
    qistas_data = {k: ('' if pd.isna(v) else v) for k, v in qistas_df.iloc[current_index].to_dict().items()}
    st.markdown("<h3 style='color: #667eea !important; text-align: center;'>بيانات قسطاس</h3>", unsafe_allow_html=True)
    DISPLAY_FIELDS = [
        ("اسم التشريع", "leg_name"), ("رقم التشريع", "leg_number"), ("السنة", "year"),
        ("رقم الجريدة", "magazine_number"), ("صفحة الجريدة", "magazine_page"), ("تاريخ الجريدة", "magazine_date"),
        ("تاريخ السريان", "start_date"), ("يحل محل", "replaced_for"), ("الحالة", "status"),
        ("ألغي بواسطة", "cancelled_by"), ("تاريخ الانتهاء", "end_date"),
    ]
    rows = []
    for label, key in DISPLAY_FIELDS:
        val = qistas_data.get(key, '')
        display_val = '—' if str(val).strip() == '' else str(val)
        rows.append((label, display_val))
    html = ["<div class='cmp-wrapper'><table class='cmp-table'>"]
    html.append("<thead><tr><th>اسم الحقل</th><th>القيمة</th></tr></thead><tbody>")
    for label, val in rows:
        html.append(f"<tr><td>{label}</td><td>{val}</td></tr>")
    html.append("</tbody></table></div>")
    st.markdown("\n".join(html), unsafe_allow_html=True)
    render_selection_buttons(qistas_data, current_index, total_records)

def render_selection_buttons(qistas_data: dict, current_index: int, total_records: int):
    st.markdown("---")
    st.markdown("<h3 style='color: white; text-align: center;'>احفظ البيانات الصحيحة</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ حفظ كما هو (قسطاس)", use_container_width=True, key=f"save_as_is_{current_index}"):
            save_comparison_record(qistas_data, 'قسطاس')
            celebrate_save()  # احتفال بعد كل حفظ
            move_to_next_record(total_records, current_index)
    with col2:
        if st.button("✍️ تصحيح يدوي", use_container_width=True, key=f"manual_{current_index}"):
            st.session_state.show_custom_form = True
            st.rerun()

    if st.session_state.get("show_custom_form", False):
        render_custom_form(qistas_data, current_index, total_records)

def render_custom_form(reference_data: dict, current_index: int, total_records: int):
    st.markdown("---")
    st.markdown("<h3 style='color: white; text-align: center;'>تصحيح يدوي</h3>", unsafe_allow_html=True)
    with st.form("custom_form", clear_on_submit=False):
        custom_data = {}
        cols_list = st.columns(3)
        ordered_keys = ["leg_name", "leg_number", "year", "magazine_number", "magazine_page",
                        "magazine_date", "start_date", "replaced_for", "status", "cancelled_by", "end_date"]
        fields = [k for k in ordered_keys if k in reference_data] + [k for k in reference_data if k not in ordered_keys]
        for i, key in enumerate(fields):
            with cols_list[i % 3]:
                label = FIELD_LABELS.get(key, key)
                val = reference_data.get(key, "")
                value_str = str(val) if val else ""
                custom_data[key] = st.text_input(label, value=value_str)
        c1, c2 = st.columns(2)
        with c1:
            if st.form_submit_button("حفظ والتالي", use_container_width=True):
                cleaned = {k: v.strip() if v else "" for k, v in custom_data.items()}
                for k in reference_data:
                    if k not in cleaned:
                        cleaned[k] = reference_data[k] if reference_data[k] else ""
                save_comparison_record(cleaned, 'تصحيح يدوي')
                celebrate_save()  # احتفال بعد كل حفظ
                st.session_state.show_custom_form = False
                move_to_next_record(total_records, current_index)
        with c2:
            if st.form_submit_button("إلغاء", use_container_width=True):
                st.session_state.show_custom_form = False
                st.rerun()

def save_comparison_record(data: dict, source: str) -> None:
    comp_key = SessionManager.get_unique_key("comparison_data")
    new_record = {
        'تاريخ الإدخال': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'المصدر': source,
        'المعدل بواسطة': user_name,
        **data
    }
    st.session_state[comp_key].append(new_record)
    save_persistent_data()

def move_to_next_record(total_records: int, current_index: int) -> None:
    idx_key = SessionManager.get_unique_key("current_index")
    max_key = SessionManager.get_unique_key("max_reached_idx")
    if current_index + 1 < total_records:
        st.session_state[idx_key] += 1
        st.session_state[max_key] = max(st.session_state.get(max_key, 0), current_index + 1)
        st.session_state.show_custom_form = False
        save_progress(st.session_state[idx_key], st.session_state[max_key])
        save_persistent_data()
        st.rerun()
    else:
        celebrate_completion()
        st.success(f"🎉 تم الانتهاء من مراجعة جميع سجلات {option} بنجاح!")
        st.info("تقدر دلوقتي تغيّر النوع من القائمة الجانبية أو تبدأ من جديد.")

def render_navigation_buttons(current_index: int, total_records: int):
    st.markdown("---")
    col1, _, col3 = st.columns([1, 2, 1])
    idx_key = SessionManager.get_unique_key("current_index")
    max_key = SessionManager.get_unique_key("max_reached_idx")
    with col1:
        if current_index > 0 and st.button("⏮️ السابق", use_container_width=True):
            st.session_state[idx_key] -= 1
            st.session_state.show_custom_form = False
            save_progress(st.session_state[idx_key], st.session_state[max_key])
            st.rerun()
    with col3:
        if current_index < total_records - 1 and current_index < st.session_state.get(max_key, 0):
            if st.button("⏭️ التالي", use_container_width=True, type="primary"):
                st.session_state[idx_key] += 1
                save_progress(st.session_state[idx_key], st.session_state[max_key])
                st.rerun()

def render_comparison_tab(qistas_df: pd.DataFrame):
    st.markdown("<div class='comparison-card'>", unsafe_allow_html=True)
    total_records = len(qistas_df)
    current_index = st.session_state[SessionManager.get_unique_key("current_index")]
    progress = int(((current_index + 1) / total_records) * 100) if total_records else 0
    st.markdown(f"""
        <div class='wizard-container'>
            <h3 style='color: #667eea; text-align: center;'>مراجعة التشريعات - {option}</h3>
            <p style='text-align: center; font-size: 1.1em; color: #718096;'>
                السجل {current_index + 1} من {total_records} ({progress}%)
            </p>
        </div>
    """, unsafe_allow_html=True)
    render_wizard_steps(current_index, total_records)
    st.markdown(f"<div style='background: #e2e8f0; height: 15px; border-radius: 10px; overflow: hidden; margin: 2rem 0;'><div style='height: 100%; background: linear-gradient(90deg, #667eea, #48bb78); width: {progress}%;'></div></div>", unsafe_allow_html=True)
    if current_index < total_records:
        render_law_comparison(qistas_df, current_index, total_records)
        render_navigation_buttons(current_index, total_records)
    else:
        st.markdown("<div style='text-align: center; padding: 3rem;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #667eea;'>تم الانتهاء من هذا النوع بنجاح! 🎯</h2>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 1.2em;'>اختر نوع تشريع آخر من الشريط الجانبي للمتابعة.</p>", unsafe_allow_html=True)
        if st.button("🔄 بدء جديد لهذا النوع"):
            st.session_state[SessionManager.get_unique_key("current_index")] = 0
            save_progress(0, 0)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_saved_data_tab():
    st.markdown("<div class='comparison-card'>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='color: #667eea; text-align: center;'>البيانات المحفوظة - {option}</h2>", unsafe_allow_html=True)
    data = st.session_state.get(SessionManager.get_unique_key("comparison_data"), [])
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        st.download_button(
            f"تحميل البيانات ({len(data)} سجل)",
            buffer.getvalue(),
            f"{user_name}_{option}_مراجعة_{datetime.now().strftime('%Y%m%d')}.xlsx",
            use_container_width=True
        )
    else:
        st.info("لا توجد بيانات محفوظة بعد.")
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== البرنامج الرئيسي ====================
def main():
    apply_styles()
    st.markdown("""
        <div class="title-container">
            <h1 style='color: #667eea;'>⚖️ نظام مراجعة التشريعات</h1>
            <p style='color: #718096; font-size: 18px;'>مراجعة وتصحيح بيانات قسطاس - حفظ دائم لكل مستخدم</p>
        </div>
    """, unsafe_allow_html=True)
    initialize_session_state()
    qistas_df = load_qis_data(option)
    if qistas_df is None:
        st.error("فشل تحميل البيانات.")
        return
    if 'GroupKey' in qistas_df.columns:
        qistas_df = qistas_df.sort_values(by='GroupKey').reset_index(drop=True)
    tab1, tab2 = st.tabs(["مراجعة", "البيانات المحفوظة"])
    with tab1:
        render_comparison_tab(qistas_df)
    with tab2:
        render_saved_data_tab()
    st.markdown("<div style='text-align: center; color: white; padding: 1rem;'>نظام مراجعة التشريعات © 2026</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()

