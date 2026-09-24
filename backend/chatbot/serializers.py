from rest_framework import serializers

from .models import Booking, Conversation, Diagnosis, MediaUpload, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "sender", "text", "media", "created_at"]


class MediaUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaUpload
        fields = ["id", "conversation", "file", "media_type", "ai_analysis", "uploaded_at"]
        read_only_fields = ["ai_analysis"]


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = [
            "id", "conversation", "category", "summary", "probable_causes",
            "suggested_repair", "urgency", "used_ai", "created_at",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    diagnosis = DiagnosisSerializer(read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "session_id", "stage", "messages", "diagnosis", "created_at", "updated_at"]


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "id", "conversation", "diagnosis", "customer_name", "phone_number",
            "preferred_date", "preferred_time_slot", "notes", "status", "created_at",
        ]
        read_only_fields = ["status", "created_at"]
