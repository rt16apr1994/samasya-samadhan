import streamlit as st
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Support App", layout="wide")

# AI Setup
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
except:
    st.error("Gemini API Key missing in Secrets!")

# Sheets Setup
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
try:
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open("smasya-samadhan-form").sheet1
except:
    st.error("Google Sheets credentials error!")

# --- 2. THE UI LAYOUT (2 Columns) ---
# Hum complex floating icon ki jagah 2 columns use karenge taaki error na aaye
col1, col2 = st.columns([2, 1], gap="large")

with col1:
    st.title("📝 Service Request Form")
    with st.form("user_form", clear_on_submit=True):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        contact = st.text_input("Contact Number")
        problem = st.text_area("Problem Description")
        
        submitted = st.form_submit_button("Submit Request")
        if submitted:
            if full_name and email and contact and problem:
                sheet.append_row([full_name, email, contact, problem])
                st.success("Data saved successfully!")
            else:
                st.warning("Please fill all fields.")

with col2:
    st.title("🤖 AI Assistant")
    st.write("How can I help you today?")
    
    # Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Container for messages
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("Type your message..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                response = model.generate_content(prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
