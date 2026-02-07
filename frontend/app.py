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
    mask_id_number, mask_name, mask_address,
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

# Custom CSS for RTL support and better styling
st.markdown("""
<style>
    .rtl-text { direction: rtl; text-align: right; }
    .policy-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #4F46E5;
    }
    .premium-highlight {
        font-size: 1.5em;
        color: #10B981;
        font-weight: bold;
    }
    .coverage-item {
        background-color: #EEF2FF;
        padding: 8px 12px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 10px 20px;
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
    st.image("https://documentinsight.ai/logo.png", width=200)
    st.header("⚙️ הגדרות")

    default_url = os.getenv("BACKEND_URL", "http://localhost:7071/api")
    backend_url = st.text_input("Backend URL", value=default_url)

    st.divider()
    show_sensitive = st.toggle("🔓 הצג מידע רגיש", value=st.session_state.show_sensitive)
    st.session_state.show_sensitive = show_sensitive
    if not show_sensitive:
        st.caption("🔒 מידע אישי מוסתר")

    st.divider()
    st.markdown("**DocumentInsight.ai**")
    st.caption("From a junkyard of information to a gallery of Knowledge")

# Header
col1, col2 = st.columns([1, 4])
with col1:
    st.markdown("# 🔍")
with col2:
    st.title("PolicyLens")
    st.caption("מערכת חכמה לחילוץ וניהול פוליסות ביטוח")

st.divider()

# Main workflow tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 1. העלאת פוליסות",
    "📋 2. סקירת נתונים", 
    "📊 3. יצירת תיק ביטוח",
    "🔍 4. השוואת פוליסות",
    "🕐 5. חילוצים אחרונים"
])

# ==================== TAB 1: Upload Policies ====================
with tab1:
    st.header("העלאת מסמכי פוליסה")
    st.markdown("העלה קבצי PDF או תמונות של פוליסות ביטוח. המערכת תחליץ את הנתונים באופן אוטומטי.")
    
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
    st.header("סקירת נתונים שחולצו")
    
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
                all_members.add(policy['policyholder']['name'])
        
        # Summary row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📋 פוליסות", len(st.session_state.extracted_policies))
        with col2:
            st.metric("👥 מבוטחים", len(all_members))
        with col3:
            st.metric("💰 סה״כ פרמיה חודשית", f"₪{total_premium:,.2f}")
        
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
        st.markdown("### ✏️ עריכת נתונים")
        st.caption("ניתן לערוך את הנתונים ידנית לפני יצירת תיק הביטוח")

        for i, policy in enumerate(st.session_state.extracted_policies):
            with st.expander(f"📝 עריכת פוליסה {i+1}: {policy.get('_source_file', '')}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    new_name = st.text_input(
                        "שם מבוטח",
                        value=policy.get('policyholder', {}).get('name', ''),
                        key=f"edit_name_{i}",
                    )
                    new_pnum = st.text_input(
                        "מספר פוליסה",
                        value=policy.get('policy_number', ''),
                        key=f"edit_pnum_{i}",
                    )
                with ec2:
                    new_carrier = st.text_input(
                        "חברת ביטוח",
                        value=policy.get('carrier', {}).get('name', ''),
                        key=f"edit_carrier_{i}",
                    )
                    new_premium = st.number_input(
                        "פרמיה חודשית",
                        value=float(policy.get('total_monthly_premium') or 0),
                        key=f"edit_prem_{i}",
                        format="%.2f",
                        min_value=0.0,
                    )

                if st.button("💾 שמור שינויים", key=f"save_policy_{i}"):
                    if 'policyholder' not in policy:
                        policy['policyholder'] = {}
                    policy['policyholder']['name'] = new_name
                    policy['policy_number'] = new_pnum
                    if 'carrier' not in policy:
                        policy['carrier'] = {}
                    policy['carrier']['name'] = new_carrier
                    policy['total_monthly_premium'] = new_premium
                    st.success("✅ השינויים נשמרו!")
                    st.rerun()

# ==================== TAB 3: Generate Portfolio ====================
with tab3:
    st.header("יצירת תיק ביטוח משפחתי")
    
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
    st.header("השוואת פוליסות")

    if not st.session_state.extracted_policies:
        st.warning("⚠️ לא נמצאו פוליסות. העלה קבצים בלשונית הראשונה.")
    else:
        st.markdown("בחר להשוות את הכיסויים והפרמיות בין הפוליסות שחולצו.")

        if st.button("🔍 השווה פוליסות", type="primary", use_container_width=True):
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
                        st.success("✅ ההשוואה הושלמה")

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
                        st.error(f"❌ שגיאה: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"❌ שגיאת חיבור: {str(e)}")

# ==================== TAB 5: Recent Sessions ====================
with tab5:
    st.header("חילוצים אחרונים")
    st.markdown("צפייה בפוליסות שחולצו בעבר וטעינתן מחדש לעבודה.")

    if st.button("🔄 רענן רשימה", key="refresh_sessions"):
        pass  # button press triggers a rerun which fetches fresh data

    try:
        sessions_resp = requests.get(f"{backend_url}/sessions", timeout=10)
        if sessions_resp.status_code == 200:
            sessions_data = sessions_resp.json().get("sessions", [])
            if not sessions_data:
                st.info("📭 לא נמצאו חילוצים קודמים.")
            else:
                for sess in sessions_data:
                    created = sess.get("created_at", "")
                    try:
                        dt = datetime.fromisoformat(created)
                        display_date = dt.strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        display_date = created

                    family = sess.get("family_name") or "ללא שם"
                    count = sess.get("policy_count", 0)
                    sid = sess.get("session_id", "")

                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{family}** — {display_date}")
                    with col2:
                        st.text(f"{count} פוליסות")
                    with col3:
                        if st.button("📂 טען", key=f"load_{sid}"):
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
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8em;">
    <p>PolicyLens by <a href="https://documentinsight.ai">DocumentInsight.ai</a></p>
    <p>Stop searching, start knowing 🔍</p>
</div>
""", unsafe_allow_html=True)
