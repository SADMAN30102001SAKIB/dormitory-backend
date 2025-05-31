from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from django.urls import include, path

# from . import views
# from .views import PostDetailAPIView, PostListCreateAPIView
from .views import CommentViewSet, PostViewSet

router = DefaultRouter(trailing_slash=False)
router.register("posts", PostViewSet)

# Nested router for comments under posts
posts_router = routers.NestedDefaultRouter(router, "posts", lookup="post")
posts_router.register("comments", CommentViewSet, basename="post-comments")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(posts_router.urls)),
]

# urlpatterns = [
#     path("posts/", PostListCreateAPIView.as_view()),  # GET + POST with slash
#     path("posts", PostListCreateAPIView.as_view()),  # GET + POST without slash
#     path(
#         "posts/<int:pk>/", PostDetailAPIView.as_view()
#     ),  # GET + PUT + DELETE with slash
#     path(
#         "posts/<int:pk>", PostDetailAPIView.as_view()
#     ),  # GET + PUT + DELETE without slash
# ]

# urlpatterns = [
#     path("posts/", views.get_posts),
#     path("posts/create/", views.create_post),
# ]
