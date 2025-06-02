import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from LLMintegration.vectorstore_utils import (
    add_document_to_vectorstore,
    delete_document_from_vectorstore,
)

from .models import Comment, Post

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Post)
def embed_post_on_save(sender, instance, created, **kwargs):
    """Embeds post content and stores it in ChromaDB when a post is saved."""
    try:
        logger.info(f"Signal received: post_save for Post ID {instance.id}")
        doc_id = f"post_{instance.id}"
        # Combine title and content for richer embeddings
        content_to_embed = (
            f"Post Title: {instance.title}\nPost Content: {instance.content}"
        )
        if instance.image:  # Optionally include a note about an image
            content_to_embed += "\n(Note: This post includes an image.)"

        metadata = {
            "source_type": "post",
            "document_id": str(instance.id),  # Ensure it's a string
            "title": instance.title,
            "author_username": instance.author.username,
            "created_at": instance.created_at.isoformat(),
            "url": f"/posts/{instance.id}/",  # A relative URL to access the post
        }
        add_document_to_vectorstore(doc_id, content_to_embed, metadata)
    except Exception as e:
        logger.error(
            f"Error in embed_post_on_save signal for Post ID {instance.id}: {e}",
            exc_info=True,
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


@receiver(post_save, sender=Comment)
def embed_comment_on_save(sender, instance, created, **kwargs):
    """Embeds comment content and stores it in ChromaDB when a comment is saved."""
    try:
        logger.info(
            f"Signal received: post_save for Comment ID {instance.id} on Post ID {instance.post.id}"
        )
        doc_id = f"comment_{instance.id}"
        content_to_embed = (
            f"Comment on post titled '{instance.post.title}': {instance.body}"
        )
        metadata = {
            "source_type": "comment",
            "document_id": str(instance.id),  # Ensure it's a string
            "post_id": str(instance.post.id),
            "post_title": instance.post.title,
            "author_username": instance.author.username,
            "created_at": instance.created_at.isoformat(),
            "url": f"/posts/{instance.post.id}/#comment-{instance.id}",  # A relative URL to access the comment
        }
        add_document_to_vectorstore(doc_id, content_to_embed, metadata)
    except Exception as e:
        logger.error(
            f"Error in embed_comment_on_save signal for Comment ID {instance.id}: {e}",
            exc_info=True,
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
