from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Comment, Post, Tag
from .pagination import PostPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import CommentSerializer, PostSerializer, TagSerializer

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
        responses={
            200: PostSerializer(many=True),
            400: OpenApiResponse(description="Bad request - invalid parameters"),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new post",
        description="Create a new post with multiple media files support. Supports images (JPG, JPEG, PNG, GIF, BMP, WEBP, SVG, TIFF), videos (MP4, AVI, MOV, WMV, FLV, WEBM, MKV, M4V, 3GP, OGV), audio (MP3, WAV, OGG, M4A, AAC, FLAC, WMA, OPUS), and documents (PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX). Max file size: 50MB each.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "example": "My Amazing Post"},
                    "content": {
                        "type": "string",
                        "example": "This is the content of my post",
                    },
                    "source_url": {
                        "type": "string",
                        "format": "uri",
                        "example": "https://example.com",
                    },
                    "tag_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of existing tag IDs to associate with the post",
                        "example": [1, 2, 3],
                    },
                    "tag_objects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        },
                        "description": "List of tag objects to create/associate with the post",
                        "example": [{"name": "technology"}, {"name": "tutorial"}],
                    },
                },
                "required": ["content"],
            },
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "source_url": {"type": "string", "format": "uri"},
                    "tag_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of existing tag IDs to associate with the post",
                    },
                    "tag_objects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        },
                        "description": "List of tag objects to create/associate with the post",
                    },
                    "image_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple image files to upload",
                    },
                    "video_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple video files to upload",
                    },
                    "audio_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple audio files to upload",
                    },
                    "document_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple document files to upload",
                    },
                },
            },
        },
        responses={
            201: PostSerializer,
            400: OpenApiResponse(description="Bad request - validation errors"),
            401: OpenApiResponse(description="Authentication required"),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Get a specific post",
        description="Retrieve details of a specific post by ID",
        responses={
            200: PostSerializer,
            404: OpenApiResponse(description="Post not found"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a post",
        description="Update a post (only by the author). Supports multiple media files upload including images, videos, audio, and documents. Max file size: 50MB each.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "example": "Updated Post Title"},
                    "content": {"type": "string", "example": "Updated content"},
                    "source_url": {
                        "type": "string",
                        "format": "uri",
                        "example": "https://updated-example.com",
                    },
                    "tag_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of existing tag IDs to associate with the post",
                        "example": [1, 2, 3],
                    },
                    "tag_objects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        },
                        "description": "List of tag objects to create/associate with the post",
                        "example": [{"name": "updated"}, {"name": "post"}],
                    },
                },
            },
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "source_url": {"type": "string", "format": "uri"},
                    "tag_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of existing tag IDs to associate with the post",
                    },
                    "tag_objects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        },
                        "description": "List of tag objects to create/associate with the post",
                    },
                    "image_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple image files to upload",
                    },
                    "video_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple video files to upload",
                    },
                    "audio_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple audio files to upload",
                    },
                    "document_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple document files to upload",
                    },
                },
            },
        },
        responses={
            200: PostSerializer,
            400: OpenApiResponse(description="Bad request - validation errors"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied - not the author"),
            404: OpenApiResponse(description="Post not found"),
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a post",
        description="Partially update a post (only by the author). Supports multiple media files upload including images, videos, audio, and documents. Max file size: 50MB each.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "example": "Partially Updated Title"},
                    "content": {
                        "type": "string",
                        "example": "Partially updated content",
                    },
                    "source_url": {
                        "type": "string",
                        "format": "uri",
                        "example": "https://partial-update.com",
                    },
                    "tag_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of existing tag IDs to associate with the post",
                        "example": [1, 2],
                    },
                    "tag_objects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        },
                        "description": "List of tag objects to create/associate with the post",
                        "example": [{"name": "updated"}],
                    },
                },
            },
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "source_url": {"type": "string", "format": "uri"},
                    "tag_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of existing tag IDs to associate with the post",
                    },
                    "tag_objects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"name": {"type": "string"}},
                        },
                        "description": "List of tag objects to create/associate with the post",
                    },
                    "image_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple image files to upload",
                    },
                    "video_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple video files to upload",
                    },
                    "audio_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple audio files to upload",
                    },
                    "document_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple document files to upload",
                    },
                },
            },
        },
        responses={
            200: PostSerializer,
            400: OpenApiResponse(description="Bad request - validation errors"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied - not the author"),
            404: OpenApiResponse(description="Post not found"),
        },
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
        responses={
            200: CommentSerializer(many=True),
            404: OpenApiResponse(description="Post not found"),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new comment",
        description="Add a new comment to a post with multiple media files support. Supports images (JPG, JPEG, PNG, GIF, BMP, WEBP, SVG, TIFF), videos (MP4, AVI, MOV, WMV, FLV, WEBM, MKV, M4V, 3GP, OGV), audio (MP3, WAV, OGG, M4A, AAC, FLAC, WMA, OPUS), and documents (PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX). Max file size: 50MB each.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "body": {
                        "type": "string",
                        "example": "This is my comment",
                        "description": "Content of the comment",
                    },
                },
                "required": ["body"],
            },
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "body": {"type": "string"},
                    "image_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple image files to upload",
                    },
                    "video_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple video files to upload",
                    },
                    "audio_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple audio files to upload",
                    },
                    "document_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple document files to upload",
                    },
                },
            },
        },
        responses={
            201: CommentSerializer,
            400: OpenApiResponse(description="Bad request - validation errors"),
            401: OpenApiResponse(description="Authentication required"),
            404: OpenApiResponse(description="Post not found"),
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Get a specific comment",
        description="Retrieve details of a specific comment",
        responses={
            200: CommentSerializer,
            404: OpenApiResponse(description="Comment not found"),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a comment",
        description="Update a comment (only by the author). Supports multiple media files upload including images, videos, audio, and documents. Max file size: 50MB each.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "body": {"type": "string", "example": "Updated comment content"},
                },
                "required": ["body"],
            },
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "body": {"type": "string"},
                    "image_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple image files to upload",
                    },
                    "video_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple video files to upload",
                    },
                    "audio_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple audio files to upload",
                    },
                    "document_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple document files to upload",
                    },
                },
            },
        },
        responses={
            200: CommentSerializer,
            400: OpenApiResponse(description="Bad request - validation errors"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied - not the author"),
            404: OpenApiResponse(description="Comment not found"),
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a comment",
        description="Partially update a comment (only by the author). Supports multiple media files upload including images, videos, audio, and documents. Max file size: 50MB each.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "body": {"type": "string", "example": "Partially updated comment"},
                },
            },
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "body": {"type": "string"},
                    "image_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple image files to upload",
                    },
                    "video_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple video files to upload",
                    },
                    "audio_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple audio files to upload",
                    },
                    "document_files": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"},
                        "description": "Multiple document files to upload",
                    },
                },
            },
        },
        responses={
            200: CommentSerializer,
            400: OpenApiResponse(description="Bad request - validation errors"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Permission denied - not the author"),
            404: OpenApiResponse(description="Comment not found"),
        },
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


@extend_schema(tags=["Tags"])
class TagViewSet(ModelViewSet):
    """
    ViewSet for managing tags.
    Supports creating, reading, updating, and deleting tags.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="List all tags",
        description="Get a list of all available tags with optional search and ordering",
        parameters=[
            OpenApiParameter(
                "search",
                str,
                description="Search tags by name",
                required=False,
            ),
            OpenApiParameter(
                "ordering",
                str,
                description="Order by name or id (-name for descending)",
                required=False,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new tag",
        description="Create a new tag",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Get a specific tag",
        description="Retrieve details of a specific tag by ID",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a tag",
        description="Update a tag",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a tag",
        description="Partially update a tag",
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a tag",
        description="Delete a tag",
        responses={
            204: OpenApiResponse(description="Tag deleted successfully"),
            404: OpenApiResponse(description="Tag not found"),
        },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Get posts for a tag",
        description="Get all posts associated with this tag",
        responses={200: PostSerializer(many=True)},
    )
    @action(detail=True, methods=["get"])
    def posts(self, request, pk=None):
        """Get all posts for a specific tag"""
        tag = self.get_object()
        posts = tag.posts.all()
        serializer = PostSerializer(posts, many=True, context={"request": request})
        return Response(serializer.data)
