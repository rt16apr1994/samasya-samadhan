import streamlit as st
import gspread
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="RAG Support App", layout="wide")
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

# --- 2. RAG FUNCTIONS (PDF Processing) ---
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
    return vector_store

def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context. If the answer is not in
    provided context, just say, "answer is not available in the context", don't provide the wrong answer.\n\n
    Context:\n {context}?\n
    Question: \n{question}\n
    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3, google_api_key=api_key)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

# --- 3. UI LAYOUT ---
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.title("📝 Form & PDF Upload")
    
    # PDF Upload Section
    uploaded_files = st.file_uploader("Upload PDF for AI Context", accept_multiple_files=True, type=["pdf"])
    if st.button("Process PDF"):
        with st.spinner("Reading PDF..."):
            raw_text = get_pdf_text(uploaded_files)
            text_chunks = get_text_chunks(raw_text)
            get_vector_store(text_chunks)
            st.success("PDF Processed! Now ask questions in the chat.")

    st.divider()

    # Existing Form
    with st.form("smasya-samadhan-form", clear_on_submit=True):
        full_name = st.text_input("Full Name")
        role = st.selectbox("Select Your Role", ["Needy/Student/Learner", "Solver/Teacher/Trainer"])
        problem = st.text_area("Problem Description")
        submitted = st.form_submit_button("Submit Request")
        if submitted:
            # (Sheets logic remains same)
            st.success("Data Saved!")

with col2:
    st.title("🤖 RAG AI Chat")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_question := st.chat_input("Ask about the PDF..."):
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        # RAG Logic for response
        with st.chat_message("assistant"):
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
            new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
            docs = new_db.similarity_search(user_question)
            
            chain = get_conversational_chain()
            response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
            
            final_res = response["output_text"]
            st.markdown(final_res)
            st.session_state.messages.append({"role": "assistant", "content": final_res})
