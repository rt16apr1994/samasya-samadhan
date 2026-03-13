import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# 1. Setup Connection to Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
# In production, use st.secrets to store these credentials safely
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("Your_Sheet_Name").sheet1

# 2. UI Form
st.title("AI Support Assistant")
with st.form("user_form", clear_on_submit=True):
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    contact = st.text_input("Contact Number")
    problem = st.text_area("Problem Description")
    
    submitted = st.form_submit_button("Submit")
    
    if submitted:
        # Save to Google Sheets
        sheet.append_row([full_name, email, contact, problem])
        st.success("Data submitted successfully!")
