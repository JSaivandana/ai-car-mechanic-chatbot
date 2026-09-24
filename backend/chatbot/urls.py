from django.urls import path

from . import views

urlpatterns = [
    path("chat/", views.ChatView.as_view(), name="chat"),
    path("upload/", views.UploadView.as_view(), name="upload"),
    path("diagnosis/", views.DiagnosisView.as_view(), name="diagnosis"),
    path("booking/", views.BookingView.as_view(), name="booking-create"),
    path("booking/<int:booking_id>/", views.BookingDetailView.as_view(), name="booking-detail"),
    # Convenience endpoint (not in the minimum list) to reload history:
    path("conversation/<str:session_id>/", views.ConversationDetailView.as_view(), name="conversation-detail"),
]
