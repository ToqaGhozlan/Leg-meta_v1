"""
نظام مراجعة التشريعات القانونية
مراجعة وتصحيح بيانات قانونية
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
import json

# ==================== إعدادات الصفحة ====================
st.set_page_config(
    page_title="نظام مراجعة التشريعات القانونية",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("نوع التشريع")
option = st.sidebar.radio(
    "اختر نوع البيانات:",
    ["نظام", "قانون"],
)

# ==================== ملفات منفصلة لكل نوع تشريع ====================
DATA_FILES = {
    'نظام': 'Bylaw_Comparison.json',
    'قانون': 'Law_Comparison.json',
}
PROGRESS_FILES = {
    'نظام': 'Bylaw_Progress.json',
    'قانون': 'Law_Progress.json',
}
COMPARISON_OUTPUTS = {
    'نظام': 'Bylaws_Comparison_Saved.xlsx',
    'قانون': 'Laws_Comparison_Saved.xlsx',
}
COMPARISON_FILE = COMPARISON_OUTPUTS[option]
DATA_FILE = DATA_FILES[option]
PROGRESS_FILE = PROGRESS_FILES[option]

@st.cache_data
def load_qis_data(kind: str):
    PATHS = {
        'نظام': r'Qistas\V02_All_Legs\V10_Bylaws.xlsx',
        'قانون': r'Qistas\V02_All_Legs\V05_Laws.xlsx',
    }
    if kind not in PATHS:
        st.error(f"النوع '{kind}' غير مدعوم حاليًا.")
        return None
    qis_path = PATHS[kind]
    if not os.path.exists(qis_path):
        st.error(f"الملف غير موجود ← {qis_path}")
        return None
    try:
        df = pd.read_excel(qis_path)
        st.sidebar.success(f"تم تحميل قسطاس ({os.path.basename(qis_path)})")
        return df
    except Exception as e:
        st.error(f"فشل تحميل ملف قسطاس:\n{qis_path}\n\n{str(e)}")
        return None

# ==================== قاموس الترجمة للحقول ====================
FIELD_LABELS = {
    "leg_name": "اسم التشريع",
    "leg_number": "رقم التشريع",
    "year": "السنة",
    "magazine_number": "رقم الجريدة",
    "magazine_page": "صفحة الجريدة",
    "magazine_date": "تاريخ الجريدة",
    "start_date": "تاريخ السريان",
    "replaced_for": "يحل محل",
    "status": "الحالة",
    "cancelled_by": "ألغي بواسطة",
    "end_date": "تاريخ الانتهاء",
}

# ==================== دوال عامة ====================
def save_to_file(filename: str, data) -> None:
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"خطأ في حفظ البيانات: {str(e)}")

def load_from_file(filename: str):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {str(e)}")
    return None

class SessionManager:
    @staticmethod
    def get_current_files():
        return DATA_FILE, PROGRESS_FILE
   
    @staticmethod
    def get_unique_key(base_key: str) -> str:
        return f"{base_key}_{option.replace(' ', '_')}"

    @staticmethod
    def initialize():
        data_file, progress_file = SessionManager.get_current_files()
        comp_key = SessionManager.get_unique_key('comparison_data')
        idx_key = SessionManager.get_unique_key('current_index')
        form_key = SessionManager.get_unique_key('show_custom_form')
        next_key = SessionManager.get_unique_key('show_next_in_review')
        max_key = SessionManager.get_unique_key('max_reached_idx')
       
        if comp_key not in st.session_state:
            saved = load_from_file(data_file)
            st.session_state[comp_key] = saved if saved is not None else []

        if idx_key not in st.session_state:
            saved_progress = load_from_file(progress_file)
            if saved_progress and isinstance(saved_progress, dict):
                st.session_state[idx_key] = saved_progress.get('current_index', 0)
                st.session_state[max_key] = saved_progress.get('max_reached_idx', 0)
            elif saved_progress is not None:
                st.session_state[idx_key] = saved_progress
                st.session_state[max_key] = saved_progress
            else:
                st.session_state[idx_key] = 0
                st.session_state[max_key] = 0

        if form_key not in st.session_state: st.session_state[form_key] = False
        if next_key not in st.session_state: st.session_state[next_key] = False
        if max_key not in st.session_state: st.session_state[max_key] = 0

    @staticmethod
    def save_persistent():
        data_file, progress_file = SessionManager.get_current_files()
        try:
            comp_key = SessionManager.get_unique_key('comparison_data')
            idx_key = SessionManager.get_unique_key('current_index')
            max_key = SessionManager.get_unique_key('max_reached_idx')
            progress_data = {
                'current_index': st.session_state[idx_key],
                'max_reached_idx': st.session_state.get(max_key, 0)
            }
            save_to_file(data_file, st.session_state[comp_key])
            save_to_file(progress_file, progress_data)
        except Exception as e:
            st.error(f"فشل الحفظ التلقائي: {e}")

def initialize_session_state():
    SessionManager.initialize()

def save_persistent_data():
    SessionManager.save_persistent()

def get_legislation_data(index: int, source_df: pd.DataFrame) -> dict:
    if index >= len(source_df):
        return {}
    row = source_df.iloc[index]
    return {k: ('' if pd.isna(v) else v) for k, v in row.to_dict().items()}

def save_comparison_record(data: dict, source: str) -> None:
    comp_key = SessionManager.get_unique_key('comparison_data')
    new_record = {
        'تاريخ الإدخال': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'المصدر': source,
        **data
    }
    st.session_state[comp_key].append(new_record)
    save_persistent_data()

def move_to_next_record(total_records: int, current_index: int) -> None:
    idx_key = SessionManager.get_unique_key('current_index')
    max_key = SessionManager.get_unique_key('max_reached_idx')
   
    if current_index + 1 < total_records:
        st.session_state[idx_key] += 1
        st.session_state[max_key] = max(st.session_state.get(max_key, 0), current_index + 1)
        save_persistent_data()
        st.rerun()
    else:
        st.balloons()
        st.success("🎉 تم الانتهاء من مراجعة جميع السجلات!")

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

# ==================== عرض بيانات قسطاس ====================
def render_law_comparison(qistas_df: pd.DataFrame, current_index: int, total_records: int):
    qistas_data = get_legislation_data(current_index, qistas_df)
    st.markdown("<h3 style='color: #667eea !important; text-align: center;'>بيانات قسطاس</h3>", unsafe_allow_html=True)

    DISPLAY_FIELDS = [
        ("اسم التشريع", "leg_name"),
        ("رقم التشريع", "leg_number"),
        ("السنة", "year"),
        ("رقم الجريدة", "magazine_number"),
        ("صفحة الجريدة", "magazine_page"),
        ("تاريخ الجريدة", "magazine_date"),
        ("تاريخ السريان", "start_date"),
        ("يحل محل", "replaced_for"),
        ("الحالة", "status"),
        ("ألغي بواسطة", "cancelled_by"),
        ("تاريخ الانتهاء", "end_date"),
    ]

    rows = []
    for label, key in DISPLAY_FIELDS:
        val = qistas_data.get(key, '')
        display_val = '—' if pd.isna(val) or str(val).strip() == '' else str(val)
        rows.append((label, display_val))

    if rows:
        html = ["<div class='cmp-wrapper'><table class='cmp-table'>"]
        html.append("<thead><tr><th>اسم الحقل</th><th>القيمة</th></tr></thead><tbody>")
        for label, val in rows:
            html.append(f"<tr><td>{label}</td><td>{val}</td></tr>")
        html.append("</tbody></table></div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)
    else:
        st.info("لا توجد بيانات في هذا السجل.")

    render_selection_buttons(qistas_data, current_index, total_records)

def render_selection_buttons(qistas_data: dict, current_index: int, total_records: int):
    st.markdown("---")
    st.markdown("<h3 style='color: white; text-align: center;'>احفظ البيانات الصحيحة</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ حفظ كما هو (قسطاس)", use_container_width=True, key=f"save_as_is_{current_index}"):
            save_comparison_record(qistas_data, 'قسطاس')
            st.success("تم الحفظ!")
            move_to_next_record(total_records, current_index)
    
    with col2:
        form_key = SessionManager.get_unique_key('show_custom_form')
        if st.button("✍️ تصحيح يدوي", use_container_width=True, key=f"manual_{current_index}"):
            st.session_state[form_key] = True
            st.rerun()

    if st.session_state.get(SessionManager.get_unique_key('show_custom_form'), False):
        render_custom_form(qistas_data, current_index, total_records)

# ==================== نموذج التصحيح اليدوي (خانات عادية بسيطة) ====================
def render_custom_form(reference_data: dict, current_index: int, total_records: int):
    st.markdown("---")
    st.markdown("<h3 style='color: white; text-align: center;'>تصحيح يدوي</h3>", unsafe_allow_html=True)
    
    with st.form("custom_form", clear_on_submit=False):
        custom_data = {}
        
        ordered_keys = [
            "leg_name", "leg_number", "year", "magazine_number", "magazine_page",
            "magazine_date", "start_date", "replaced_for", "status",
            "cancelled_by", "end_date"
        ]
        
        fields = [k for k in ordered_keys if k in reference_data]
        fields += [k for k in reference_data if k not in ordered_keys]  # أي حقول إضافية

        for key in fields:
            label = FIELD_LABELS.get(key, key)
            value = reference_data.get(key, "")
            value_str = str(value) if value else ""
            
            edited = st.text_input(label, value=value_str, key=f"edit_{key}_{current_index}")
            custom_data[key] = edited.strip() if edited.strip() else value_str

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("✅ حفظ والتالي", use_container_width=True, type="primary"):
                # نضمن حفظ كل الحقول حتى لو ما تغيرت
                final_data = {}
                for k in reference_data:
                    final_data[k] = custom_data.get(k, reference_data.get(k, ""))
                
                save_comparison_record(final_data, 'تصحيح يدوي')
                st.session_state[SessionManager.get_unique_key('show_custom_form')] = False
                st.success("تم الحفظ بنجاح!")
                move_to_next_record(total_records, current_index)

        with col2:
            if st.form_submit_button("❌ إلغاء", use_container_width=True):
                st.session_state[SessionManager.get_unique_key('show_custom_form')] = False
                st.rerun()

def render_navigation_buttons(current_index: int, total_records: int):
    st.markdown("---")
    col1, _, col3 = st.columns([1, 2, 1])
    idx_key = SessionManager.get_unique_key('current_index')
    form_key = SessionManager.get_unique_key('show_custom_form')
    max_key = SessionManager.get_unique_key('max_reached_idx')

    with col1:
        if current_index > 0 and st.button("⏮️ السابق", use_container_width=True):
            st.session_state[idx_key] -= 1
            st.session_state[form_key] = False
            save_persistent_data()
            st.rerun()

    with col3:
        if current_index < total_records - 1 and current_index < st.session_state.get(max_key, 0):
            if st.button("⏭️ التالي", use_container_width=True, type="primary"):
                st.session_state[idx_key] += 1
                save_persistent_data()
                st.rerun()

def render_comparison_tab(qistas_df: pd.DataFrame):
    st.markdown("<div class='comparison-card'>", unsafe_allow_html=True)
    total_records = len(qistas_df)
    current_index = st.session_state[SessionManager.get_unique_key('current_index')]
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
        st.success("🎉 تم الانتهاء من المراجعة!")
        if st.button("🔄 بدء جديد"):
            st.session_state[SessionManager.get_unique_key('current_index')] = 0
            st.session_state[SessionManager.get_unique_key('show_custom_form')] = False
            save_persistent_data()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

def render_saved_data_tab():
    st.markdown("<div class='comparison-card'>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='color: #667eea; text-align: center;'>البيانات المحفوظة - {option}</h2>", unsafe_allow_html=True)

    comp_key = SessionManager.get_unique_key('comparison_data')
    data = st.session_state.get(comp_key, [])
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        st.download_button(f"تحميل البيانات ({len(data)} سجل)", buffer.getvalue(), COMPARISON_FILE, use_container_width=True)
        
        if st.button("مسح الكل", type="secondary"):
            for f in [DATA_FILE, PROGRESS_FILE]:
                if os.path.exists(f): os.remove(f)
            st.session_state[comp_key] = []
            st.session_state[SessionManager.get_unique_key('current_index')] = 0
            st.success("تم المسح!")
            st.rerun()
    else:
        st.info("لا توجد بيانات محفوظة بعد.")

    st.markdown("</div>", unsafe_allow_html=True)

# ==================== البرنامج الرئيسي ====================
def main():
    apply_styles()
    
    st.markdown("""
        <div class="title-container">
            <h1 style='color: #667eea;'>⚖️ نظام مراجعة التشريعات</h1>
            <p style='color: #718096; font-size: 18px;'>مراجعة وتصحيح بيانات قسطاس</p>
        </div>
    """, unsafe_allow_html=True)
    
    initialize_session_state()
    
    qistas_df = load_qis_data(option)
    
    if qistas_df is None:
        st.error("فشل تحميل بيانات قسطاس. تأكد من المسار.")
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
