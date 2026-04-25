from dotenv import load_dotenv
load_dotenv()

import os
from supabase import create_client
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

# ── Config ───────────────────────────────────────────────────────────────────
GEMINI_MODEL  = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
MATCH_COUNT   = int(os.environ.get("MATCH_COUNT", "4"))

# ── Clients ───────────────────────────────────────────────────────────────────
_supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"],
)

_embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

_llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    temperature=0.2,
    max_output_tokens=1024,
)

# ── Prompt ───────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """You are a helpful local legal and DIY assistant for Pierce County, WA.
Use only the context below to answer. If the answer isn't in the context, say so clearly
rather than guessing. Keep answers practical and plain-language.

If the context contains URLs relevant to the answer, include them at the end of your
response under a "Sources:" section. Only include URLs that actually appear in the context —
do not invent or guess at links.

Context:
{context}

Question: {question}

Answer:"""

_prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=PROMPT_TEMPLATE,
)

_chain = _prompt | _llm | StrOutputParser()


# ── Retrieval (direct RPC — no SupabaseVectorStore) ──────────────────────────
def _retrieve(question: str) -> list[Document]:
    """
    Embed the question and call the match_documents RPC directly.
    Returns a list of LangChain Document objects.
    """
    vector = _embeddings.embed_query(question)

    response = (
        _supabase
        .rpc("match_documents", {
            "query_embedding": vector,
            "match_count": MATCH_COUNT,
            "filter": {},
        })
        .execute()
    )

    docs = []
    for row in response.data or []:
        docs.append(Document(
            page_content=row["content"],
            metadata=row.get("metadata", {}),
        ))
    return docs


# ── Query ─────────────────────────────────────────────────────────────────────
def query(question: str) -> dict:
    """
    Run a RAG query against Supabase.

    Returns:
        {
            "answer": str,
            "sources": [{"source": str, "page": int}, ...]
        }
    """
    docs = _retrieve(question)

    context = "\n\n".join(doc.page_content for doc in docs)

    answer = _chain.invoke({
        "context": context,
        "question": question,
    })

    sources = []
    for doc in docs:
        meta = doc.metadata
        sources.append({
            "source": meta.get("source", "unknown"),
            "page":   meta.get("page", 0),
        })

    return {
        "answer": answer,
        "sources": sources,
    }