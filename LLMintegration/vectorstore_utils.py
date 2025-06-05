## ADDED CHUNKING
"""
What it does:
0. Initializes the HuggingFace embedding model and Chroma vector store once.
1. Get the tokenizer from the embedding model's client (if available), or fallback to AutoTokenizer, or fallback to character-based splitting without any tokenizer.
2. Split the text content into chunks using Recursive Splitter based on the tokenizer/character length.
3. Add each chunk to the vector store with metadata linking it to the original document ID (i.e. post_32) and chunk index (2 meaning 3rd chunk). To uniquely identify chunks in the ChromaDB, we combine them. (e.g., post_32_chunk_2).
4. Implemented a delete function that removes ALL chunks associated with a given original document ID (i.e. post_32).
5. Implemented a search function that retrieves chunks based on a query with all metadata intact, allowing you to trace back to the original document and chunk index/sequence.
"""

import logging
from django.conf import settings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer  # For token-based splitting

logger = logging.getLogger(__name__)

_embedding_function = None
_vector_store = None

# --- Configuration for Chunking ---

MAX_TOKENS = 128
FALLBACK_CHUNK_SIZE_CHARS = 384  # if 1 token ~ 3-4 chars, 128 tokens ~ 384-512 chars.
FALLBACK_CHUNK_OVERLAP_CHARS = max(
    0, FALLBACK_CHUNK_SIZE_CHARS // 5
)  # e.g., ~20% overlap, ensure non-negative # characters
# Metadata keys for linking chunks to original documents
ORIGINAL_DOC_ID_KEY = "original_doc_id"
CHUNK_INDEX_KEY = "chunk_index"


def get_embedding_function():
    """Initializes and returns the HuggingFace embedding function."""
    global _embedding_function  # it is GLOBAL. meaning it is shared across all calls to this function. It will be initialized only once (upon the first call) and reused in subsequent calls
    # Using `global _embedding_function` inside a function tells Python that when you assign to `_embedding_function`, you’re referring to the module-level variable of that name rather than creating a new local. It doesn’t automatically create the variable—you still need to define it at module scope—but it lets you update that shared global from within the function.
    if _embedding_function is None:  # if it is not initialized yet
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
            collection_name="dormitory_content",  # Consider making this configurable via settings
            embedding_function=embedding_function,
            persist_directory=str(settings.CHROMA_PERSIST_DIRECTORY),
        )
        logger.info("Chroma vector store initialized.")
    return _vector_store


def _get_text_splitter():
    """
    Initializes and returns a text splitter, preferring token-based splitting (first tries to get tokenizer from embedding model's client, then falls back to AutoTokenizer).
    Falls back to character-based splitting if token-based setup fails.
    """
    embedding_fn = (
        get_embedding_function()
    )  # Ensures embedding_function is initialized before using it

    # Attempt to use the tokenizer from the loaded SentenceTransformer model
    # embedding_fn.client may not exist; safely retrieve it
    tokenizer_source = getattr(embedding_fn, "client", None)
    hf_tokenizer = (
        getattr(tokenizer_source, "tokenizer", None) if tokenizer_source else None
    )

    if hf_tokenizer:
        try:
            text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
                tokenizer=hf_tokenizer,
                chunk_size=MAX_TOKENS,
                chunk_overlap=FALLBACK_CHUNK_OVERLAP_CHARS,
            )
            logger.info(
                f"Using tokenizer from loaded embedding model for chunking. Max tokens per chunk: {MAX_TOKENS}"
            )
            return text_splitter  # successfully returned
        except Exception as e:
            logger.warning(
                f"Failed to initialize RecursiveCharacterTextSplitter with model's tokenizer: {e}. Trying AutoTokenizer."
            )

    # Fallback: Try to load tokenizer using AutoTokenizer
    try:
        logger.info(
            f"Attempting to load tokenizer with AutoTokenizer for model: {settings.EMBEDDING_MODEL_NAME}"
        )
        tokenizer_fallback = AutoTokenizer.from_pretrained(
            settings.EMBEDDING_MODEL_NAME
        )
        text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
            tokenizer=tokenizer_fallback,
            chunk_size=MAX_TOKENS,
            chunk_overlap=FALLBACK_CHUNK_OVERLAP_CHARS,
        )
        logger.info(
            f"Using AutoTokenizer-loaded tokenizer for chunking. Max tokens per chunk: {MAX_TOKENS}"
        )
        return text_splitter
    except Exception as tokenizer_ex:
        logger.warning(
            f"Failed to initialize HuggingFace tokenizer via AutoTokenizer: {tokenizer_ex}. "
            f"Falling back to character-based splitting."
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=FALLBACK_CHUNK_SIZE_CHARS,
            chunk_overlap=FALLBACK_CHUNK_OVERLAP_CHARS,
            length_function=len,  # python's built-in len function. it will be used to calculate the length of the text chunks
            is_separator_regex=False,
        )
        logger.info(
            f"Using character-based splitting. Chunk size: {FALLBACK_CHUNK_SIZE_CHARS} chars, "
            f"Overlap: {FALLBACK_CHUNK_OVERLAP_CHARS} chars."
        )
        return text_splitter


def add_document_to_vectorstore(
    original_doc_id: str, text_content: str, metadata: dict
):  # like post_32, text_content, metadata dict containing source_type, document_id, author_username, created_at, url
    """
    Splits a document into chunks and adds them to the vector store.
    Each chunk is associated with the original document ID and includes original metadata.
    """
    try:
        if not text_content or not text_content.strip():
            logger.warning(
                f"Text content for document {original_doc_id} is empty or whitespace only. Skipping."
            )
            return

        vector_store = get_vector_store()
        text_splitter = _get_text_splitter()

        text_chunks = text_splitter.split_text(text_content)

        if not text_chunks:
            logger.warning(
                f"No text chunks generated for document {original_doc_id} (original_doc_id). Content might be too short after splitting attempt."
            )
            return

        documents_to_add = []
        chunk_ids_for_db = []

        for i, chunk_text in enumerate(text_chunks):
            # Create a unique ID for each chunk to store in Chroma
            chunk_db_id = f"{original_doc_id}_chunk_{i}"

            # Combine original metadata with chunk-specific metadata
            chunk_metadata = {
                **metadata,  # Original metadata passed to the function
                ORIGINAL_DOC_ID_KEY: original_doc_id,  # Link to the parent document # this will be used to trace back to the original document, and while deleting
                CHUNK_INDEX_KEY: i,  # Sequence of the chunk
            }

            doc = Document(page_content=chunk_text, metadata=chunk_metadata)
            documents_to_add.append(doc)
            chunk_ids_for_db.append(chunk_db_id)

        if documents_to_add:
            vector_store.add_documents(documents=documents_to_add, ids=chunk_ids_for_db)
            logger.info(
                f"{len(documents_to_add)} chunks for document {original_doc_id} added to vector store."
            )
        else:
            # This case should ideally be caught by 'if not text_chunks' earlier
            logger.info(
                f"No document chunks to add for {original_doc_id} after processing."
            )

    except Exception as e:
        logger.error(
            f"Error adding document {original_doc_id} (chunked): {e}", exc_info=True
        )


def delete_document_from_vectorstore(original_doc_id: str):
    """
    Deletes all chunks associated with the given original document ID from the vector store.
    """
    try:
        vector_store = get_vector_store()

        # Chroma's delete method can use a 'where' filter based on metadata.
        # This will delete all chunks that have 'original_doc_id' set to the provided ID.
        filter_criteria = {ORIGINAL_DOC_ID_KEY: original_doc_id}

        # The Langchain Chroma wrapper passes `where` to the underlying Chroma client's delete method.
        vector_store.delete(where=filter_criteria)

        logger.info(
            f"Attempted deletion of all chunks for document {original_doc_id} (matching filter {filter_criteria}) from vector store."
        )

    except Exception as e:
        # Log error, but don't necessarily re-raise if, e.g., the document wasn't there.
        # Chroma's delete with a `where` clause typically doesn't error if no documents match.
        logger.error(
            f"Error deleting document chunks for {original_doc_id}: {e}", exc_info=True
        )


def search_vectorstore(
    query: str, k: int = 5, fetch_k: int = 10, lambda_mult: float = 0.5
):  # k means how many chunks to return, fetch_k is how many chunks to fetch before MMR filtering, lambda_mult is the trade-off between relevance and diversity (1.0 means only relevance, 0.0 means only diversity, default is 0.5 which balances both)
    """
    Searches the vector store using Maximal Marginal Relevance (MMR) search.
    Returns diverse, relevant document chunks.
    The metadata of each chunk contains ORIGINAL_DOC_ID_KEY and CHUNK_INDEX_KEY
    to link back to the original post/comment.
    """
    try:
        vector_store = get_vector_store()
        logger.info(
            f"Searching vector store with MMR for query: '{query}', k={k}, fetch_k={fetch_k}, lambda_mult={lambda_mult}"
        )

        # Perform MMR search. Results will be Document objects representing chunks.
        results = vector_store.max_marginal_relevance_search(
            query=query, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult
        )

        logger.info(
            f"Found {len(results)} document chunks for query, they are: '{results}'"
        )
        # Example of accessing original document ID from a retrieved chunk:
        # if results:
        #     first_chunk = results[0]
        #     original_id = first_chunk.metadata.get(ORIGINAL_DOC_ID_KEY)
        #     chunk_idx = first_chunk.metadata.get(CHUNK_INDEX_KEY)
        #     logger.debug(f"First retrieved chunk belongs to original doc '{original_id}', chunk index {chunk_idx}")
        return results
    except Exception as e:
        logger.error(
            f"Error searching vector store for query '{query}': {e}", exc_info=True
        )
        return []


'''
Old code without chunking, for reference:
# import logging

# from django.conf import settings
# from langchain_chroma import Chroma
# from langchain_core.documents import Document
# from langchain_huggingface import HuggingFaceEmbeddings

# logger = logging.getLogger(__name__)

# _embedding_function = None
# _vector_store = None


# def get_embedding_function():
#     """Initializes and returns the HuggingFace embedding function."""
#     global _embedding_function
#     if _embedding_function is None:
#         logger.info(f"Initializing embedding model: {settings.EMBEDDING_MODEL_NAME}")
#         _embedding_function = HuggingFaceEmbeddings(
#             model_name=settings.EMBEDDING_MODEL_NAME,
#             model_kwargs={"device": "cpu"},
#             encode_kwargs={"normalize_embeddings": True},  # Cosine similarity
#         )
#         logger.info("Embedding model initialized.")
#     return _embedding_function


# def get_vector_store():
#     """Initializes and returns the Chroma vector store."""
#     global _vector_store
#     if _vector_store is None:
#         embedding_function = get_embedding_function()
#         logger.info(
#             f"Initializing Chroma vector store at: {settings.CHROMA_PERSIST_DIRECTORY}"
#         )
#         _vector_store = Chroma(
#             collection_name="dormitory_content",
#             embedding_function=embedding_function,
#             persist_directory=str(settings.CHROMA_PERSIST_DIRECTORY),
#         )
#         logger.info("Chroma vector store initialized.")
#     return _vector_store


# def add_document_to_vectorstore(doc_id: str, text_content: str, metadata: dict):
#     """Adds a single document to the vector store."""
#     try:
#         vector_store = get_vector_store()
#         document = Document(page_content=text_content, metadata=metadata)
#         vector_store.add_documents(documents=[document], ids=[doc_id])
#         logger.info(f"Document {doc_id} added to vector store.")
#     except Exception as e:
#         logger.error(f"Error adding document {doc_id}: {e}", exc_info=True)


# def delete_document_from_vectorstore(doc_id: str):
#     """Deletes a document from the vector store by its ID."""
#     try:
#         vector_store = get_vector_store()
#         vector_store.delete(ids=[doc_id])
#         logger.info(f"Document {doc_id} deleted from vector store.")
#     except Exception as e:
#         logger.error(f"Error deleting document {doc_id}: {e}", exc_info=True)


# def search_vectorstore(
#     query: str, k: int = 5, fetch_k: int = 10, lambda_mult: float = 0.5
# ):
#     """
#     Searches the vector store using Maximal Marginal Relevance (MMR) search.
#     Returns diverse, relevant documents.

#     Args:
#         query (str): The search query.
#         k (int): Number of documents to return (default: 5).
#         fetch_k (int): Number of initial documents to fetch for MMR (default: 10).
#         lambda_mult (float): MMR trade-off between relevance (1.0) and diversity (0.0, default: 0.5).

#     Returns:
#         List[Document]: List of relevant, diverse documents.
#     """
#     try:
#         vector_store = get_vector_store()
#         logger.info(
#             f"Searching vector store with MMR for query: '{query}', k={k}, fetch_k={fetch_k}, lambda_mult={lambda_mult}"
#         )

#         # Perform MMR search
#         results = vector_store.max_marginal_relevance_search(
#             query=query, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult
#         )

#         logger.info(f"Found {len(results)} documents for query: '{query}'")
#         return results
#     except Exception as e:
#         logger.error(
#             f"Error searching vector store for query '{query}': {e}", exc_info=True
#         )
#         return []
# '''
