import streamlit as st
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from PyPDF2 import PdfReader
#from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="AI Support App", layout="wide")
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

# PDF File Path (Aapki file ka naam yahan likhein)
PDF_FILE_PATH = "bhopal_culture.pdf" 

# --- 2. RAG LOGIC (Background Processing) ---

def process_local_pdf(file_path):
    """Server side PDF ko read karke vector store banata hai"""
    if not os.path.exists(file_path):
        st.error(f"Error: {file_path} file nahi mili! Please check project folder.")
        return False
    
    # 1. Extract Text
    text = ""
    pdf_reader = PdfReader(file_path)
    for page in pdf_reader.pages:
        text += page.extract_text()
    
    # 2. Chunking
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_text(text)
    
    # 3. Create Vector Store
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
    return True

def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context. If the answer is not in
    provided context, just say, "Maaf kijiye, iska jawab document mein nahi hai.", don't provide the wrong answer.\n\n
    Context:\n {context}?\n
    Question: \n{question}\n
    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3, google_api_key=api_key)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

# --- 3. AUTO-PROCESS PDF ON LOAD ---
# Yeh check karta hai ki kya index pehle se bana hai, nahi to banata hai
if "processed" not in st.session_state:
    with st.spinner("AI Brain loading... Please wait."):
        success = process_local_pdf(PDF_FILE_PATH)
        if success:
            st.session_state.processed = True

# --- 4. UI LAYOUT ---
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.title("📝 Service Request Form")
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
    st.title("🤖 Chat with Our AI")
    st.info("Mein aapki help ke liye document se information nikal sakta hoon.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_question := st.chat_input("Puchiye apne sawal..."):
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            if "processed" in st.session_state:
                embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
                # Load index from local folder
                new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
                docs = new_db.similarity_search(user_question)
                
                chain = get_conversational_chain()
                response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
                
                res_text = response["output_text"]
                st.markdown(res_text)
                st.session_state.messages.append({"role": "assistant", "content": res_text})
            else:
                st.warning("PDF abhi tak process nahi hui hai.")
