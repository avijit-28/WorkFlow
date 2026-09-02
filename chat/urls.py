from django.urls import path

from .views import (
    ConversationListView,
    DirectMessageDetailView,
    DirectMessageListCreateView,
    ProjectMessageDetailView,
    ProjectMessageHideView,
    ProjectMessageListCreateView,
)

urlpatterns = [
    path("project-messages/", ProjectMessageListCreateView.as_view(), name="project-messages"),
    path("project-messages/hide/", ProjectMessageHideView.as_view(), name="project-messages-hide"),
    path("project-messages/<int:pk>/", ProjectMessageDetailView.as_view(), name="project-message-detail"),
    path("direct-messages/", DirectMessageListCreateView.as_view(), name="direct-messages"),
    path("direct-messages/<int:pk>/", DirectMessageDetailView.as_view(), name="direct-message-detail"),
    path("conversations/", ConversationListView.as_view(), name="conversations"),
]
