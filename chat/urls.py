from django.urls import path

from .views import (
    BlockStatusView,
    BlockUserView,
    ConversationListView,
    DirectMessageDeleteConversationView,
    DirectMessageDetailView,
    DirectMessageHideView,
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
    path("direct-messages/hide/", DirectMessageHideView.as_view(), name="direct-messages-hide"),
    path(
        "direct-messages/delete-conversation/",
        DirectMessageDeleteConversationView.as_view(),
        name="direct-messages-delete-conversation",
    ),
    path("direct-messages/<int:pk>/", DirectMessageDetailView.as_view(), name="direct-message-detail"),
    path("conversations/", ConversationListView.as_view(), name="conversations"),
    path("block/", BlockUserView.as_view(), name="block-user"),
    path("block-status/", BlockStatusView.as_view(), name="block-status"),
]
