import logging
from django.conf import settings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_embedding_function = None
_vector_store = None


def get_embedding_function():
    """Initializes and returns the HuggingFace embedding function."""
    global _embedding_function
    if _embedding_function is None:
        logger.info(f"Initializing embedding model: {settings.EMBEDDING_MODEL_NAME}")
        _embedding_function = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},  # Cosine similarity
        )
        logger.info("Embedding model initialized.")
    return _embedding_function


def get_vector_store():
    """Initializes and returns the Chroma vector store."""
    global _vector_store
    if _vector_store is None:
        embedding_function = get_embedding_function()
        logger.info(
            f"Initializing Chroma vector store at: {settings.CHROMA_PERSIST_DIRECTORY}"
        )
        _vector_store = Chroma(
            collection_name="dormitory_content",
            embedding_function=embedding_function,
            persist_directory=str(settings.CHROMA_PERSIST_DIRECTORY),
        )
        logger.info("Chroma vector store initialized.")
    return _vector_store


def add_document_to_vectorstore(doc_id: str, text_content: str, metadata: dict):
    """Adds a single document to the vector store."""
    try:
        vector_store = get_vector_store()
        document = Document(page_content=text_content, metadata=metadata)
        vector_store.add_documents(documents=[document], ids=[doc_id])
        logger.info(f"Document {doc_id} added to vector store.")
    except Exception as e:
        logger.error(f"Error adding document {doc_id}: {e}", exc_info=True)


def delete_document_from_vectorstore(doc_id: str):
    """Deletes a document from the vector store by its ID."""
    try:
        vector_store = get_vector_store()
        vector_store.delete(ids=[doc_id])
        logger.info(f"Document {doc_id} deleted from vector store.")
    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}", exc_info=True)


def search_vectorstore(
    query: str, k: int = 5, fetch_k: int = 10, lambda_mult: float = 0.5
):
    """
    Searches the vector store using Maximal Marginal Relevance (MMR) search.
    Returns diverse, relevant documents.

    Args:
        query (str): The search query.
        k (int): Number of documents to return (default: 5).
        fetch_k (int): Number of initial documents to fetch for MMR (default: 10).
        lambda_mult (float): MMR trade-off between relevance (1.0) and diversity (0.0, default: 0.5).

    Returns:
        List[Document]: List of relevant, diverse documents.
    """
    try:
        vector_store = get_vector_store()
        logger.info(
            f"Searching vector store with MMR for query: '{query}', k={k}, fetch_k={fetch_k}, lambda_mult={lambda_mult}"
        )

        # Perform MMR search
        results = vector_store.max_marginal_relevance_search(
            query=query, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult
        )

        logger.info(f"Found {len(results)} documents for query: '{query}'")
        return results
    except Exception as e:
        logger.error(
            f"Error searching vector store for query '{query}': {e}", exc_info=True
        )
        return []
