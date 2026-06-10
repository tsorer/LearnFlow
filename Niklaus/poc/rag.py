import os
import tempfile
from dataclasses import dataclass, field

import chromadb
from llama_index.core import Settings, SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "learnflow_poc"


@dataclass
class Source:
    filename: str
    page: str
    score: float
    excerpt: str


@dataclass
class RAGResponse:
    answer: str
    sources: list[Source]
    confidence: float
    is_confident: bool
    is_partial: bool


def configure() -> None:
    api_key = os.environ["OPENAI_API_KEY"]
    Settings.llm = OpenAI(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        api_key=api_key,
    )
    Settings.embed_model = OpenAIEmbedding(
        model=os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        api_key=api_key,
    )


def _collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(COLLECTION_NAME)


def doc_count() -> int:
    try:
        return _collection().count()
    except Exception:
        return 0


def ingest(files) -> int:
    """Accept a list of Streamlit UploadedFile objects."""
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            dest = os.path.join(tmp, f.name)
            with open(dest, "wb") as out:
                out.write(f.read())
        docs = SimpleDirectoryReader(tmp, recursive=False).load_data()

    for doc in docs:
        doc.metadata.setdefault("filename", doc.metadata.get("file_name", "Unbekannt"))

    collection = _collection()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    VectorStoreIndex.from_documents(docs, storage_context=storage_context)
    return len(docs)


def ask(question: str, threshold: float = 0.6) -> RAGResponse:
    collection = _collection()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)

    nodes = index.as_retriever(similarity_top_k=5).retrieve(question)

    if not nodes:
        return RAGResponse(
            answer="Der Korpus ist leer. Bitte zuerst Dokumente hochladen.",
            sources=[], confidence=0.0, is_confident=False, is_partial=False,
        )

    top_score = nodes[0].score or 0.0

    # below 70 % of threshold → suppress completely (maps to <50 % AC)
    if top_score < threshold * 0.7:
        return RAGResponse(
            answer=(
                "Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden.\n\n"
                "_Tipp: Versuche, einen konkreten Prozess oder ein Dokument zu nennen._"
            ),
            sources=[], confidence=top_score, is_confident=False, is_partial=False,
        )

    is_partial = top_score < threshold
    context_nodes = nodes[:3]
    context = "\n\n---\n\n".join(n.node.get_content() for n in context_nodes)

    sources = [
        Source(
            filename=n.node.metadata.get("filename", n.node.metadata.get("file_name", "Unbekannt")),
            page=str(n.node.metadata.get("page_label", n.node.metadata.get("page", "?"))),
            score=round(n.score or 0.0, 3),
            excerpt=n.node.get_content()[:300],
        )
        for n in context_nodes
    ]

    prompt = f"""Du bist ein Lernassistent für neue Mitarbeitende eines Softwareunternehmens.
Beantworte die Frage ausschliesslich auf Basis der bereitgestellten Quellen.
Wenn die Quellen keine ausreichende Antwort ermöglichen, schreibe: "Ich weiss es nicht."
Antworte präzise und auf Deutsch.

Quellen:
{context}

Frage: {question}

Antwort:"""

    answer = str(Settings.llm.complete(prompt))

    return RAGResponse(
        answer=answer,
        sources=sources,
        confidence=top_score,
        is_confident=not is_partial,
        is_partial=is_partial,
    )
