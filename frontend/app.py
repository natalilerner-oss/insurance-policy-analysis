import streamlit as st
import requests
import json
import os
import sys
import base64
import time
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Ensure sibling modules are importable regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))
from sanitizer import (
    mask_id_number, mask_name, mask_address, mask_phone, mask_email,
    sanitize_policy, sanitize_policies,
)

load_dotenv()

# Polling configuration constants
POLL_MAX_WAIT_SECONDS = 600  # 10 minutes maximum wait time
POLL_INITIAL_INTERVAL_SECONDS = 5  # Initial polling interval
POLL_MAX_INTERVAL_SECONDS = 15  # Maximum polling interval
POLL_BACKOFF_INCREMENT_SECONDS = 2  # Interval increase per poll

# Configuration
st.set_page_config(
    page_title="PolicyLens - מחלץ פוליסות ביטוח",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS: DocumentInsight.ai-inspired design with full RTL Hebrew support
st.markdown("""
<style>
    /* ===== Global RTL Direction ===== */
    .main .block-container, .stMarkdown, .stTextInput, .stNumberInput,
    .stSelectbox, .stMultiselect, .stCheckbox, .stRadio, .stDateInput,
    .stFileUploader, .stExpander, .stDataFrame {
        direction: rtl;
        text-align: right;
    }
    /* Force RTL on all Streamlit elements */
    [data-testid="stAppViewContainer"] {
        direction: rtl;
    }
    [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stTextInput {
        direction: rtl;
        text-align: right;
    }
    /* Input fields RTL */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        direction: rtl;
        text-align: right;
    }
    /* Labels RTL */
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    .stFileUploader label, .stCheckbox label, .stDateInput label,
    .stTextArea label {
        direction: rtl;
        text-align: right;
        width: 100%;
    }

    /* ===== Color Palette & Typography ===== */
    :root {
        --di-primary: #0056b3;
        --di-primary-dark: #003d82;
        --di-teal: #17a2b8;
        --di-gradient: linear-gradient(90deg, #17a2b8, #0056b3);
        --di-bg: #f8fafc;
        --di-card-bg: #ffffff;
        --di-text: #374151;
        --di-text-light: #6b7280;
        --di-border: #e5eaf0;
        --di-icon-bg: #eef6ff;
        --di-icon-color: #0b63c5;
        --di-success: #10B981;
        --di-shadow: 0 6px 24px rgba(0,0,0,0.08);
        --di-shadow-hover: 0 10px 32px rgba(0,0,0,0.12);
    }

    /* ===== Hero Section ===== */
    .hero-section {
        background: linear-gradient(135deg, rgba(0,86,179,0.85), rgba(23,162,184,0.85)),
                    url('https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=1200') center/cover;
        border-radius: 16px;
        padding: 48px 40px;
        margin: 0 0 2rem 0;
        text-align: right;
        direction: rtl;
        position: relative;
        min-height: 200px;
        box-sizing: border-box;
        width: 100%;
    }
    .hero-section h1 {
        color: #ffffff;
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 8px;
        letter-spacing: 0.01em;
    }
    .hero-section .hero-subtitle {
        color: rgba(255,255,255,0.9);
        font-size: 1.15rem;
        margin-bottom: 20px;
        line-height: 1.6;
    }
    .hero-features {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-top: 16px;
    }
    .hero-feature-item {
        color: rgba(255,255,255,0.95);
        font-size: 1rem;
        display: flex;
        align-items: center;
        gap: 10px;
        direction: rtl;
    }
    .hero-feature-item .icon {
        color: #7dd3fc;
        font-size: 1.1rem;
    }

    /* ===== Pill Badge ===== */
    .pill-badge {
        display: inline-block;
        background: linear-gradient(90deg, #17a2b8, #0056b3);
        color: #ffffff;
        padding: 6px 20px;
        border-radius: 999px;
        font-size: 0.9rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        margin-bottom: 12px;
    }

    /* ===== Feature Cards ===== */
    .feature-card {
        background: var(--di-card-bg);
        border: 1px solid var(--di-border);
        border-radius: 14px;
        padding: 24px;
        box-shadow: var(--di-shadow);
        transition: transform 0.2s, box-shadow 0.2s;
        direction: rtl;
        text-align: right;
        height: 100%;
    }
    .feature-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--di-shadow-hover);
    }
    .feature-card .card-icon {
        width: 52px;
        height: 52px;
        background: var(--di-icon-bg);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 16px;
        font-size: 1.5rem;
        color: var(--di-icon-color);
    }
    .feature-card h3 {
        color: var(--di-primary);
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .feature-card p {
        color: var(--di-text-light);
        font-size: 0.95rem;
        line-height: 1.6;
    }

    /* ===== Section Headers ===== */
    .section-header {
        direction: rtl;
        text-align: right;
        margin-bottom: 24px;
    }
    .section-header h2 {
        color: var(--di-primary);
        font-size: 1.6rem;
        font-weight: 700;
        letter-spacing: 0.01em;
    }
    .section-header p {
        color: var(--di-text-light);
        font-size: 1rem;
        margin-top: 4px;
    }

    /* ===== Policy Card (Data Display) ===== */
    .policy-card {
        background-color: var(--di-card-bg);
        border-radius: 14px;
        padding: 20px;
        margin: 12px 0;
        border-right: 4px solid var(--di-primary);
        border-left: none;
        box-shadow: var(--di-shadow);
        direction: rtl;
        text-align: right;
    }

    /* ===== Premium Highlight ===== */
    .premium-highlight {
        font-size: 1.5em;
        color: var(--di-success);
        font-weight: bold;
    }

    /* ===== Coverage Item ===== */
    .coverage-item {
        background-color: var(--di-icon-bg);
        padding: 10px 14px;
        border-radius: 8px;
        margin: 6px 0;
        direction: rtl;
        text-align: right;
    }

    /* ===== Tabs Styling ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        direction: rtl;
        justify-content: flex-start;
        border-bottom: 2px solid var(--di-border);
        padding-bottom: 0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        padding: 10px 20px;
        border-radius: 10px 10px 0 0;
        font-weight: 600;
        color: var(--di-text-light);
        background: transparent;
        border: none;
        direction: rtl;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: var(--di-primary);
        background: var(--di-card-bg);
        border-bottom: 3px solid var(--di-primary);
    }

    /* ===== Metric Cards ===== */
    [data-testid="stMetric"] {
        background: var(--di-card-bg);
        border: 1px solid var(--di-border);
        border-radius: 14px;
        padding: 16px 20px;
        box-shadow: var(--di-shadow);
        direction: rtl;
        text-align: right;
    }
    [data-testid="stMetricLabel"] {
        direction: rtl;
        text-align: right;
    }
    [data-testid="stMetricValue"] {
        color: var(--di-primary);
        font-weight: 700;
    }

    /* ===== Buttons ===== */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(90deg, #17a2b8, #0056b3) !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 12px 24px !important;
        font-size: 1rem !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="baseButton-primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0,86,179,0.3) !important;
    }
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        border: 1px solid var(--di-border) !important;
    }

    /* ===== Expander RTL ===== */
    .streamlit-expanderHeader {
        direction: rtl;
        text-align: right;
    }
    [data-testid="stExpander"] {
        border: 1px solid var(--di-border);
        border-radius: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    /* ===== File Uploader ===== */
    [data-testid="stFileUploader"] {
        direction: rtl;
        text-align: right;
    }
    [data-testid="stFileUploader"] section {
        border: 2px dashed var(--di-border);
        border-radius: 14px;
        background: var(--di-card-bg);
    }

    /* ===== Data frames RTL ===== */
    .stDataFrame {
        direction: rtl;
    }

    /* ===== Footer ===== */
    .di-footer {
        text-align: center;
        color: var(--di-text-light);
        padding: 24px 0 8px 0;
        font-size: 0.85rem;
        direction: rtl;
    }
    .di-footer a {
        color: var(--di-primary);
        text-decoration: none;
        font-weight: 600;
    }
    .di-footer a:hover {
        text-decoration: underline;
    }
    .di-footer .footer-brand {
        font-size: 0.95rem;
        margin-bottom: 4px;
    }

    /* ===== Sidebar Styling ===== */
    [data-testid="stSidebar"] {
        background: var(--di-card-bg);
        border-left: 1px solid var(--di-border);
        border-right: none;
    }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--di-primary);
    }

    /* ===== LTR for English / URL inputs in sidebar ===== */
    [data-testid="stSidebar"] .stTextInput input[value*="."],
    [data-testid="stSidebar"] .stTextInput input[value*="http"],
    [data-testid="stSidebar"] .stTextInput input[type="text"] {
        direction: ltr;
        text-align: left;
    }

    /* ===== Divider ===== */
    hr {
        border-color: var(--di-border) !important;
    }

    /* ===== Info/Warning/Error boxes RTL ===== */
    .stAlert {
        direction: rtl;
        text-align: right;
    }

    /* ===== Download button ===== */
    .stDownloadButton > button {
        background: linear-gradient(90deg, #17a2b8, #0056b3) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }

    /* ===== Columns RTL fix ===== */
    [data-testid="stHorizontalBlock"] {
        direction: rtl;
    }

    /* ===== Stat row ===== */
    .stat-row {
        display: flex;
        gap: 16px;
        direction: rtl;
        margin-bottom: 24px;
    }
    .stat-card {
        flex: 1;
        background: var(--di-card-bg);
        border: 1px solid var(--di-border);
        border-radius: 14px;
        padding: 20px;
        box-shadow: var(--di-shadow);
        text-align: center;
    }
    .stat-card .stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--di-primary);
    }
    .stat-card .stat-label {
        color: var(--di-text-light);
        font-size: 0.9rem;
        margin-top: 4px;
    }

    /* ===== Responsive Design ===== */

    /* Global box-sizing */
    *, *::before, *::after {
        box-sizing: border-box;
    }

    /* Prevent horizontal overflow globally */
    html, body, [data-testid="stAppViewContainer"],
    .main, .main .block-container {
        max-width: 100%;
        overflow-x: hidden;
    }
    .main .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* Text overflow safety */
    .stMarkdown, .hero-section, .feature-card, .section-header,
    .di-footer, .policy-card, p, h1, h2, h3, h4, h5, h6, span, a, li {
        overflow-wrap: break-word;
        word-wrap: break-word;
    }

    /* Responsive images */
    img {
        max-width: 100%;
        height: auto;
    }

    /* Feature cards row responsive */
    .feature-cards-row {
        display: flex;
        gap: 16px;
        direction: rtl;
        margin-bottom: 24px;
        flex-wrap: wrap;
        width: 100%;
    }
    .feature-cards-row .feature-card {
        flex: 1 1 280px;
        min-width: 0;
    }

    /* Tabs horizontal scroll on small screens */
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto;
        flex-wrap: nowrap;
        -webkit-overflow-scrolling: touch;
    }

    /* ---- Tablet (<=900px) ---- */
    @media (max-width: 900px) {
        .hero-section {
            padding: 32px 24px;
            margin: 0 0 1.5rem 0;
            border-radius: 12px;
        }
        .hero-section h1 {
            font-size: 1.8rem;
        }
        .hero-section .hero-subtitle {
            font-size: 1rem;
        }
        .feature-cards-row .feature-card {
            flex: 1 1 240px;
        }
        .feature-card {
            padding: 18px;
        }
        .feature-card h3 {
            font-size: 1.05rem;
        }
        .section-header h2 {
            font-size: 1.35rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 14px;
            font-size: 0.9rem;
        }
        .stat-row {
            flex-wrap: wrap;
        }
    }

    /* ---- Mobile (<=600px) ---- */
    @media (max-width: 600px) {
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        .hero-section {
            padding: 24px 16px;
            margin: 0 0 1rem 0;
            border-radius: 10px;
            min-height: auto;
        }
        .hero-section h1 {
            font-size: 1.5rem;
        }
        .hero-section .hero-subtitle {
            font-size: 0.9rem;
            margin-bottom: 12px;
        }
        .hero-feature-item {
            font-size: 0.85rem;
        }
        /* Stack feature cards vertically */
        .feature-cards-row {
            flex-direction: column !important;
            gap: 12px;
        }
        .feature-cards-row .feature-card {
            flex: 1 1 100%;
            min-width: 0 !important;
            width: 100%;
        }
        .feature-card {
            padding: 16px;
        }
        .feature-card .card-icon {
            width: 40px;
            height: 40px;
            font-size: 1.2rem;
        }
        .feature-card h3 {
            font-size: 1rem;
        }
        .feature-card p {
            font-size: 0.85rem;
        }
        .pill-badge {
            font-size: 0.8rem;
            padding: 5px 14px;
        }
        .section-header h2 {
            font-size: 1.2rem;
        }
        .section-header p {
            font-size: 0.85rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 6px 10px;
            font-size: 0.8rem;
            height: auto;
            white-space: nowrap;
        }
        [data-testid="stMetric"] {
            padding: 12px 14px;
        }
        .stat-row {
            flex-direction: column;
        }
        .stat-card .stat-value {
            font-size: 1.4rem;
        }
        .di-footer {
            font-size: 0.75rem;
            padding: 16px 0 4px 0;
        }
        /* Columns stacking */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap;
        }
    }

    /* ---- Small mobile (<=375px) ---- */
    @media (max-width: 375px) {
        .hero-section h1 {
            font-size: 1.3rem;
        }
        .hero-section .hero-subtitle {
            font-size: 0.8rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 5px 8px;
            font-size: 0.75rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'extracted_policies' not in st.session_state:
    st.session_state.extracted_policies = []
if 'family_name' not in st.session_state:
    st.session_state.family_name = ""
if 'show_sensitive' not in st.session_state:
    st.session_state.show_sensitive = False

# Sidebar Configuration
with st.sidebar:
    try:
        st.image("https://documentinsight.ai/logo.png", width=200)
    except Exception:
        st.markdown(
            '<div style="direction:ltr;text-align:center;padding:12px 0;">'
            '<span style="font-size:1.4rem;font-weight:700;color:#0056b3;">DocumentInsight.ai</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    st.markdown("---")
    st.markdown('<div style="direction:rtl;text-align:right;"><h3 style="color:#0056b3;">הגדרות</h3></div>', unsafe_allow_html=True)

    default_url = os.getenv("BACKEND_URL", "http://localhost:7071/api")
    backend_url = st.text_input("Backend URL", value=default_url)

    st.divider()
    show_sensitive = st.toggle("הצג מידע רגיש", value=st.session_state.show_sensitive)
    st.session_state.show_sensitive = show_sensitive
    if not show_sensitive:
        st.caption("מידע אישי מוסתר")

    st.divider()
    st.markdown(
        '<div style="direction:ltr;text-align:left;">'
        '<strong>DocumentInsight.ai</strong><br>'
        '<span style="color:#6b7280;font-size:0.85rem;">From a junkyard of information to a gallery of Knowledge</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# Hero Section
st.markdown("""
<div class="hero-section">
    <h1>PolicyLens</h1>
    <div class="hero-subtitle">
        מערכת חכמה לחילוץ וניהול פוליסות ביטוח — מונעת בינה מלאכותית
    </div>
    <div class="hero-features">
        <div class="hero-feature-item">
            <span class="icon">&#9650;</span>
            <span>העלאה אוטומטית של קבצי PDF, תמונות וסריקות</span>
        </div>
        <div class="hero-feature-item">
            <span class="icon">&#9776;</span>
            <span>חילוץ נתונים חכם, פילוח והעשרה למסד ידע מובנה</span>
        </div>
        <div class="hero-feature-item">
            <span class="icon">&#10148;</span>
            <span>ייצוא תיקי ביטוח נקיים ומוכנים לעבודה</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Feature cards row
st.markdown("""
<div class="feature-cards-row">
    <div class="feature-card">
        <div class="card-icon">&#128229;</div>
        <h3>קליטה אחידה</h3>
        <p>העלאת קבצי PDF, תמונות וסריקות. המערכת מנרמלת פורמטים ומבצעת OCR אוטומטי.</p>
    </div>
    <div class="feature-card">
        <div class="card-icon">&#128202;</div>
        <h3>מבנה שנשאר</h3>
        <p>פילוח, סיכום ותיוג תוכן כדי שהמידע יהיה ממוקד, נקי ומוכן לכל אסטרטגיית שליפה.</p>
    </div>
    <div class="feature-card">
        <div class="card-icon">&#128640;</div>
        <h3>ייצוא לכל מקום</h3>
        <p>ייצוא תיקי ביטוח נקיים ל-Excel, עם שמירה מלאה על מקוריות הנתונים.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Workflow pill badge + tabs
st.markdown('<div style="text-align:center; margin-bottom:8px;"><span class="pill-badge">מוכן לעבודה עם AI</span></div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. העלאת פוליסות",
    "2. סקירת נתונים",
    "3. יצירת תיק ביטוח",
    "4. השוואת פוליסות",
    "5. חילוצים אחרונים"
])

# ==================== TAB 1: Upload Policies ====================
with tab1:
    st.markdown('<div class="section-header"><h2>העלאת מסמכי פוליסה</h2><p>העלה קבצי PDF או תמונות של פוליסות ביטוח. המערכת תחליץ את הנתונים באופן אוטומטי.</p></div>', unsafe_allow_html=True)
    
    # Family name input
    family_name = st.text_input(
        "שם המשפחה",
        value=st.session_state.family_name,
        placeholder="לדוגמה: לרנר",
        help="שם המשפחה יופיע בכותרת תיק הביטוח"
    )
    st.session_state.family_name = family_name
    
    st.divider()
    
    # File uploader - multiple files
    uploaded_files = st.file_uploader(
        "בחר קבצי פוליסה",
        type=['pdf', 'png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="ניתן להעלות מספר קבצים בו-זמנית"
    )
    
    if uploaded_files:
        st.info(f"📁 נבחרו {len(uploaded_files)} קבצים")
        
        # Show file list
        for i, file in enumerate(uploaded_files):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.text(f"📄 {file.name}")
            with col2:
                st.text(f"{file.size / 1024:.1f} KB")
            with col3:
                st.text(file.type.split('/')[-1].upper())
        
        st.divider()
        
        # Extract button
        if st.button("🚀 חלץ נתונים מכל הפוליסות", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            extracted_policies = []
            
            for i, file in enumerate(uploaded_files):
                status_text.text(f"מעבד: {file.name}...")
                progress_bar.progress((i + 1) / len(uploaded_files))
                
                try:
                    # Send to async extraction API to avoid timeout issues
                    files = {'file': (file.name, file.getvalue(), file.type)}
                    full_url = f"{backend_url}/extract_policy_async"
                    st.text(f"Calling: {full_url}")
                    print(f"Calling: {full_url}")

                    response = requests.post(
                        full_url,
                        files=files,
                        timeout=60
                    )
                    
                    if response.status_code == 202:
                        # Async job started, poll for completion
                        job_data = response.json()
                        job_id = job_data.get("jobId")
                        polling_url = job_data.get("pollingUrl") or f"{backend_url}/extract_policy/status/{job_id}"
                        
                        st.text(f"📋 Job started: {job_id}")
                        print(f"Job started: {job_id}, polling: {polling_url}")
                        
                        # Poll for completion with exponential backoff
                        poll_interval = POLL_INITIAL_INTERVAL_SECONDS
                        elapsed = 0
                        consecutive_errors = 0
                        
                        while elapsed < POLL_MAX_WAIT_SECONDS:
                            time.sleep(poll_interval)
                            elapsed += poll_interval
                            
                            try:
                                status_response = requests.get(polling_url, timeout=30)
                                if status_response.status_code == 200:
                                    consecutive_errors = 0  # Reset error count on success
                                    job_status = status_response.json()
                                    status = job_status.get("status")
                                    
                                    if status == "completed":
                                        data = job_status.get("result", {})
                                        data['_source_file'] = file.name
                                        extracted_policies.append(data)
                                        st.success(f"✅ {file.name} - חילוץ הושלם")
                                        break
                                    elif status == "failed":
                                        error_msg = job_status.get("error", "Unknown error")
                                        st.error(f"❌ {file.name} - שגיאה: {error_msg}")
                                        print(f"Job failed: {error_msg}")
                                        break
                                    else:
                                        # Still running, update status
                                        status_text.text(f"מעבד: {file.name}... ({elapsed}s)")
                                        # Increase poll interval with backoff
                                        poll_interval = min(poll_interval + POLL_BACKOFF_INCREMENT_SECONDS, POLL_MAX_INTERVAL_SECONDS)
                                else:
                                    consecutive_errors += 1
                                    print(f"Polling error: {status_response.status_code}")
                                    if consecutive_errors >= 3:
                                        st.warning(f"⚠️ {file.name} - בעיית תקשורת זמנית, ממשיך לנסות...")
                            except Exception as poll_error:
                                consecutive_errors += 1
                                print(f"Polling exception: {poll_error}")
                                if consecutive_errors >= 3:
                                    st.warning(f"⚠️ {file.name} - בעיית תקשורת זמנית, ממשיך לנסות...")
                        else:
                            # Timeout waiting for completion
                            st.error(f"❌ {file.name} - תם הזמן המוקצב לחילוץ")
                            print(f"Job timed out after {POLL_MAX_WAIT_SECONDS}s")
                    
                    elif response.status_code == 200:
                        # Sync response (fallback if async not available)
                        data = response.json()
                        data['_source_file'] = file.name
                        extracted_policies.append(data)
                        st.success(f"✅ {file.name} - חילוץ הושלם")
                    else:
                        st.error(f"❌ {file.name} - שגיאה: {response.status_code}")
                        print(f"Error response: {response.status_code} - {response.text}")
                        st.text(f"Response: {response.text}")
                        
                except Exception as e:
                    st.error(f"❌ {file.name} - שגיאה: {str(e)}")
                    print(f"Exception: {str(e)}")
            
            progress_bar.progress(100)
            status_text.text("✨ החילוץ הושלם!")
            
            # Store in session state
            st.session_state.extracted_policies = extracted_policies
            
            if extracted_policies:
                st.balloons()
                st.success(f"🎉 חולצו בהצלחה {len(extracted_policies)} פוליסות!")
                st.info("👈 עבור ללשונית 'סקירת נתונים' לצפייה בתוצאות")

                # Save session to backend
                try:
                    session_payload = {
                        "family_name": st.session_state.family_name,
                        "policies": extracted_policies,
                    }
                    requests.post(
                        f"{backend_url}/sessions",
                        json=session_payload,
                        timeout=10,
                    )
                except Exception:
                    pass  # Non-critical; don't block the user

# ==================== TAB 2: Review Data ====================
with tab2:
    st.markdown('<div class="section-header"><h2>סקירת נתונים שחולצו</h2></div>', unsafe_allow_html=True)
    
    if not st.session_state.extracted_policies:
        st.warning("⚠️ לא נמצאו פוליסות. העלה קבצים בלשונית הראשונה.")
    else:
        # Summary cards
        total_premium = 0
        all_members = set()

        for policy in st.session_state.extracted_policies:
            if 'total_monthly_premium' in policy:
                total_premium += policy.get('total_monthly_premium') or 0
            if 'policyholder' in policy and 'name' in policy['policyholder']:
                raw_name = policy['policyholder']['name']
                all_members.add(mask_name(raw_name) if not st.session_state.show_sensitive else raw_name)

        # Summary row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("פוליסות", len(st.session_state.extracted_policies))
        with col2:
            st.metric("מבוטחים", len(all_members))
        with col3:
            st.metric("סה״כ פרמיה חודשית", f"₪{total_premium:,.2f}")
        
        st.divider()
        
        # Display each policy
        for i, policy in enumerate(st.session_state.extracted_policies):
            # Prepare display copy with PII masked when toggle is off
            display = policy if st.session_state.show_sensitive else sanitize_policy(policy)

            with st.expander(
                f"📄 פוליסה {i+1}: {policy.get('_source_file', 'Unknown')}",
                expanded=(i == 0)
            ):
                # Policy header
                col1, col2 = st.columns(2)

                with col1:
                    if 'policyholder' in display:
                        ph = display['policyholder']
                        st.markdown(f"**מבוטח:** {ph.get('name', 'N/A')}")
                        if st.session_state.show_sensitive:
                            st.markdown(f"**ת.ז.:** {ph.get('id_number', 'N/A')}")
                        else:
                            st.markdown(f"**ת.ז.:** {ph.get('id_number', 'N/A')} 🔒")
                        st.markdown(f"**תאריך לידה:** {ph.get('date_of_birth', 'N/A')}")

                with col2:
                    if 'carrier' in display:
                        carrier = display['carrier']
                        st.markdown(f"**חברת ביטוח:** {carrier.get('name', 'N/A')}")
                    st.markdown(f"**מספר פוליסה:** {display.get('policy_number', 'N/A')}")
                    st.markdown(f"**פרמיה חודשית:** ₪{(display.get('total_monthly_premium') or 0):,.2f}")

                # Coverages
                if 'coverages' in display and display['coverages']:
                    st.markdown("---")
                    st.markdown("**כיסויים:**")

                    coverage_data = []
                    for cov in display['coverages']:
                        coverage_data.append({
                            "סוג כיסוי": cov.get('type', ''),
                            "שם מוצר": cov.get('product_name', ''),
                            "פרמיה": f"₪{(cov.get('premium', {}).get('final_monthly') or 0):,.2f}" if isinstance(cov.get('premium'), dict) else f"₪{(cov.get('premium') or 0):,.2f}"
                        })

                    st.dataframe(coverage_data, use_container_width=True, hide_index=True)

                # Exclusions
                if 'exclusions' in display and display['exclusions']:
                    st.markdown("---")
                    st.markdown("**החרגות:**")
                    for exc in display['exclusions']:
                        st.markdown(f"- {exc.get('coverage', '')}: {', '.join(exc.get('conditions', []))}")

                # Sanitized JSON viewer (read-only)
                with st.expander("📝 JSON גולמי"):
                    st.json(display)

        # Form-based editing
        st.divider()
        st.markdown('<div class="section-header"><h2>עריכת נתונים</h2><p>ניתן לערוך את הנתונים ידנית לפני יצירת תיק הביטוח</p></div>', unsafe_allow_html=True)

        if not st.session_state.show_sensitive:
            st.info("להצגת ועריכת הנתונים המלאים, הפעל את מתג 'הצג מידע רגיש' בסרגל הצד.")

        for i, policy in enumerate(st.session_state.extracted_policies):
            with st.expander(f"עריכת פוליסה {i+1}: {policy.get('_source_file', '')}"):
                # Determine display values based on sensitive toggle
                raw_name = policy.get('policyholder', {}).get('name', '')
                display_name = raw_name if st.session_state.show_sensitive else mask_name(raw_name)
                raw_carrier = policy.get('carrier', {}).get('name', '')

                ec1, ec2 = st.columns(2)
                with ec1:
                    new_name = st.text_input(
                        "שם מבוטח",
                        value=display_name,
                        key=f"edit_name_{i}",
                        disabled=not st.session_state.show_sensitive,
                    )
                    new_pnum = st.text_input(
                        "מספר פוליסה",
                        value=policy.get('policy_number', ''),
                        key=f"edit_pnum_{i}",
                    )
                with ec2:
                    new_carrier = st.text_input(
                        "חברת ביטוח",
                        value=raw_carrier,
                        key=f"edit_carrier_{i}",
                    )
                    new_premium = st.number_input(
                        "פרמיה חודשית",
                        value=float(policy.get('total_monthly_premium') or 0),
                        key=f"edit_prem_{i}",
                        format="%.2f",
                        min_value=0.0,
                    )

                if st.button("שמור שינויים", key=f"save_policy_{i}"):
                    if 'policyholder' not in policy:
                        policy['policyholder'] = {}
                    # Only update name if sensitive is on (field was editable)
                    if st.session_state.show_sensitive:
                        policy['policyholder']['name'] = new_name
                    policy['policy_number'] = new_pnum
                    if 'carrier' not in policy:
                        policy['carrier'] = {}
                    policy['carrier']['name'] = new_carrier
                    policy['total_monthly_premium'] = new_premium
                    st.success("השינויים נשמרו!")
                    st.rerun()

# ==================== TAB 3: Generate Portfolio ====================
with tab3:
    st.markdown('<div class="section-header"><h2>יצירת תיק ביטוח משפחתי</h2></div>', unsafe_allow_html=True)
    
    if not st.session_state.extracted_policies:
        st.warning("⚠️ לא נמצאו פוליסות. העלה קבצים בלשונית הראשונה.")
    else:
        # Portfolio settings
        col1, col2 = st.columns(2)
        with col1:
            portfolio_family_name = st.text_input(
                "שם משפחה לתיק",
                value=st.session_state.family_name or "ישראלי"
            )
        with col2:
            report_date = st.date_input(
                "תאריך הדוח",
                value=date.today()
            )
        
        # Email option
        send_email = st.checkbox("📧 שלח לינק למייל", value=False)
        recipient_email = None
        if send_email:
            recipient_email = st.text_input(
                "כתובת מייל",
                placeholder="example@email.com",
                help="הזן כתובת מייל לקבלת קישור הורדה"
            )
        
        st.divider()
        
        # Preview what will be included
        st.markdown("### 📋 פוליסות שייכללו בתיק:")
        
        # Convert extracted policies to portfolio format
        family_members = []
        insurance_products = []
        
        for policy in st.session_state.extracted_policies:
            # Extract member
            if 'policyholder' in policy:
                member_name = policy['policyholder'].get('name', 'לא ידוע')
                if member_name not in [m['name'] for m in family_members]:
                    family_members.append({
                        "name": member_name,
                        "role": "מבוטח"
                    })
            
            # Extract products
            if 'coverages' in policy:
                for cov in policy['coverages']:
                    product = {
                        "member_name": policy.get('policyholder', {}).get('name', 'לא ידוע'),
                        "policy_number": policy.get('policy_number', ''),
                        "start_date": cov.get('period', {}).get('start', str(date.today())),
                        "company": policy.get('carrier', {}).get('name', ''),
                        "product_name": cov.get('type', ''),
                        "details": cov.get('product_name', ''),
                        "premium": (cov.get('premium', {}).get('final_monthly') or 0) if isinstance(cov.get('premium'), dict) else (cov.get('premium') or 0),
                        "exclusions": '',
                        "discounts": ''
                    }
                    
                    # Check for exclusions
                    if 'exclusions' in policy:
                        for exc in policy['exclusions']:
                            if exc.get('coverage') == cov.get('type') or exc.get('appendix') == cov.get('appendix_number'):
                                product['exclusions'] = ', '.join(exc.get('conditions', []))
                    
                    # Check for discounts
                    if isinstance(cov.get('premium'), dict):
                        discount = cov['premium'].get('discount_percent') or 0
                        if discount and discount > 0:
                            product['discounts'] = f"{discount}%"
                    
                    insurance_products.append(product)
        
        # Show preview table
        if insurance_products:
            preview_data = []
            for prod in insurance_products:
                display_member = prod['member_name'] if st.session_state.show_sensitive else mask_name(prod['member_name'])
                preview_data.append({
                    "מבוטח": display_member,
                    "חברה": prod['company'],
                    "מוצר": prod['product_name'],
                    "פרמיה": f"₪{prod['premium']:,.2f}" if isinstance(prod['premium'], (int, float)) else prod['premium']
                })
            
            st.dataframe(preview_data, use_container_width=True, hide_index=True)
            
            total = sum(p['premium'] for p in insurance_products if isinstance(p['premium'], (int, float)))
            st.markdown(f"**סה״כ פרמיה חודשית: ₪{total:,.2f}**")
        
        st.divider()
        
        # Generate button
        if st.button("📊 צור תיק ביטוח Excel", type="primary", use_container_width=True):
            # Email validation if send_email is checked
            email_valid = True
            if send_email and recipient_email:
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, recipient_email):
                    st.error("❌ כתובת המייל אינה תקינה")
                    email_valid = False
            elif send_email and not recipient_email:
                st.error("❌ נא להזין כתובת מייל")
                email_valid = False

            if not send_email or email_valid:
                with st.spinner("מייצר תיק ביטוח..."):
                    # Optionally mask PII in exports
                    export_products = insurance_products
                    export_members = family_members
                    if not st.session_state.show_sensitive:
                        export_products = [
                            {**p, "member_name": mask_name(p["member_name"])} for p in insurance_products
                        ]
                        export_members = [
                            {**m, "name": mask_name(m["name"])} for m in family_members
                        ]

                    # Prepare portfolio request
                    portfolio_request = {
                        "family_name": portfolio_family_name,
                        "report_date": str(report_date),
                        "family_members": export_members,
                        "insurance_products": export_products,
                    }

                    # Add email if provided
                    if send_email and recipient_email:
                        portfolio_request["recipient_email"] = recipient_email

                    try:
                        response = requests.post(
                            f"{backend_url}/generate_insurance_portfolio",
                            json=portfolio_request,
                            timeout=60
                        )

                        if response.status_code == 200:
                            content_type = response.headers.get('Content-Type', '')

                            if 'application/json' in content_type:
                                result = response.json()
                                st.success("✅ תיק הביטוח נוצר בהצלחה!")

                                # Show email confirmation if email was sent
                                if send_email and recipient_email:
                                    st.info(f"📧 קישור ההורדה נשלח למייל: {recipient_email}")

                                if 'downloadUrl' in result:
                                    st.markdown(f"### [📥 הורד את תיק הביטוח]({result['downloadUrl']})")

                                if 'summary' in result:
                                    st.json(result['summary'])
                            else:
                                # Direct file download
                                st.success("✅ תיק הביטוח נוצר בהצלחה!")
                                st.download_button(
                                    label="📥 הורד תיק ביטוח Excel",
                                    data=response.content,
                                    file_name=f"תיק_ביטוח_{portfolio_family_name}_{report_date}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                        else:
                            st.error(f"❌ שגיאה: {response.status_code} - {response.text}")

                    except Exception as e:
                        st.error(f"❌ שגיאת חיבור: {str(e)}")
        
        # Manual JSON input (collapsed) — display sanitized when toggle is off
        with st.expander("🔧 הזנה ידנית (JSON)"):
            st.caption("למשתמשים מתקדמים - הזנת JSON ישירות")

            portfolio_payload = {
                "family_name": portfolio_family_name,
                "report_date": str(report_date),
                "family_members": family_members,
                "insurance_products": insurance_products,
            }
            display_payload = portfolio_payload if st.session_state.show_sensitive else sanitize_policy(portfolio_payload)

            st.json(display_payload)

# ==================== TAB 4: Compare Policies ====================
with tab4:
    st.markdown('<div class="section-header"><h2>השוואת פוליסות</h2></div>', unsafe_allow_html=True)

    if not st.session_state.extracted_policies:
        st.warning("⚠️ לא נמצאו פוליסות. העלה קבצים בלשונית הראשונה.")
    else:
        st.markdown("בחר להשוות את הכיסויים והפרמיות בין הפוליסות שחולצו.")

        if st.button("השווה פוליסות", type="primary", use_container_width=True):
            with st.spinner("מבצע השוואה..."):
                try:
                    compare_data = st.session_state.extracted_policies
                    response = requests.post(
                        f"{backend_url}/compare_policies",
                        json={"policies": compare_data},
                        timeout=30
                    )

                    if response.status_code == 200:
                        result = response.json()
                        # Sanitize comparison result when sensitive toggle is off
                        if not st.session_state.show_sensitive:
                            result = sanitize_policy(result)
                        st.success("ההשוואה הושלמה")

                        summary = result.get("policies", [])
                        if summary:
                            st.subheader("סיכום פוליסות")
                            st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

                        rows = result.get("rows", [])
                        columns = result.get("columns", [])
                        if rows:
                            st.subheader("השוואת כיסויים")
                            df = pd.DataFrame(rows)
                            if columns:
                                df = df.reindex(columns=columns)
                            st.dataframe(df, use_container_width=True)
                    else:
                        st.error(f"שגיאה: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"שגיאת חיבור: {str(e)}")

# ==================== TAB 5: Recent Sessions ====================
with tab5:
    st.markdown('<div class="section-header"><h2>חילוצים אחרונים</h2><p>צפייה בפוליסות שחולצו בעבר וטעינתן מחדש לעבודה.</p></div>', unsafe_allow_html=True)

    if st.button("רענן רשימה", key="refresh_sessions"):
        pass  # button press triggers a rerun which fetches fresh data

    try:
        sessions_resp = requests.get(f"{backend_url}/sessions", timeout=10)
        if sessions_resp.status_code == 200:
            sessions_data = sessions_resp.json().get("sessions", [])
            if not sessions_data:
                st.info("לא נמצאו חילוצים קודמים.")
            else:
                for sess in sessions_data:
                    created = sess.get("created_at", "")
                    try:
                        dt = datetime.fromisoformat(created)
                        display_date = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        display_date = created

                    raw_family = sess.get("family_name") or "ללא שם"
                    family = raw_family if st.session_state.show_sensitive else mask_name(raw_family)
                    count = sess.get("policy_count", 0)
                    sid = sess.get("session_id", "")

                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{family}** — {display_date}")
                    with col2:
                        st.text(f"{count} פוליסות")
                    with col3:
                        if st.button("טען", key=f"load_{sid}"):
                            try:
                                detail_resp = requests.get(
                                    f"{backend_url}/sessions/{sid}",
                                    timeout=10,
                                )
                                if detail_resp.status_code == 200:
                                    detail = detail_resp.json()
                                    st.session_state.extracted_policies = detail.get("policies", [])
                                    st.session_state.family_name = detail.get("family_name", "")
                                    st.success("✅ הנתונים נטענו בהצלחה!")
                                    st.rerun()
                                else:
                                    st.error("❌ שגיאה בטעינת החילוץ")
                            except Exception as load_err:
                                st.error(f"❌ שגיאה: {str(load_err)}")
        else:
            st.warning("⚠️ לא ניתן לטעון חילוצים אחרונים.")
    except Exception:
        st.info("📭 שירות החילוצים אינו זמין כרגע.")

# Footer
st.markdown("---")
st.markdown("""
<div class="di-footer">
    <div class="footer-brand">
        <strong>PolicyLens</strong> by <a href="https://documentinsight.ai">DocumentInsight.ai</a>
    </div>
    <div style="margin-top:4px;">
        <span style="background:linear-gradient(90deg,#17a2b8,#0056b3);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-weight:600;">
            Stop searching, start knowing
        </span>
    </div>
    <div style="margin-top:8px;color:#9ca3af;font-size:0.8rem;">
        &copy; 2024 DocumentInsight.ai — כל הזכויות שמורות
    </div>
</div>
""", unsafe_allow_html=True)
