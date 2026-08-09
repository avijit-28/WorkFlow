from django.urls import path

from .views import ConversationListView, DirectMessageListCreateView, ProjectMessageListCreateView

urlpatterns = [
    path("project-messages/", ProjectMessageListCreateView.as_view(), name="project-messages"),
    path("direct-messages/", DirectMessageListCreateView.as_view(), name="direct-messages"),
    path("conversations/", ConversationListView.as_view(), name="conversations"),
]
