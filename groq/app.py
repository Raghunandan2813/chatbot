import streamlit as st
import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

# ---------------- API KEY ----------------
groq_api_key = os.getenv("GROQ_API_KEY")

# ---------------- STREAMLIT UI ----------------
st.title("🔥 Groq RAG Chatbot (Modern LangChain)")

# ---------------- LOAD MODEL ----------------
llm = ChatGroq(
    api_key=groq_api_key,
    model_name="llama-3.1-8b-instant"
)

# ---------------- VECTOR DB ----------------
if "vectorstore" not in st.session_state:

    # Load data
    loader = WebBaseLoader("https://docs.langchain.com/langsmith/home")
    docs = loader.load()

    # Split text
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = splitter.split_documents(docs)

    # Embeddings
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Vector DB
    st.session_state.vectorstore = FAISS.from_documents(chunks, embeddings)

# ---------------- RETRIEVER ----------------
retriever = st.session_state.vectorstore.as_retriever()

# ---------------- PROMPT ----------------
prompt = ChatPromptTemplate.from_template("""
Answer the question using only the context below.

Context:
{context}

Question:
{question}
""")

# ---------------- RAG CHAIN (MODERN STYLE) ----------------
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {
        "context": retriever | format_docs,
        "question": RunnablePassthrough()
    }
    | prompt
    | llm
)

# ---------------- INPUT ----------------
user_input = st.text_input("Ask something from the docs:")

if user_input:
    response = rag_chain.invoke(user_input)
    st.write(response.content)