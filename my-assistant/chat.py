from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama

DB_DIR = "./db"

embeddings = OllamaEmbeddings(model="gemma2:2b")
vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
llm = Ollama(model="gemma2:2b")

system_prompt = """
You are a paralegal assistant specializing in Pierce County municipal code
and Washington State law. Answer questions clearly and cite the relevant
section when possible. Always remind the user to consult a licensed attorney
for legal advice.
"""

def ask(question):
    docs = vectorstore.similarity_search(question, k=3)
    context = "\n\n".join([d.page_content for d in docs])
    prompt = f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {question}"
    return llm(prompt)

def ask_stream(question):
    docs = vectorstore.similarity_search(question, k=3)
    context = "\n\n".join([d.page_content for d in docs])
    prompt = f"{system_prompt}\n\nContext:\n{context}\n\nQuestion: {question}"
    for chunk in llm.stream(prompt):
        yield chunk