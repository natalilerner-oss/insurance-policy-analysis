import streamlit as st
import requests
import json
import os
import jwt
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
st.set_page_config(page_title="Insurance Policy Analysis", page_icon="🛡️", layout="wide")

st.title("🛡️ Insurance Policy Analysis")

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    
    # Default to local function app port if running locally
    default_url = os.getenv("BACKEND_URL", "http://localhost:7071/api")
    backend_url = st.text_input("Backend URL", value=default_url)
    
    jwt_secret = st.text_input("JWT Secret", value=os.getenv("JWT_SECRET", ""), type="password")
    
    st.divider()
    st.info("Ensure the Azure Functions backend is running.")

def get_headers():
    headers = {}
    if jwt_secret:
        # Generate a dummy token signed with the secret just to pass the check
        # The backend expects 'sub' in payload
        payload = {
            "sub": "frontend-user",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow().replace(year=datetime.utcnow().year + 1)
        }
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        headers["Authorization"] = f"Bearer {token}"
    return headers

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Extract Policy", 
    "Portfolio Generation", 
    "Office Doc Extraction", 
    "Translate Text",
    "Translate File"
])

# --- Tab 1: Extract Policy ---
with tab1:
    st.header("Extract Policy Data")
    uploaded_file = st.file_uploader("Upload Policy (PDF/Image)", type=['pdf', 'png', 'jpg', 'jpeg'], key="policy_file")
    
    if uploaded_file and st.button("Extract", key="extract_btn"):
        files = {'file': (uploaded_file.name, uploaded_file, uploaded_file.type)}
        with st.spinner("Extracting data..."):
            try:
                # Based on analysis, extract_policy doesn't require JWT, but we can send it anyway
                response = requests.post(f"{backend_url}/extract_policy", files=files)
                if response.status_code == 200:
                    st.success("Extraction Complete")
                    data = response.json()
                    st.json(data)
                    
                    # Option to save for Portfolio
                    if st.button("Use for Portfolio Generation"):
                        st.session_state['portfolio_data'] = data
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")

# --- Tab 2: Portfolio Generation ---
with tab2:
    st.header("Generate Insurance Portfolio")
    
    input_method = st.radio("Input Method", ["Paste JSON", "Use Last Extraction"])
    
    input_data = ""
    if input_method == "Use Last Extraction":
        if 'portfolio_data' in st.session_state:
            input_data = json.dumps(st.session_state['portfolio_data'], indent=2, ensure_ascii=False)
        else:
            st.warning("No extraction data found in session.")
    
    json_input = st.text_area("Portfolio Data (JSON)", value=input_data, height=300)
    
    if st.button("Generate Portfolio"):
        if not jwt_secret:
            st.warning("JWT Secret is likely required for this endpoint.")
        
        try:
            payload = json.loads(json_input)
            with st.spinner("Generating Portfolio..."):
                response = requests.post(
                    f"{backend_url}/generate_insurance_portfolio", 
                    json=payload,
                    headers=get_headers()
                )
                
                if response.status_code == 200:
                    # Depending on response type. Code says it uploads to blob and returns download_url usually?
                    # Let's check response content-type or if it's a direct download
                    try:
                        resp_json = response.json()
                        st.success("Portfolio Generated!")
                        if "download_url" in resp_json:
                            st.markdown(f"[Download Excel Report]({resp_json['download_url']})")
                        st.json(resp_json)
                    except:
                        # Maybe it returns bytes directly?
                        st.download_button(
                            label="Download Excel",
                            data=response.content,
                            file_name="portfolio.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")

        except json.JSONDecodeError:
            st.error("Invalid JSON")
        except Exception as e:
            st.error(f"Error: {e}")

# --- Tab 3: Office Doc Extraction ---
with tab3:
    st.header("Extract Text from Office Docs")
    office_file = st.file_uploader("Upload File (.docx, .pptx, .xlsx, .pdf)", type=['docx', 'pptx', 'xlsx', 'pdf'], key="office_file")
    
    if office_file and st.button("Extract Text"):
        files = {'file': (office_file.name, office_file, office_file.type)}
        with st.spinner("Extracting text..."):
            try:
                response = requests.post(
                    f"{backend_url}/extract", 
                    files=files,
                    headers=get_headers()
                )
                if response.status_code == 200:
                    st.text_area("Extracted Text", value=response.text, height=400)
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Error: {e}")

# --- Tab 4: Translate Text ---
with tab4:
    st.header("Translate Text")
    txt_to_translate = st.text_area("Text to Translate")
    col1, col2 = st.columns(2)
    with col1:
        from_lang = st.text_input("From Lang", "en")
    with col2:
        to_lang = st.text_input("To Lang", "he")
        
    if st.button("Translate"):
        payload = {
            "text": txt_to_translate,
            "from": from_lang,
            "to": to_lang
        }
        try:
            response = requests.post(
                f"{backend_url}/translateText", 
                json=payload,
                headers=get_headers()
            )
            if response.status_code == 200:
                res = response.json()
                st.success("Translation:")
                st.write(res.get("translatedText", ""))
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"Error: {e}")

# --- Tab 5: Translate File ---
with tab5:
    st.header("Translate File (Async)")
    st.info("Note: This endpoint expects a URL to a file (SAS URL or public URL). The frontend doesn't support direct upload to blob yet.")
    
    file_url = st.text_input("File URL (must be accessible by backend)")
    if st.button("Start Translation Job"):
        payload = {
            "fileUrl": file_url,
            "from": "en",
            "to": "he"
        }
        try:
            response = requests.post(
                f"{backend_url}/translateFile", 
                json=payload,
                headers=get_headers()
            )
            if response.status_code == 202:
                job_data = response.json()
                st.success(f"Job Started! ID: {job_data.get('jobId')}")
                st.json(job_data)
                
                # Polling
                if st.button("Check Status"):
                    status_url = job_data.get('pollingUrl')
                    # Or construct manually if needed
                    st.write(f"Polling: {status_url}")
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"Error: {e}")
            
    # Check status by ID
    check_id = st.text_input("Check Job ID")
    if check_id and st.button("Check Status", key="check_status_btn"):
        try:
            response = requests.get(
                f"{backend_url}/translateFile/status/{check_id}",
                headers=get_headers()
            )
            if response.status_code == 200:
                st.json(response.json())
            else:
                st.write(response.text)
        except Exception as e:
            st.error(f"Error: {e}")
