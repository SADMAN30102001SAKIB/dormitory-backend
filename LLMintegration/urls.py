from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet

router = DefaultRouter() #automatically generate URL patterns for the viewset
router.register(r'conversations', ConversationViewSet, basename='conversation') #r'conversations' is the The URL prefix under which all the generated routes for the viewset live. basename='conversation' is used to name the URL patterns for reverse lookups. 

urlpatterns = [
    path('', include(router.urls)), 
]
