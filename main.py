import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

app = FastAPI()

# --- CONFIGURATION ---
FOLDERS = ["./SMT", "./WAVE"]
DB_DIR = "./smt_expert_db"
MODEL_NAME = "llama3.2-vision"
EMBED_MODEL = "mxbai-embed-large"

# Initialize global variable for the chain
rag_chain = None

class QueryRequest(BaseModel):
    input: str

@app.on_event("startup")
async def startup_event():
    global rag_chain
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    
    # Check for DB
    if os.path.exists(DB_DIR) and os.listdir(DB_DIR):
        vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    else:
        # Load and Index if missing
        all_docs = []
        for folder in FOLDERS:
            if os.path.exists(folder):
                loader = DirectoryLoader(folder, glob="**/*.md", loader_cls=UnstructuredMarkdownLoader)
                all_docs.extend(loader.load())
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(all_docs)
        vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=DB_DIR)

    llm = ChatOllama(model=MODEL_NAME, temperature=0)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    system_prompt = (
        "You are an expert SMT and Wave Soldering technician. "
        "Use the provided documentation to troubleshoot defects. \n\n {context}"
    )
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    print("🚀 Backend Engine Ready!")

@app.post("/stream")
async def stream_chat(request: QueryRequest):
    def generate():
        for chunk in rag_chain.stream({"input": request.input}):
            if "answer" in chunk:
                yield chunk["answer"]
    return StreamingResponse(generate(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)