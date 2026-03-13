import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Define the scope
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Retrieve the secret from Streamlit's TOML format
# "gcp_service_account" must match the name in your Secrets box
creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)

client = gspread.authorize(creds)
# Use your exact Sheet name here
sheet = client.open("smasya-samadhan-form").sheet1

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
