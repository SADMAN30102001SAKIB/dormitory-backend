import json
import logging

import numpy as np
from django.contrib.auth.models import User

from LLMintegration.vectorstore_utils import get_embedding_function
from posts.models import Comment, Post, PostLike, Reply
from users.user_vectorstore_utils import (
    add_or_update_user_embedding,
    get_user_embedding as get_user_embedding_from_store,
)

logger = logging.getLogger(__name__)

# --- Alpha values for Exponentially Weighted Moving Average ---
# Higher alpha = more weight on the new interaction.
INTERACTION_ALPHAS = {
    "created_post": 0.25,
    "comment_or_reply": 0.15,
    "liked_post": 0.10,
}


# this function is used from signals.py
def _get_item_embedding(item_instance):
    """
    1. `_get_item_embedding(item_instance)`
    - Purpose: Produce a single “semantic” vector for one Django model object (Post, Comment, or Reply).
    - How it works:
        • Formats the instance's text (title/body) into one string.
        • Calls your embedding API (`embed_query`) once.
        • Wraps that result as a NumPy array and returns it.
    2. `add_document_to_vectorstore(doc_id, text_content, metadata)` from vectorstore_utils.py
    - Purpose: Add a single document (text + metadata) to your Chroma vector database for later retrieval.
    - How it works:
        • Splits the full text into smaller chunks (token- or character-based).
        • For each chunk, calls the same embedding API under the hood.
        • Stores each chunk's embedding (and its metadata + chunk ID) in your persistent Chroma collection.
    """
    embedding_fn = get_embedding_function()
    content_to_embed = ""

    if isinstance(item_instance, Post):
        content_to_embed = (
            f"Post Title: {item_instance.title}\nPost Content: {item_instance.content}"
        )
    elif isinstance(item_instance, Comment):
        content_to_embed = (
            f"Comment on post titled '{item_instance.post.title}': {item_instance.body}"
        )
    elif isinstance(item_instance, Reply):
        content_to_embed = f"Reply to a comment on post titled '{item_instance.comment.post.title}': {item_instance.body}"

    if not content_to_embed:
        return None

    return np.array(embedding_fn.embed_query(content_to_embed))


def calculate_initial_interest_vector(user: User):
    """Calculates the initial interest vector for a new user based on their selected interest tags."""
    profile = getattr(user, "profile", None)
    if not profile:
        return None

    interest_tags = profile.interests.all()
    if not interest_tags.exists():
        return None

    embedding_fn = get_embedding_function()
    tag_embeddings = [embedding_fn.embed_query(tag.name) for tag in interest_tags]

    if not tag_embeddings:
        return None

    initial_vector = np.mean(tag_embeddings, axis=0)
    logger.info(f"Calculated initial interest vector for user {user.username}.")
    return initial_vector


def get_user_interest_vector(user: User):
    """
    Retrieves the user's interest vector from the vector store.
    If it doesn't exist, it calculates the initial one from their interest tags.
    """
    embedding = get_user_embedding_from_store(user)
    if embedding is not None:
        return np.array(embedding)

    # If no embedding exists, calculate the initial one and save it
    initial_vector = calculate_initial_interest_vector(user)
    if initial_vector is not None:
        add_or_update_user_embedding(user, initial_vector.tolist())
        logger.info(f"Saved initial interest vector for {user.username}.")
        return initial_vector

    return None


def incrementally_update_interest_vector(
    user: User, interaction_embedding: np.ndarray, interaction_type: str
):
    """
    Updates the user's interest vector incrementally using an EWMA.

    Args:
        user (User): The user whose profile is to be updated.
        interaction_embedding (np.ndarray): The embedding of the item interacted with.
        interaction_type (str): The type of interaction (e.g., 'created_post').
    """
    alpha = INTERACTION_ALPHAS.get(interaction_type)
    if not alpha:
        logger.warning(f"Invalid interaction_type '{interaction_type}'.")
        return

    # Get the user's current interest vector
    old_vector = get_user_interest_vector(user)

    if old_vector is None:
        # If the user has no vector yet, the new interaction becomes their vector
        new_vector = interaction_embedding
        logger.info(
            f"User {user.username} has no prior vector. Initializing with new interaction."
        )
    else:
        # Apply the EWMA formula
        new_vector = (alpha * interaction_embedding) + ((1 - alpha) * old_vector)

    # Normalize the final vector to maintain a consistent magnitude (unit vector)
    norm = np.linalg.norm(new_vector)
    if norm > 0:
        new_vector /= norm

    # Save the updated vector to the vector store
    add_or_update_user_embedding(user, new_vector.tolist())
    logger.info(
        f"Incrementally updated interest vector for {user.username} via {interaction_type}."
    )


"""
Old version of the code, kept for reference. The old version used to calculate the interest vector based on all interactions at once, which was less efficient and could lead to performance issues for users with many interactions.
Also it didn't use EWMA, which is more suitable for real-time updates. It would just average all embeddings without considering the recency of interactions.
Now it can be used to recalculate the interest vector from scratch if needed.
"""
# # --- Interaction Weights ---
# WEIGHTS = {
#     "created_post": 3.0,
#     "liked_post": 1.0,
#     "comment_or_reply": 2.0,
# }


# def update_user_interest_vector(user: User):
#     """
#     Calculates and saves the user's interest vector based on a weighted average
#     of their interactions (posts, likes, comments, replies).
#     """
#     logger.info(f"Starting interest vector update for user: {user.username}")
#     embeddings = []
#     weights = []

#     # 1. Posts created by the user (Weight = 3)
#     user_posts = Post.objects.filter(author=user).iterator()
#     for post in user_posts:
#         embedding = _get_item_embedding(post)
#         if embedding:
#             embeddings.append(embedding)
#             weights.append(WEIGHTS["created_post"])

#     # 2. Posts liked by the user (Weight = 1)
#     user_likes = PostLike.objects.filter(user=user).select_related("post").iterator()
#     for like in user_likes:
#         embedding = _get_item_embedding(like.post)
#         if embedding:
#             embeddings.append(embedding)
#             weights.append(WEIGHTS["liked_post"])

#     # 3. Comments and Replies by the user (Weight = 2)
#     user_comments = (
#         Comment.objects.filter(author=user).select_related("post").iterator()
#     )
#     for comment in user_comments:
#         embedding = _get_item_embedding(comment)
#         if embedding:
#             embeddings.append(embedding)
#             weights.append(WEIGHTS["comment_or_reply"])

#     user_replies = (
#         Reply.objects.filter(author=user).select_related("comment__post").iterator()
#     )
#     for reply in user_replies:
#         embedding = _get_item_embedding(reply)
#         if embedding:
#             embeddings.append(embedding)
#             weights.append(WEIGHTS["comment_or_reply"])

#     profile = getattr(user, "profile", None)
#     if not profile:
#         logger.error(
#             f"Profile not found for user {user.username}. Cannot save embedding."
#         )
#         return

#     if embeddings and weights:
#         # Calculate the weighted average vector
#         interest_vector = np.average(embeddings, axis=0, weights=weights)
#         # Normalize the final vector to ensure consistent magnitude
#         interest_vector /= np.linalg.norm(interest_vector)
#         logger.info(
#             f"Successfully calculated new interest vector for {user.username} from {len(embeddings)} interactions."
#         )
#     else:
#         # Fallback for users with no interactions: use initial interest tags
#         logger.info(
#             f"No interactions found for {user.username}. Falling back to initial interest tags."
#         )
#         interest_vector = calculate_initial_interest_vector(user)

#     if interest_vector is not None:
#         # Serialize numpy array to a JSON string for storing in TextField
#         profile.users_embedding = json.dumps(interest_vector.tolist())
#         profile.save(update_fields=["users_embedding"])
#         logger.info(f"Saved updated interest vector for user: {user.username}")
#     else:
#         logger.warning(
#             f"Could not compute or save interest vector for {user.username}."
#         )


# def full_recalculate_get_user_interest_vector(user: User, recalculate: bool = False):
#     """
#     Retrieves the user's interest vector. If it doesn't exist or `recalculate` is True,
#     it computes and saves it first.
#     """
#     profile = getattr(user, "profile", None)
#     if not profile:
#         return None

#     if not profile.users_embedding or recalculate:
#         update_user_interest_vector(user)
#         # Refresh profile from db to get the new embedding
#         profile.refresh_from_db()

#     if profile.users_embedding:
#         # Deserialize the JSON string back into a numpy array
#         return np.array(json.loads(profile.users_embedding))

#     return None
