import streamlit as st
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from PyPDF2 import PdfReader
import os

# Naye Stable Imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate


# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Hybrid AI Support", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Please add GEMINI_API_KEY in Secrets.")
    st.stop()

api_key = st.secrets["GEMINI_API_KEY"]

# File Path (Apni file ka sahi naam yahan likhein)
PDF_FILE_PATH = "bhopal_culture.pdf" 

# --- 2. RAG LOGIC ---

def setup_rag(file_path):
    if not os.path.exists(file_path):
        return None
    
    # Text Extraction
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    # Chunking
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(text)
    
    # Embeddings & Vector Store
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    return vector_store

# Initializing AI Models
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.4)

# Load RAG only once
if "vector_db" not in st.session_state:
    with st.spinner("Document process ho raha hai..."):
        db = setup_rag(PDF_FILE_PATH)
        if db:
            st.session_state.vector_db = db
            st.success("Document loaded successfully!")
        else:
            st.warning("Document file nahi mili. AI ab general mode mein kaam karega.")
            st.session_state.vector_db = None

# --- 3. UI LAYOUT ---
col1, col2 = st.columns([1, 1])

with col1:
    st.title("📝 Service Form")
    # (Aapka Google Sheets Form yahan aayega - pehle wala code same rakhein)
    st.info("Form fill karein ya right side AI se baat karein.")
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

with col2:
    st.title("🤖 Hybrid AI Chatbot")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- Chat Processing Logic ---
if prompt := st.chat_input("Puchiye apna sawal..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_text = ""
        
        if st.session_state.vector_db:
            # 1. Prompt Taiyar Karein
            system_prompt = (
                "You are an assistant for question-answering tasks. "
                "Use the following pieces of retrieved context to answer the question. "
                "If the answer is not in the context, use your own knowledge to answer, "
                "but prioritize the document context first.\n\n"
                "{context}"
            )
            chat_prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
            ])

            # 2. Chain Banayein
            question_answer_chain = create_stuff_documents_chain(llm, chat_prompt)
            rag_chain = create_retrieval_chain(st.session_state.vector_db.as_retriever(), question_answer_chain)

            # 3. Answer Generate Karein
            response = rag_chain.invoke({"input": prompt})
            response_text = response["answer"]
        else:
            # Agar document nahi hai toh seedhe LLM se puchein
            full_ai_response = llm.invoke(prompt)
            response_text = full_ai_response.content
        
        st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
