import streamlit as st
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials
import pandas as pd

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="AI Support Assistant", layout="centered")

# --- 2. CONFIGURATION & SECRETS (Existing Logic) ---
# AI Brain Setup
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("AI connection error. Check your GEMINI_API_KEY secret.")

# Google Sheets Setup
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
try:
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    # CHANGE THIS to your actual Sheet Name
    sheet = client.open("smasya-samadhan-form").sheet1
except Exception as e:
    st.error("Google Sheets connection error. Check your credentials.")


# --- 3. SESSION STATE FOR CHATBOT ---
# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_open" not in st.session_state:
    st.session_state.chat_open = False

# --- 4. CUSTOM CSS FOR FLOATING CHAT BUBBLE ---
# Yeh CSS pure app ko standard Floating Chat UI jaisa dikhayega
st.markdown("""
<style>
    /* 1. Chat Container (Right-Bottom Corner) */
    .stChatContainer {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        display: flex;
        flex-direction: column-reverse; /* For correct input placement */
        align-items: flex-end;
    }

    /* 2. Floating Chat Icon (Bubble) */
    .stChatFloatingIcon {
        width: 60px;
        height: 60px;
        background-color: #ff4b4b; /* Streamlit default color, or change to #007bff for blue */
        border-radius: 50%;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 30px;
        color: white;
        margin-top: 10px;
        transition: transform 0.2s ease;
    }
    .stChatFloatingIcon:hover {
        transform: scale(1.1);
    }

    /* 3. The Chat Window (when open) */
    .stChatWindow {
        width: 350px;
        height: 450px;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        display: none; /* Initially hidden */
    }

    /* Show Chat Window when open */
    .show-chat .stChatWindow {
        display: flex;
    }

    /* Chat Header */
    .stChatHeader {
        background-color: #f0f2f6;
        padding: 10px 15px;
        border-bottom: 1px solid #ddd;
        font-weight: bold;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Close button in header */
    .stCloseChat {
        cursor: pointer;
        color: #888;
        font-size: 20px;
    }

    /* Message Area (make it scrollable) */
    .stChatHistory {
        flex: 1;
        overflow-y: auto;
        padding: 15px;
        background-color: #fafafa;
    }

    /* Streamlit's internal chat elements must be modified to fit the small window */
    .element-container:has(div.stChatFloatingIcon) {
        pointer-events: none; /* Make clicking the icon work */
    }
</style>
""", unsafe_allow_with_html=True)

# --- 5. CHATBOT UI & LOGIC ---

# 5.1 Chat Logic Functions
def get_ai_response(prompt):
    """Gets response from Gemini Model"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "Sorry, I am facing connectivity issues."

def toggle_chat():
    """Opens/Closes the chat window"""
    st.session_state.chat_open = not st.session_state.chat_open

# 5.2 Chat Widget (The entire right-bottom section)
# We wrap it in a div that CSS targets
chat_class = "show-chat stChatContainer" if st.session_state.chat_open else "stChatContainer"

st.markdown(f'<div class="{chat_class}">', unsafe_allow_with_html=True)

# 5.2.1 Chat Window Contents (When Open)
if st.session_state.chat_open:
    # Header with title and close button (needs to be HTML)
    st.markdown("""
    <div class="stChatHeader">
        <div>🤖 AI Support</div>
        <div class="stCloseChat" onclick="window.location.reload();">×</div>
    </div>
    """, unsafe_allow_with_html=True)
    
    # We use streamlit's native chat elements *inside* our CSS container
    with st.container(height=350, border=False): # Controls internal height
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat Input (stays inside the open window)
    if prompt := st.chat_input("Ask me something..."):
        # 1. Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 2. Add AI response immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            response_text = get_ai_response(prompt)
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})

# 5.2.2 Floating Icon (The Bubble)
# When clicked, it calls toggle_chat
if st.button("💬", key="chat_icon", on_click=toggle_chat, type="secondary"):
    pass # button action handled by callback

# Apply CSS classes to the button we just made
st.markdown('<script>document.getElementById("chat_icon").classList.add("stChatFloatingIcon");</script>', unsafe_allow_with_html=True)

st.markdown('</div>', unsafe_allow_with_html=True) # Close stChatContainer


# --- 6. MAIN FORM (Existing Logic - Right Side of Bubble) ---
# Page contents must be written *after* the chatbot container for correct rendering
st.title("Service Request Form")
st.write("Submit your details below.")

with st.form("user_form", clear_on_submit=True):
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    contact = st.text_input("Contact Number")
    problem = st.text_area("Problem Description")
    
    if st.form_submit_button("Submit Request"):
        if full_name and email and contact and problem:
            sheet.append_row([full_name, email, contact, problem])
            st.success("Your request has been logged. Our AI chatbot can help you while you wait!")
        else:
            st.error("Please fill all fields.")
