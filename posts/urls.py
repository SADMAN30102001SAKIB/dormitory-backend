from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import CommentViewSet, PostViewSet, RecommendedPostsFeedView

router = DefaultRouter(trailing_slash=False)
router.register("posts", PostViewSet)

posts_router = routers.NestedDefaultRouter(router, "posts", lookup="post")
posts_router.register("comments", CommentViewSet, basename="post-comments")

urlpatterns = [
    # Personalized recommendations for authenticated users
    path(
        "posts/recommended",
        RecommendedPostsFeedView.as_view(),
        name="recommended-posts",
    ),
    path("", include(router.urls)),
    path("", include(posts_router.urls)),
]
