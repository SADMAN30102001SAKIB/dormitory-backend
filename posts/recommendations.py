import logging
from django.contrib.auth.models import User
from .models import Post, PostView
from users.interest_modeling import get_user_interest_vector
from LLMintegration.vectorstore_utils import search_by_vector, ORIGINAL_DOC_ID_KEY
from django.db import models

logger = logging.getLogger(__name__)

CANDIDATE_POOL_SIZE = 200
MAX_CANDIDATE_POOL_MULTIPLIER = (
    5  # max times to expand the pool (e.g., up to 1000 candidates)
)


def get_recommended_posts(user: User, page: int = 1, page_size: int = 10):
    """
    Generates a paginated list of personalized post recommendations for a user.

    This function:
    1. Fetches a large pool of candidate documents from the vector store.
    2. Includes parent posts of relevant comments and replies.
    3. Filters out posts the user has already seen or created.
    4. Returns a specific page of the final, clean recommendation list.

    Args:
        user (User): The user for whom to generate recommendations.
        page (int): The page number of the recommendation results.
        page_size (int): The number of recommendations per page.

    Returns:
        QuerySet[Post]: A queryset of recommended Post objects for the given page.
    """
    # 1. Get the user's interest vector
    interest_vector = get_user_interest_vector(user)

    if (
        interest_vector is None
    ):  #  user has no interaction history and no interests provided
        logger.warning(
            f"No interest vector for user {user.username}. Cannot generate recommendations."
        )
        return Post.objects.none()

    # 2. Find a large pool of similar documents in the vector store
    # prepare exclude_ids early
    seen_post_ids = PostView.objects.filter(user=user).values_list("post_id", flat=True)
    # is fetching all the IDs of posts that the given user has already viewed. The query filters for entries where the user matches the given user.
    # Extracting post_id Values: The values_list("post_id", flat=True) method retrieves only the post_id field from the filtered results. The flat=True argument ensures that the result is a flat list of IDs, rather than a list of tuples.
    created_post_ids = Post.objects.filter(author=user).values_list("id", flat=True)
    exclude_ids = set(seen_post_ids) | set(
        created_post_ids
    )  # union seen and created post IDs

    # iteratively expand the candidate pool until we get enough unseen posts
    candidate_pool = CANDIDATE_POOL_SIZE
    similar_chunks = []
    unique_filtered_ids = []
    for _ in range(MAX_CANDIDATE_POOL_MULTIPLIER):
        similar_chunks = search_by_vector(
            embedding_vector=interest_vector.tolist(),  # convert to list for compatibility
            k=candidate_pool,  # this is the iterator
            fetch_k=candidate_pool * 2,
            use_mmr=False,
        )
        # extract and filter IDs
        candidate_post_ids = []
        for chunk in similar_chunks:
            doc_id = chunk.metadata.get(ORIGINAL_DOC_ID_KEY)
            try:
                if doc_id and doc_id.startswith("post_"):
                    pid = int(doc_id.split("_")[1])  # extract post ID from "post_<id>"
                elif doc_id and doc_id.startswith(("comment_", "reply_")):
                    pid = int(chunk.metadata.get("post_id", 0))
                else:
                    continue

                if pid and pid not in exclude_ids:
                    candidate_post_ids.append(pid)
            except Exception:
                continue
        # preserve order and unique
        # Converts candidate_post_ids into a dictionary (keys preserve order and remove duplicates).
        candidate_post_ids_dict = dict.fromkeys(candidate_post_ids)
        # Converts the dictionary back into a list, ensuring the IDs are unique and their original order is preserved.
        unique_filtered_ids = list(candidate_post_ids_dict)
        # if enough for pagination, break
        if len(unique_filtered_ids) >= page * page_size:
            break  # from the loop as we have enough unique IDs
        # otherwise expand and retry
        candidate_pool += CANDIDATE_POOL_SIZE

    if not unique_filtered_ids:  # no new posts found. either no posts or all seen.
        logger.info(
            f"Vector search returned no new posts for user {user.username} even after expanding pool maximum times. no new posts found. either no posts or all seen."
        )
        return Post.objects.none()

    # 6. Apply pagination to the clean list of IDs
    # calculates the starting index for the current page
    offset = (page - 1) * page_size
    paginated_ids = unique_filtered_ids[offset : offset + page_size]
    if not paginated_ids:
        logger.info(
            f"No new recommendations for user {user.username} on page {page} SOMEHOW."
        )
        return Post.objects.none()

    # 7. Fetch and return the final list of post objects, preserving order
    preserved_order = models.Case(
        *[models.When(pk=pk, then=pos) for pos, pk in enumerate(paginated_ids)]
    )  # Create a conditional expression to preserve the order of paginated_ids in the database query. For example, if paginated_ids = [5, 3, 8], the query ensures the posts are returned in the same order.

    recommended_posts = Post.objects.filter(pk__in=paginated_ids).order_by(
        preserved_order
    )

    logger.info(
        f"Returning {recommended_posts.count()} recommendations for user {user.username} on page {page}."
    )
    return recommended_posts  # returns a QUERYSET of Post objects
