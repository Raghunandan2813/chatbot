from fastapi import FastAPI
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langserve import add_routes
import uvicorn
import os
from langchain_community.llms import Ollama
from dotenv import load_dotenv


load_dotenv()

os.environ['GROQ_API_KEY']=os.getenv("GROQ_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"]="true"
os.environ["LANGCHAIN_API_KEY"]=os.getenv("LANGCHAIN_API_KEY")

app=FastAPI(
    title="Langchain Server",
    version="1.0",
    description="A simple API Server"
)


add_routes(
    app, 
    ChatGroq(
        model="llama-3.1-8b-instant"),
    path="/groqai"
    
)

llm1=ChatGroq(model="llama-3.1-8b-instant",
              )

llm2=Ollama(model="llama2")


prompt1=ChatPromptTemplate.from_template("Wrtie an eassy about {topic} with 100 words")
prompt2=ChatPromptTemplate.from_template("Wrtie an eassy about {topic} with 100 words")


add_routes(
    app,
    prompt1|llm1,
    path="/essay"
)


add_routes(
    app,
    prompt2|llm2,
    path="/poem"
)



if __name__=="__main__":
    uvicorn.run(app, host="localhost", port=8000)