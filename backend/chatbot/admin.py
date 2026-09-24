from django.contrib import admin

from .models import Booking, Conversation, Diagnosis, MediaUpload, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ["sender", "text", "media", "created_at"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "session_id", "stage", "created_at", "updated_at"]
    list_filter = ["stage"]
    inlines = [MessageInline]


@admin.register(MediaUpload)
class MediaUploadAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "media_type", "uploaded_at"]


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "category", "urgency", "used_ai", "created_at"]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "customer_name", "preferred_date", "status", "created_at"]
    list_filter = ["status"]
