from django.urls import path

from .views import LoginView, ProfileUpdateView, RegisterView, UserListView

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("users", UserListView.as_view(), name="user-list"),
    path("profile", ProfileUpdateView.as_view()),
]
