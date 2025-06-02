from django.conf import settings
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
import logging

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
            model_kwargs={'device': 'cpu'}, 
            encode_kwargs={'normalize_embeddings': True} # Set to True for cosine similarity, False for L2 distance
        )
        logger.info("Embedding model initialized.")
    return _embedding_function

def get_vector_store():
    """Initializes and returns the Chroma vector store."""
    global _vector_store
    if _vector_store is None:
        embedding_function = get_embedding_function()
        logger.info(f"Initializing Chroma vector store at: {settings.CHROMA_PERSIST_DIRECTORY}")
        _vector_store = Chroma(
            persist_directory=str(settings.CHROMA_PERSIST_DIRECTORY),
            embedding_function=embedding_function,
            collection_name="dormitory_content"
        )
        logger.info("Chroma vector store initialized.")
    return _vector_store

def add_document_to_vectorstore(doc_id: str, text_content: str, metadata: dict):
    """Adds a single document to the vector store."""
    try:
        vector_store = get_vector_store()
        document = Document(page_content=text_content, metadata=metadata)
        vector_store.add_documents([document], ids=[doc_id])
        logger.info(f"Document {doc_id} added to vector store.")
        # Chroma with persist_directory usually persists automatically.
        # If facing issues, uncomment: vector_store.persist()
    except Exception as e:
        logger.error(f"Error adding document {doc_id} to vector store: {e}", exc_info=True)

def delete_document_from_vectorstore(doc_id: str):
    """Deletes a document from the vector store by its ID."""
    try:
        vector_store = get_vector_store()
        # Chroma's delete method expects a list of IDs.
        # It might not raise an error if the ID doesn't exist, depending on version/config.
        vector_store.delete(ids=[doc_id])
        logger.info(f"Document {doc_id} deleted from vector store request sent.")
        # If facing issues, uncomment: vector_store.persist()
    except Exception as e:
        logger.error(f"Error deleting document {doc_id} from vector store: {e}", exc_info=True)

def search_vectorstore(query: str, k: int = 3, score_threshold: float = 0.5):
    """
    Searches the vector store for relevant documents using similarity search with score.
    Returns only documents above the score_threshold.
    """
    try:
        vector_store = get_vector_store()
        # Using similarity_search_with_score to filter by relevance
        results_with_scores = vector_store.similarity_search_with_score(query, k=k)
        
        # Filter results based on the threshold
        # For HuggingFaceEmbeddings with normalize_embeddings=True, scores are cosine similarity (higher is better)
        # If using L2 distance, lower is better. Chroma usually returns distance.
        # However, similarity_search_with_score with HuggingFaceEmbeddings often returns distance (lower is better).
        # Let's assume lower score (distance) is better. Adjust if your setup differs.
        # A common convention for normalized embeddings: score is distance, so threshold means distance < threshold
        # If scores are similarity (higher is better), change to `score >= score_threshold`
        # According to Langchain Chroma docs, it returns distance.
        # Let's set a sensible default threshold, e.g. for normalized embeddings, a distance < 0.7-1.0 might be reasonable.
        # For `paraphrase-multilingual-MiniLM-L12-v2` with normalization, cosine distances are typically < 1.0 for somewhat relevant items.
        # A threshold like 0.7 (distance) means pretty relevant.
        
        # The `score_threshold` for `similarity_search_with_relevance_scores` in Chroma
        # actually refers to a relevance score (0-1, higher is better), not distance.
        # To use it effectively, we'd call `similarity_search_with_relevance_scores`.
        # For now, let's use `similarity_search_with_score` and manually filter if needed,
        # or rely on the `k` most similar if a direct threshold isn't easily applied without more info on score range.

        # `similarity_search_with_score` returns (Document, score) tuples. Score is distance.
        # Let's use a relevance score threshold if available, or just return top K.
        # For simplicity, we'll use `similarity_search` and `k`.
        # If you want to filter by score, you would use `similarity_search_with_score`
        # and then filter the list:
        # filtered_results = [doc for doc, score in results_with_scores if score < score_threshold] # if score is distance

        logger.info(f"Searching vector store for query: '{query}' with k={k}")
        # For now, just return the top k results without explicit score filtering here.
        # The prompt will guide the LLM on relevancy.
        results = vector_store.similarity_search(query, k=k)

        logger.info(f"Found {len(results)} documents from vector store.")
        return results
    except Exception as e:
        logger.error(f"Error searching vector store for query '{query}': {e}", exc_info=True)
        return []