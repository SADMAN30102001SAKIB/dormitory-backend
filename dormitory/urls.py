from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from landing.views import landing_page
from users.views import CustomTokenObtainPairView, CustomTokenRefreshView

urlpatterns = [
    path("", landing_page, name="landing"),
    path("admin/", admin.site.urls),
    path("api/", include("posts.urls")),
    path("api/auth/", include("users.urls")),
    path("api/llm/", include("LLMintegration.urls")),
    path("api/token", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
