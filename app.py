import streamlit as st
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURATION & AI SETUP ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# Google Sheets Setup
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("smasya-samadhan-form").sheet1

# --- 2. SIDEBAR CHATBOT ---
with st.sidebar:
    st.title("🤖 AI Support Chat")
    st.info("Ask me anything about your technical issues!")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("How can I help?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate AI response
        with st.chat_message("assistant"):
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

# --- 3. MAIN FORM (Existing Logic) ---
st.title("Service Request Form")
with st.form("user_form", clear_on_submit=True):
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    contact = st.text_input("Contact Number")
    problem = st.text_area("Problem Description")
    
    if st.form_submit_button("Submit Request"):
        sheet.append_row([full_name, email, contact, problem])
        st.success("Your request has been logged. Our AI chatbot in the sidebar can help you while you wait!")
