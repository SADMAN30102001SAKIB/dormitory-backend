from django.urls import path

from .views import (
    LoginView,
    ProfileUpdateView,
    RegisterView,
    UserDeleteView,
    UserDetailView,
    UserListView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("users", UserListView.as_view(), name="user-list"),
    path("profile", ProfileUpdateView.as_view()),
    path("user/<str:username>", UserDetailView.as_view()),
    path("user", UserDeleteView.as_view()),
]
