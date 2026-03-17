import streamlit as st
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from PyPDF2 import PdfReader
import os

# --- STABLE IMPORTS (Updated for LangChain 2024/25) ---
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
# Yahan se error aa raha tha, ab hum naya path use kar rahe hain:
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Hybrid AI Support", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Please add GEMINI_API_KEY in Secrets.")
    st.stop()

api_key = st.secrets["GEMINI_API_KEY"]
PDF_FILE_PATH = "bhopal_culture.pdf" # Make sure this file is in your GitHub

# --- 2. RAG LOGIC ---
def setup_rag(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_text(text)
        
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
        vector_store = FAISS.from_texts(chunks, embedding=embeddings)
        return vector_store
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None

# AI Models
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.4)

if "vector_db" not in st.session_state:
    db = setup_rag(PDF_FILE_PATH)
    st.session_state.vector_db = db

# --- 3. UI LAYOUT ---
col1, col2 = st.columns([1, 1])

with col1:
    st.title("📝 Service Form")
    # Yahan aapka purana Google Sheets form logic paste karein
    with st.form("user_form", clear_on_submit=True):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        contact = st.text_input("Contact Number")
        role = st.selectbox("Select Your Role", ["Needy/Student/Learner", "Solver/Teacher/Trainer"])
        problem = st.text_area("Problem Description")
        
        submitted = st.form_submit_button("Submit Request")
        if submitted:
            # Google Sheets logic
            try:
                scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
                client = gspread.authorize(creds)
                sheet = client.open("smasya-samadhan-form").sheet1
                sheet.append_row([full_name, email, contact, role, problem])
                st.success("Aapka data save ho gaya hai!")
            except:
                st.error("Sheets connection error!")
    st.info("Fill the form or chat with AI on the right.")

with col2:
    st.title("🤖 Support Chat")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Puchiye apna sawal..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if st.session_state.vector_db:
                # Naya Retrieval Chain Process
                system_prompt = (
                    "You are a helpful assistant. Use the following context to answer. "
                    "If the answer isn't there, use your own knowledge. \n\n {context}"
                )
                chat_prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}"),
                ])
                
                combine_docs_chain = create_stuff_documents_chain(llm, chat_prompt)
                retrieval_chain = create_retrieval_chain(st.session_state.vector_db.as_retriever(), combine_docs_chain)
                
                response = retrieval_chain.invoke({"input": prompt})
                answer = response["answer"]
            else:
                # Fallback to direct LLM
                response = llm.invoke(prompt)
                answer = response.content
            
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
