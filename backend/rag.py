import io
import pickle
import re
from pathlib import Path

import numpy as np
from pypdf import PdfReader

from google import genai
from google.genai import types
from dotenv import load_dotenv
import os


# ---------------------------------------------------------
# Gemini client
# ---------------------------------------------------------

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing.")

client = genai.Client(api_key=API_KEY)

EMBEDDING_MODEL = "gemini-embedding-2"


# ---------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------

def extract_pdf_text(pdf_bytes):
    """
    Extract text from a PDF stored in memory.
    Returns a list of page dictionaries.
    """

    reader = PdfReader(io.BytesIO(pdf_bytes))

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):

        text = page.extract_text() or ""

        text = re.sub(r"\s+", " ", text).strip()

        if text:
            pages.append(
                {
                    "page": page_number,
                    "text": text,
                }
            )

    return pages


# ---------------------------------------------------------
# Text chunking
# ---------------------------------------------------------

def chunk_text(pages, chunk_size=900, overlap=150):
    """
    Split extracted PDF text into overlapping chunks.
    Keeps page numbers for later source references.
    """

    chunks = []

    for page_data in pages:

        page_number = page_data["page"]
        text = page_data["text"]

        start = 0

        while start < len(text):

            end = start + chunk_size

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(
                    {
                        "text": chunk,
                        "page": page_number,
                    }
                )

            start += chunk_size - overlap

    return chunks


# ---------------------------------------------------------
# Create embeddings
# ---------------------------------------------------------

def create_embedding(text):
    """
    Create one embedding vector for a text chunk.
    """

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768
        ),
    )

    return np.array(
        response.embeddings[0].values,
        dtype=np.float32,
    )


def create_embeddings(chunks, batch_size=16):
    """
    Create embeddings for document chunks in batches.
    """

    if not chunks:
        return np.empty((0, 768), dtype=np.float32)

    all_embeddings = []

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]

        contents = [
            types.Content(
                parts=[
                    types.Part.from_text(
                        text=chunk["text"]
                    )
                ]
            )
            for chunk in batch
        ]

        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=contents,
            config=types.EmbedContentConfig(
                output_dimensionality=768
            ),
        )

        batch_embeddings = [
            np.array(
                embedding.values,
                dtype=np.float32
            )
            for embedding in response.embeddings
        ]

        all_embeddings.extend(batch_embeddings)

    return np.vstack(all_embeddings)


# ---------------------------------------------------------
# Similarity search
# ---------------------------------------------------------

def cosine_similarity(query_vector, document_vectors):
    """
    Calculate cosine similarity between query and document vectors.
    """

    if len(document_vectors) == 0:
        return np.array([])

    query_norm = np.linalg.norm(query_vector)

    document_norms = np.linalg.norm(
        document_vectors,
        axis=1,
    )

    if query_norm == 0:
        return np.zeros(len(document_vectors))

    denominator = (
        document_norms * query_norm
    )

    denominator = np.where(
        denominator == 0,
        1e-10,
        denominator,
    )

    return np.dot(
        document_vectors,
        query_vector,
    ) / denominator


def retrieve_chunks(
    query,
    chunks,
    embeddings,
    top_k=4,
):
    """
    Retrieve the most relevant chunks for a question.
    """

    if not chunks or embeddings.size == 0:
        return []

    query_vector = create_embedding(query)

    similarities = cosine_similarity(
        query_vector,
        embeddings,
    )

    top_indices = np.argsort(
        similarities
    )[::-1][:top_k]

    results = []

    for index in top_indices:

        results.append(
            {
                "text": chunks[index]["text"],
                "page": chunks[index]["page"],
                "source": chunks[index].get("source"),
                "score": float(similarities[index]),
            }
        )

    return results


# ---------------------------------------------------------
# Build context
# ---------------------------------------------------------

def build_context(results):
    """
    Convert retrieved chunks into context for Gemini.
    """

    if not results:
        return ""

    context_parts = []

    for result in results:
        source = result.get("source")
        location = f"{source}, page {result['page']}" if source else f"page {result['page']}"

        context_parts.append(
            f"[Source: {location}]\n"
            f"{result['text']}"
        )

    return "\n\n".join(context_parts)


# ---------------------------------------------------------
# Source information
# ---------------------------------------------------------

def format_sources(results):
    """
    Create a simple source list.
    """

    if not results:
        return ""

    seen_sources = set()
    sources = []

    for result in results:
        source = result.get("source")
        page = result["page"]
        source_key = (source, page)

        if source_key not in seen_sources:
            source_label = f"{source}, page {page}" if source else f"Page {page}"
            sources.append(f"📄 {source_label}")
            seen_sources.add(source_key)

    return " · ".join(sources)


# ---------------------------------------------------------
# Build a complete document index
# ---------------------------------------------------------

def build_document_index(pdf_bytes, source_name="Study PDF"):
    """
    Extract, chunk, and embed a PDF.
    """
    pages = extract_pdf_text(pdf_bytes)

    if not pages:
        raise ValueError(
            "No readable text was found in this PDF."
        )

    chunks = chunk_text(pages)

    if not chunks:
        raise ValueError(
            "Could not create text chunks from this PDF."
        )

    for chunk in chunks:
        chunk["source"] = source_name

    embeddings = create_embeddings(chunks)

    return {
        "pages": pages,
        "chunks": chunks,
        "embeddings": embeddings,
        "source_name": source_name,
    }


# ---------------------------------------------------------
# Retrieve from multiple uploaded documents
# ---------------------------------------------------------

def retrieve_from_documents(
    query,
    documents,
    top_k=5,
):
    """
    Search across all indexed PDFs in the current chat.
    """
    all_chunks = []
    all_embeddings = []

    for document in documents:
        index = document.get("rag_index")

        if not index:
            continue

        all_chunks.extend(index["chunks"])
        all_embeddings.append(index["embeddings"])

    if not all_chunks or not all_embeddings:
        return []

    combined_embeddings = np.vstack(
        all_embeddings
    )

    return retrieve_chunks(
        query=query,
        chunks=all_chunks,
        embeddings=combined_embeddings,
        top_k=top_k,
    )


# ---------------------------------------------------------
# Save / load cached indexes
# ---------------------------------------------------------

def save_document_index(rag_index, cache_path):
    """
    Save a generated RAG index to disk so it can be reused
    after restarting the Streamlit application.
    """
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    with cache_path.open("wb") as file:
        pickle.dump(rag_index, file)


def load_document_index(cache_path):
    """
    Load a previously saved RAG index from disk.
    Returns None if the cache does not exist or cannot be loaded.
    """
    cache_path = Path(cache_path)

    if not cache_path.exists():
        return None

    try:
        with cache_path.open("rb") as file:
            return pickle.load(file)

    except Exception:
        return None