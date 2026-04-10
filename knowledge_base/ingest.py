"""One-time script to ingest the AutoStream knowledge base into Chroma."""

import os
import sys

# Allow running from project root or knowledge_base/ directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

KB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autostream_kb.md")
CHROMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db"
)


def ingest() -> None:
    print(f"Loading knowledge base from: {KB_PATH}")
    loader = TextLoader(KB_PATH, encoding="utf-8")
    raw_docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
    )
    split_docs = splitter.split_documents(raw_docs)
    print(f"Split into {len(split_docs)} chunks")

    print("Loading embedding model (all-MiniLM-L6-v2) — first run downloads ~90 MB...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print(f"Creating Chroma vector store at: {CHROMA_PATH}")
    Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings,
        persist_directory=CHROMA_PATH,
    )
    print(f"Ingestion complete. {len(split_docs)} chunks stored in {CHROMA_PATH}")


if __name__ == "__main__":
    ingest()
