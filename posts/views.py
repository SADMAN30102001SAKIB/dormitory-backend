from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView

from .models import Comment, Post
from .pagination import PostPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import CommentSerializer, PostSerializer

from .recommendations import get_recommended_posts
from drf_spectacular.utils import OpenApiParameter, extend_schema


@extend_schema(tags=["Posts"])
class PostViewSet(ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    pagination_class = PostPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content", "author__username"]
    ordering_fields = ["created_at"]
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    @extend_schema(
        summary="List all posts",
        description="Get a paginated list of all posts with optional search, filtering, and ordering",
        parameters=[
            OpenApiParameter(
                "search",
                str,
                description="Search posts by title, content, or author username",
                required=False,
            ),
            OpenApiParameter(
                "author",
                str,
                description="Filter posts by author username",
                required=False,
            ),
            OpenApiParameter(
                "ordering",
                str,
                description="Order by created_at (-created_at for descending)",
                required=False,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new post",
        description="Create a new post.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Get a specific post",
        description="Retrieve details of a specific post by ID",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a post",
        description="Update a post (only by the author)",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a post",
        description="Partially update a post (only by the author)",
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a post",
        description="Delete a post (only by the author)",
        responses={
            204: OpenApiResponse(description="Post deleted successfully"),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        queryset = Post.objects.all()
        author_username = self.request.query_params.get("author")
        if author_username is not None:
            queryset = queryset.filter(author__username=author_username)
        return queryset


@extend_schema(tags=["Comments"])
class CommentViewSet(ModelViewSet):
    serializer_class = CommentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["author__username"]
    ordering_fields = ["created_at"]
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    @extend_schema(
        summary="List comments for a post",
        description="Get all comments for a specific post",
        parameters=[
            OpenApiParameter(
                "search",
                str,
                description="Search comments by author username",
                required=False,
            ),
            OpenApiParameter(
                "ordering",
                str,
                description="Order by created_at (-created_at for descending)",
                required=False,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new comment",
        description="Add a new comment to a post.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Get a specific comment",
        description="Retrieve details of a specific comment",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a comment",
        description="Update a comment (only by the author)",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a comment",
        description="Partially update a comment (only by the author)",
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a comment",
        description="Delete a comment (only by the author)",
        responses={
            204: OpenApiResponse(description="Comment deleted successfully"),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        post_pk = self.kwargs.get("post_pk")
        if post_pk:
            return Comment.objects.filter(post_id=post_pk)
        return Comment.objects.all()

    def perform_create(self, serializer):
        post_pk = self.kwargs.get("post_pk")
        post = get_object_or_404(Post, pk=post_pk)  # validate existence
        serializer.save(post=post, author=self.request.user)


@extend_schema(
    tags=["Posts"],
    summary="List personalized recommended posts",
    description="Returns a paginated list of posts recommended for the authenticated user. Use `?page=` to navigate.",
    parameters=[
        OpenApiParameter(
            name="page",
            required=False,
            type=int,
            location="query",
            description="Page number (default: 1)",
        ),
    ],
    responses={200: PostSerializer(many=True)},
)
class RecommendedPostsFeedView(ListAPIView):
    """
    Returns a personalized and paginated feed of recommended posts for the
    authenticated user.

    Supports pagination via the `page` query parameter.
    e.g., /api/posts/recommended/?page=2
    """

    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Get the page number from the query parameters, default to 1
        try:
            page = int(self.request.query_params.get("page", "1"))
            if page < 1:
                page = 1
        except ValueError:
            page = 1

        page_size = 10

        user = self.request.user
        recc_posts = get_recommended_posts(user, page=page, page_size=page_size)
        # print(recc_posts)
        if not recc_posts.exists():
            # print("No recommendations found for user:", user.username)
            return Post.objects.all()  # Fallback to all posts if no recommendations
        return recc_posts
