# from rest_framework import status
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from rest_framework.views import APIView

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from .models import Comment, Post
from .pagination import PostPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import CommentSerializer, PostSerializer


@extend_schema(tags=["Posts"])
class PostViewSet(ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    pagination_class = PostPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "content", "author__username"]  # allows ?search=lol
    ordering_fields = ["created_at"]  # allows ?ordering=-created_at
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
                description="Order by created_at (use -created_at for descending)",
                required=False,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new post",
        description="Create a new post. Authentication required.",
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
        summary="Delete a post",
        description="Delete a post (only by the author)",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        """
        Optionally restricts the returned posts to a given author,
        by filtering against an 'author' query parameter in the URL.
        """
        queryset = Post.objects.all()
        author_username = self.request.query_params.get("author")
        if author_username is not None:
            queryset = queryset.filter(author__username=author_username)
        return queryset


@extend_schema(tags=["Comments"])
class CommentViewSet(ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    @extend_schema(
        summary="List comments for a post",
        description="Get all comments for a specific post",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new comment",
        description="Add a new comment to a post. Authentication required.",
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
        summary="Delete a comment",
        description="Delete a comment (only by the author)",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        post_pk = self.kwargs.get("post_pk")  # comes from nested router URL
        if post_pk:
            return Comment.objects.filter(post_id=post_pk)
        return Comment.objects.all()

    def perform_create(self, serializer):
        post_pk = self.kwargs.get("post_pk")
        post = get_object_or_404(Post, pk=post_pk)  # validate existence
        serializer.save(post=post, author=self.request.user)


# class PostListCreateAPIView(APIView):
#     def get(self, request):
#         posts = Post.objects.all()
#         serializer = PostSerializer(posts, many=True)
#         return Response(serializer.data)

#     def post(self, request):
#         serializer = PostSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
# class PostDetailAPIView(APIView):
#     def get(self, request, pk):
#         post = get_object_or_404(Post, pk=pk)
#         serializer = PostSerializer(post)
#         return Response(serializer.data)

#     def put(self, request, pk):
#         post = get_object_or_404(Post, pk=pk)
#         serializer = PostSerializer(post, data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     def delete(self, request, pk):
#         post = get_object_or_404(Post, pk=pk)
#         post.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)


# @api_view(["GET"])
# def get_posts(request):
#     posts = Post.objects.all()
#     serializer = PostSerializer(posts, many=True)
#     return Response(serializer.data)


# @api_view(["POST"])
# def create_post(request):
#     serializer = PostSerializer(data=request.data)
#     if serializer.is_valid():
#         serializer.save()
#         return Response(serializer.data, status=201)
#     return Response(serializer.errors, status=400)
