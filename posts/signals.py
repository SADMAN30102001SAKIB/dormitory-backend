"""
Whenever a Post or Comment is created, edited or deleted, this module handles the embedding of the content as well as updates the users embedding vector.

Explanation how signals work:
Example:
@receiver(post_save, sender=Post) # receiver decorator connects the function to the post_save signal for the Post model
def embed_post_on_save(sender, instance, created, **kwargs):

@receiver(post_save, sender=Post):
This is a Django decorator that connects a function to a specific signal.

post_save: This is a built-in Django signal from django.db.models.signals. It is emitted automatically every whenever a model instance is saved (e.g., created or updated) via Django's ORM (Object-Relational Mapping). IT IS NOT the Post model of ours or HTTP POST request, but rather a signal with keyword as "post_save" that indicates a save operation has occurred.

sender=Post: This specifies that the signal should only trigger this function when the sender is the Post model (from your .models module). In other words, this function only responds to save events for Post instances, not other models like Comment.

@receiver: This decorator, from django.dispatch, registers the function below it (in this case, embed_post_on_save) to "listen" for the post_save signal. When the signal fires, the connected function is called with specific arguments.

def embed_post_on_save(sender, instance, created, **kwargs):
This defines the function that handles the signal. All the 4 arguments are must to write as parameter and passed automatically by Django when the signal is triggered.

Parameters:
sender: The model class that sent the signal (in this case, Post). This lets the function know which model triggered the event.

instance: The actual instance of the Post model that was just saved. This gives access to the post's attributes, like instance.title, instance.content, or instance.author.

created: A boolean indicating whether this save operation created a new Post (True) or updated an existing one (False).

**kwargs: A catch-all for additional keyword arguments passed by the signal. This might include extra context, though it's often unused in simple cases.

Purpose: This function is designed to embed the post's content into a vector store (ChromaDB) after it's saved. It constructs a doc_id (e.g., post_123), combines the post's title and content (and a note about any image), and passes this along with metadata (e.g., author, creation date) to add_document_to_vectorstore for embedding.


"""

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from LLMintegration.vectorstore_utils import (
    add_document_to_vectorstore,
    delete_document_from_vectorstore,
)

from .models import Comment, Post, Reply, PostLike
from users.interest_modeling import (
    incrementally_update_interest_vector,
    _get_item_embedding,
)


logger = logging.getLogger(__name__)


# --- Post Signals ---
@receiver(post_save, sender=Post)
def post_save_handler(sender, instance, created, **kwargs):
    """Handles embedding the post and updating the author's interest vector."""
    # 1. Embed and add the post to the vector store
    doc_id = f"post_{instance.id}"
    content_to_embed = f"Post Title: {instance.title}\nPost Content: {instance.content}"
    metadata = {
        "source_type": "post",
        "document_id": str(instance.id),
        "title": instance.title,
        "author_username": instance.author.username,
        "created_at": instance.created_at.date().isoformat(),
        "url": f"/posts/{instance.id}/",
    }
    add_document_to_vectorstore(doc_id, content_to_embed, metadata)

    # 2. If a new post is created, update the user's interest vector
    if created:
        embedding = _get_item_embedding(instance)
        if embedding is not None:
            incrementally_update_interest_vector(
                instance.author, embedding, "created_post"
            )


@receiver(post_delete, sender=Post)
def delete_post_from_vectorstore(sender, instance, **kwargs):
    """Deletes post from ChromaDB when a post is deleted."""
    try:
        logger.info(f"Signal received: post_delete for Post ID {instance.id}")
        doc_id = f"post_{instance.id}"
        delete_document_from_vectorstore(doc_id)
    except Exception as e:
        logger.error(
            f"Error in delete_post_from_vectorstore signal for Post ID {instance.id}: {e}",
            exc_info=True,
        )


# --- PostLike Signal ---
@receiver(post_save, sender=PostLike)
def post_like_save_handler(sender, instance, created, **kwargs):
    """Updates the user's interest vector when they like a post."""
    if created:
        embedding = _get_item_embedding(instance.post)
        if embedding is not None:
            incrementally_update_interest_vector(instance.user, embedding, "liked_post")


# --- Comment Signals ---
@receiver(post_save, sender=Comment)
def comment_save_handler(sender, instance, created, **kwargs):
    """Handles embedding the comment and updating the author's interest vector."""
    doc_id = f"comment_{instance.id}"
    content_to_embed = (
        f"Comment on post titled '{instance.post.title}': {instance.body}"
    )
    metadata = {
        "source_type": "comment",
        "document_id": str(instance.id),
        "post_id": str(instance.post.id),
        "post_title": instance.post.title,
        "author_username": instance.author.username,
        "created_at": instance.created_at.isoformat(),
        "url": f"/posts/{instance.post.id}/comment/{instance.id}",
    }
    add_document_to_vectorstore(doc_id, content_to_embed, metadata)

    if created:
        embedding = _get_item_embedding(instance)
        if embedding is not None:
            incrementally_update_interest_vector(
                instance.author, embedding, "comment_or_reply"
            )


@receiver(post_delete, sender=Comment)
def delete_comment_from_vectorstore(sender, instance, **kwargs):
    """Deletes comment from ChromaDB when a comment is deleted."""
    try:
        logger.info(f"Signal received: post_delete for Comment ID {instance.id}")
        doc_id = f"comment_{instance.id}"
        delete_document_from_vectorstore(doc_id)
    except Exception as e:
        logger.error(
            f"Error in delete_comment_from_vectorstore for Comment ID {instance.id}: {e}",
            exc_info=True,
        )


# --- Reply Signals ---
@receiver(post_save, sender=Reply)
def reply_save_handler(sender, instance, created, **kwargs):
    """Handles embedding the reply and updating the author's interest vector."""
    doc_id = f"reply_{instance.id}"
    content_to_embed = f"Reply to a comment on post titled '{instance.comment.post.title}': {instance.body}"
    metadata = {
        "source_type": "reply",
        "document_id": str(instance.id),
        "comment_id": str(instance.comment.id),
        "post_id": str(instance.comment.post.id),
        "author_username": instance.author.username,
        "created_at": instance.created_at.isoformat(),
        "url": f"/posts/{instance.comment.post.id}/comment/{instance.comment.id}",
    }
    add_document_to_vectorstore(doc_id, content_to_embed, metadata)

    if created:
        embedding = _get_item_embedding(instance)
        if embedding is not None:
            incrementally_update_interest_vector(
                instance.author, embedding, "comment_or_reply"
            )


@receiver(post_delete, sender=Reply)
def delete_reply_from_vectorstore(sender, instance, **kwargs):
    """Deletes reply from ChromaDB when a reply is deleted."""
    try:
        logger.info(f"Signal received: post_delete for Reply ID {instance.id}")
        doc_id = f"reply_{instance.id}"
        delete_document_from_vectorstore(doc_id)
    except Exception as e:
        logger.error(
            f"Error in delete_reply_from_vectorstore for Reply ID {instance.id}: {e}",
            exc_info=True,
        )


"""
Older versions: used to embed contents on save. Didn't updated interest vector. 
"""
# @receiver(post_save, sender=Post)
# def embed_post_on_save(sender, instance, created, **kwargs):
#     """Embeds post content and stores it in ChromaDB when a post is saved."""
#     try:
#         logger.info(f"Signal received: post_save for Post ID {instance.id}")
#         doc_id = f"post_{instance.id}"

#         # Combine title and content for richer embeddings
#         content_to_embed = (
#             f"Post Title: {instance.title}\nPost Content: {instance.content}"
#         )
#         if instance.image:  # Optionally include a note about an image
#             content_to_embed += "\n(Note: This post includes an image.)"

#         metadata = {
#             "source_type": "post",
#             "document_id": str(instance.id),
#             "title": instance.title,
#             "author_username": instance.author.username,
#             "created_at": instance.created_at.date().isoformat(),
#             "url": f"/posts/{instance.id}/",
#         }

#         add_document_to_vectorstore(doc_id, content_to_embed, metadata)

#     except Exception as e:
#         logger.error(
#             f"Error in embed_post_on_save signal for Post ID {instance.id}: {e}",
#             exc_info=True,
#         )

# @receiver(post_save, sender=Comment)
# def embed_comment_on_save(sender, instance, created, **kwargs):
#     """Embeds comment content and stores it in ChromaDB when a comment is saved."""
#     try:
#         logger.info(
#             f"Signal received: post_save for Comment ID {instance.id} on Post ID {instance.post.id}"
#         )
#         doc_id = f"comment_{instance.id}"
#         content_to_embed = (
#             f"Comment on post titled '{instance.post.title}': {instance.body}"
#         )
# metadata = {
#     "source_type": "comment",
#     "document_id": str(instance.id),
#     "post_id": str(instance.post.id),
#     "post_title": instance.post.title,
#     "author_username": instance.author.username,
#     "created_at": instance.created_at.isoformat(),
#     "url": f"/posts/{instance.post.id}/comment/{instance.id}",
# }

#         add_document_to_vectorstore(doc_id, content_to_embed, metadata)

#     except Exception as e:
#         logger.error(
#             f"Error in embed_comment_on_save signal for Comment ID {instance.id}: {e}",
#             exc_info=True,
#         )

# @receiver(post_save, sender=Reply)
# def embed_reply_on_save(sender, instance, created, **kwargs):
#     """Embeds reply content and stores it in ChromaDB when a reply is saved."""
#     try:
#         logger.info(f"Signal received: post_save for Reply ID {instance.id}")
#         doc_id = f"reply_{instance.id}"
#         post_title = instance.comment.post.title
#         content_to_embed = (
#             f"Reply to a comment on post titled '{post_title}': {instance.body}"
#         )
# metadata = {
#     "source_type": "reply",
#     "document_id": str(instance.id),
#     "comment_id": str(instance.comment.id),
#     "post_id": str(instance.comment.post.id),
#     "author_username": instance.author.username,
#     "created_at": instance.created_at.isoformat(),
#     "url": f"/posts/{instance.comment.post.id}/comment/{instance.comment.id}",
# }
#         add_document_to_vectorstore(doc_id, content_to_embed, metadata)
#     except Exception as e:
#         logger.error(
#             f"Error in embed_reply_on_save signal for Reply ID {instance.id}: {e}",
#             exc_info=True,
#         )
