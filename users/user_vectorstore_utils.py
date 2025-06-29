import logging
import numpy as np
from django.conf import settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from users.models import Profile, User
import json

logger = logging.getLogger(__name__)

_user_embedding_function = None
_user_vector_store = None


def get_user_embedding_function():
    """Initializes and returns the Google Generative AI embedding function for users."""
    global _user_embedding_function
    if _user_embedding_function is None:
        logger.info("Initializing Google Generative AI embedding model for users.")
        _user_embedding_function = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=settings.EMBEDDING_API_KEY,
        )
        logger.info("Google Generative AI embedding model for users initialized.")
    return _user_embedding_function


def get_user_vector_store():
    """Initializes and returns the Chroma vector store for users."""
    global _user_vector_store
    if _user_vector_store is None:
        embedding_function = get_user_embedding_function()
        logger.info(
            f"Initializing Chroma user vector store at: {settings.CHROMA_USER_PERSIST_DIRECTORY}"
        )
        _user_vector_store = Chroma(
            collection_name="user_profiles",
            embedding_function=embedding_function,
            persist_directory=str(settings.CHROMA_USER_PERSIST_DIRECTORY),
        )
        logger.info("Chroma user vector store initialized.")
    return _user_vector_store


def add_or_update_user_embedding(user, embedding):
    """Adds or updates a user's embedding in the vector store."""
    vector_store = get_user_vector_store()
    doc_id = f"user_{user.id}"

    # Check if the document already exists
    existing_doc = vector_store.get(ids=[doc_id])

    metadata = {
        "user_id": user.id,
        "username": user.username,
    }

    if existing_doc and existing_doc.get("ids"):
        # Update existing document
        vector_store.update_document(
            document_id=doc_id, document=Document(page_content="", metadata=metadata)
        )
        logger.info(f"Updated user embedding for user {user.id}")
    else:
        # Add new document
        vector_store.add_documents(
            documents=[Document(page_content="", metadata=metadata)],
            ids=[doc_id],
            embeddings=[embedding],
        )
        logger.info(f"Added new user embedding for user {user.id}")


def get_user_embedding(user):
    """Retrieves a user's embedding from the vector store."""
    vector_store = get_user_vector_store()
    doc_id = f"user_{user.id}"
    result = vector_store.get(ids=[doc_id], include=["embeddings"])

    # Explicitly check for None and non-empty list
    if result is not None and "embeddings" in result and len(result["embeddings"]) > 0:
        return result["embeddings"][0]
    return None


def find_similar_users(user, k=5):
    """Finds k most similar users to the given user."""
    user_embedding = get_user_embedding(user)

    # FIX: use explicit None check instead of boolean context
    if user_embedding is None:
        logger.warning(
            f"No embedding found for user {user.id}. Cannot find similar users."
        )
        return []

    vector_store = get_user_vector_store()

    try:
        results = vector_store.similarity_search_by_vector(
            embedding=user_embedding,
            k=k + 1,  # Fetch k+1 to exclude the user themselves
        )
    except Exception as e:
        logger.error(
            f"Error during similarity search for user {user.id}: {e}", exc_info=True
        )
        return []

    # print(results)
    similar_users = []
    for doc in results:
        try:
            metadata = doc.metadata
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            user_id = metadata.get("user_id")

            if user_id is not None and user_id != user.id:
                try:
                    similar_user = User.objects.get(id=user_id)
                    similar_users.append(similar_user)
                except User.DoesNotExist:
                    logger.warning(
                        f"User with ID {user_id} found in vector store but not in database."
                    )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(
                f"Error processing document metadata: {doc.metadata}. Error: {e}",
                exc_info=True,
            )

    # print(similar_users)
    return similar_users[:k]
