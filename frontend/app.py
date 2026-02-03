import streamlit as st
import requests
import json
import os
import base64
import time
from datetime import datetime, date
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

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

# Sidebar Configuration
with st.sidebar:
    st.image("https://documentinsight.ai/logo.png", width=200)
    st.header("⚙️ הגדרות")
    
    default_url = os.getenv("BACKEND_URL", "http://localhost:7071/api")
    backend_url = st.text_input("Backend URL", value=default_url)
    
    st.divider()
    st.markdown("**DocumentInsight.ai**")
    st.caption("From a junkyard of information to a gallery of Knowledge")

# Initialize session state
if 'extracted_policies' not in st.session_state:
    st.session_state.extracted_policies = []
if 'family_name' not in st.session_state:
    st.session_state.family_name = ""

# Header
col1, col2 = st.columns([1, 4])
with col1:
    st.markdown("# 🔍")
with col2:
    st.title("PolicyLens")
    st.caption("מערכת חכמה לחילוץ וניהול פוליסות ביטוח")

st.divider()

# Main workflow tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📤 1. העלאת פוליסות",
    "📋 2. סקירת נתונים", 
    "📊 3. יצירת תיק ביטוח",
    "🔍 4. השוואת פוליסות"
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
                        max_wait_time = 600  # 10 minutes max
                        poll_interval = 5  # Start with 5 seconds
                        elapsed = 0
                        
                        while elapsed < max_wait_time:
                            time.sleep(poll_interval)
                            elapsed += poll_interval
                            
                            try:
                                status_response = requests.get(polling_url, timeout=30)
                                if status_response.status_code == 200:
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
                                        # Increase poll interval with backoff, max 15 seconds
                                        poll_interval = min(poll_interval + 2, 15)
                                else:
                                    print(f"Polling error: {status_response.status_code}")
                            except Exception as poll_error:
                                print(f"Polling exception: {poll_error}")
                        else:
                            # Timeout waiting for completion
                            st.error(f"❌ {file.name} - תם הזמן המוקצב לחילוץ")
                            print(f"Job timed out after {max_wait_time}s")
                    
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
            with st.expander(
                f"📄 פוליסה {i+1}: {policy.get('_source_file', 'Unknown')}",
                expanded=(i == 0)
            ):
                # Policy header
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'policyholder' in policy:
                        ph = policy['policyholder']
                        st.markdown(f"**מבוטח:** {ph.get('name', 'N/A')}")
                        st.markdown(f"**ת.ז.:** {ph.get('id_number', 'N/A')}")
                        st.markdown(f"**תאריך לידה:** {ph.get('date_of_birth', 'N/A')}")
                
                with col2:
                    if 'carrier' in policy:
                        carrier = policy['carrier']
                        st.markdown(f"**חברת ביטוח:** {carrier.get('name', 'N/A')}")
                    st.markdown(f"**מספר פוליסה:** {policy.get('policy_number', 'N/A')}")
                    st.markdown(f"**פרמיה חודשית:** ₪{(policy.get('total_monthly_premium') or 0):,.2f}")
                
                # Coverages
                if 'coverages' in policy and policy['coverages']:
                    st.markdown("---")
                    st.markdown("**כיסויים:**")
                    
                    coverage_data = []
                    for cov in policy['coverages']:
                        coverage_data.append({
                            "סוג כיסוי": cov.get('type', ''),
                            "שם מוצר": cov.get('product_name', ''),
                            "פרמיה": f"₪{(cov.get('premium', {}).get('final_monthly') or 0):,.2f}" if isinstance(cov.get('premium'), dict) else f"₪{(cov.get('premium') or 0):,.2f}"
                        })
                    
                    st.dataframe(coverage_data, use_container_width=True, hide_index=True)
                
                # Exclusions
                if 'exclusions' in policy and policy['exclusions']:
                    st.markdown("---")
                    st.markdown("**החרגות:**")
                    for exc in policy['exclusions']:
                        st.markdown(f"- {exc.get('coverage', '')}: {', '.join(exc.get('conditions', []))}")
                
                # Raw JSON expander
                with st.expander("📝 JSON גולמי"):
                    st.json(policy)
        
        # Edit option
        st.divider()
        st.markdown("### ✏️ עריכת נתונים")
        st.caption("ניתן לערוך את הנתונים ידנית לפני יצירת תיק הביטוח")
        
        edited_json = st.text_area(
            "JSON מלא (לעריכה)",
            value=json.dumps(st.session_state.extracted_policies, indent=2, ensure_ascii=False),
            height=300
        )
        
        if st.button("💾 שמור שינויים"):
            try:
                st.session_state.extracted_policies = json.loads(edited_json)
                st.success("✅ השינויים נשמרו!")
            except json.JSONDecodeError as e:
                st.error(f"❌ שגיאת JSON: {e}")

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
                preview_data.append({
                    "מבוטח": prod['member_name'],
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
            with st.spinner("מייצר תיק ביטוח..."):
                # Prepare portfolio request
                portfolio_request = {
                    "family_name": portfolio_family_name,
                    "report_date": str(report_date),
                    "family_members": family_members,
                    "insurance_products": insurance_products
                }
                
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
                            
                            if 'download_url' in result:
                                st.markdown(f"### [📥 הורד את תיק הביטוח]({result['download_url']})")
                            
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
        
        # Manual JSON input (collapsed)
        with st.expander("🔧 הזנה ידנית (JSON)"):
            st.caption("למשתמשים מתקדמים - הזנת JSON ישירות")
            
            manual_json = st.text_area(
                "Portfolio JSON",
                value=json.dumps({
                    "family_name": portfolio_family_name,
                    "report_date": str(report_date),
                    "family_members": family_members,
                    "insurance_products": insurance_products
                }, indent=2, ensure_ascii=False),
                height=400
            )
            
            if st.button("שלח JSON ידני"):
                try:
                    payload = json.loads(manual_json)
                    response = requests.post(
                        f"{backend_url}/generate_insurance_portfolio",
                        json=payload,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        st.download_button(
                            label="📥 הורד Excel",
                            data=response.content,
                            file_name=f"portfolio_{date.today()}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error(f"Error: {response.status_code}")
                except Exception as e:
                    st.error(str(e))

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
                    response = requests.post(
                        f"{backend_url}/compare_policies",
                        json={"policies": st.session_state.extracted_policies},
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

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8em;">
    <p>PolicyLens by <a href="https://documentinsight.ai">DocumentInsight.ai</a></p>
    <p>Stop searching, start knowing 🔍</p>
</div>
""", unsafe_allow_html=True)
