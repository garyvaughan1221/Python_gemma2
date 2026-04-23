import os
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel

# ── Config ───────────────────────────────────────────────────────────────────
CHROMA_DIR = os.environ.get("CHROMA_DIR", "./db")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# ── Prompt ───────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """You are a helpful local legal and DIY assistant for Pierce County, WA.
Use only the context below to answer. If the answer isn't in the context, say so clearly
rather than guessing. Keep answers practical and plain-language.

Context:
{context}

Question: {question}

Answer:"""

prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=PROMPT_TEMPLATE,
)

# ── Singletons ────────────────────────────────────────────────────────────────
_embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
_vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=_embeddings)
_llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    temperature=0.2,
    max_output_tokens=1024,
)
_retriever = _vectorstore.as_retriever(search_kwargs={"k": 4})


# ── Helpers ───────────────────────────────────────────────────────────────────
def _format_docs(docs: list) -> str:
    """Concatenate retrieved chunks into a single context string."""
    return "\n\n".join(doc.page_content for doc in docs)


# ── Pipeline ──────────────────────────────────────────────────────────────────
#
#  How it works, step by step:
#
#  1. RunnableParallel runs two branches simultaneously on the input question:
#       - "context" branch: retriever fetches top-4 docs, _format_docs joins them
#       - "question" branch: RunnablePassthrough just forwards the raw question
#
#  2. The result { "context": "...", "question": "..." } is passed to the prompt
#
#  3. The filled prompt goes to the LLM
#
#  4. StrOutputParser pulls the plain text string out of the LLM response object
#
_answer_chain = (
    RunnableParallel(
        context=_retriever | _format_docs,
        question=RunnablePassthrough(),
    )
    | prompt
    | _llm
    | StrOutputParser()
)

# Separate retriever call so we can return source metadata alongside the answer
def query(question: str) -> dict:
    """
    Run a RAG query.

    Returns:
        {
            "answer": str,
            "sources": [{"source": str, "page": int}, ...]
        }
    """
    # Retrieve docs first so we have metadata for the sources list
    docs = _retriever.invoke(question)

    # Run the answer pipeline
    answer = _answer_chain.invoke(question)

    sources = []
    for doc in docs:
        meta = doc.metadata
        sources.append({
            "source": meta.get("source", "unknown"),
            "page": meta.get("page", 0),
        })

    return {
        "answer": answer,
        "sources": sources,
    }