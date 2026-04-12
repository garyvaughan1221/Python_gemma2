from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM

embeddings = OllamaEmbeddings(model="gemma2:2b")
vectorstore = Chroma(persist_directory="./db", embedding_function=embeddings)
llm = OllamaLLM(model="gemma2:2b")

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
    return llm.invoke(prompt)

if __name__ == "__main__":
    print(ask("What are the rules for ADUs in Pierce County?"))