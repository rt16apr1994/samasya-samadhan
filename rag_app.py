import streamlit as st
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from PyPDF2 import PdfReader
import os

# --- STABLE & SIMPLE IMPORTS ---
from langchain.chains.question_answering import load_qa_chain
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate

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
                # 1. Similarity Search (Document se relevant part nikalna)
                docs = st.session_state.vector_db.similarity_search(prompt, k=3)
                
                # 2. Prompt Template
                template = """Answer the question based only on the provided context. 
                If the answer is not in the context, use your general knowledge.
                
                Context: {context}
                Question: {question}
                Answer:"""
                
                QA_PROMPT = PromptTemplate(template=template, input_variables=["context", "question"])
                
                # 3. Chain execution
                chain = load_qa_chain(llm, chain_type="stuff", prompt=QA_PROMPT)
                response = chain({"input_documents": docs, "question": prompt}, return_only_outputs=True)
                answer = response["output_text"]
            else:
                # Fallback to direct LLM
                response = llm.invoke(prompt)
                answer = response.content
            
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
