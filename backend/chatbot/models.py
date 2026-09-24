import uuid

from django.db import models


def media_upload_path(instance, filename):
    return f"conversations/{instance.conversation.session_id}/{filename}"


class Conversation(models.Model):
    """
    One chat session between a car owner and the virtual mechanic.
    `context` stores the bot's rule-based conversation state (current
    symptom category, slots already collected, current stage) so the
    follow-up question flow works without calling any AI model.
    """

    STAGE_CHOICES = [
        ("greeting", "Greeting"),
        ("classifying", "Classifying query"),
        ("follow_up", "Asking follow-up questions"),
        ("ready_for_diagnosis", "Ready for diagnosis"),
        ("diagnosed", "Diagnosis given"),
        ("booking", "Booking in progress"),
        ("booked", "Booking confirmed"),
        ("rejected", "Irrelevant query rejected"),
    ]

    session_id = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    stage = models.CharField(max_length=32, choices=STAGE_CHOICES, default="greeting")
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation {self.session_id} ({self.stage})"


class Message(models.Model):
    SENDER_CHOICES = [("user", "User"), ("bot", "Bot")]

    conversation = models.ForeignKey(Conversation, related_name="messages", on_delete=models.CASCADE)
    sender = models.CharField(max_length=8, choices=SENDER_CHOICES)
    text = models.TextField(blank=True)
    media = models.ForeignKey(
        "MediaUpload", null=True, blank=True, related_name="messages", on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.sender}] {self.text[:40]}"


class MediaUpload(models.Model):
    MEDIA_TYPE_CHOICES = [("image", "Image"), ("audio", "Audio"), ("video", "Video")]

    conversation = models.ForeignKey(Conversation, related_name="media_files", on_delete=models.CASCADE)
    file = models.FileField(upload_to=media_upload_path)
    media_type = models.CharField(max_length=8, choices=MEDIA_TYPE_CHOICES)
    ai_analysis = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.media_type}:{self.file.name}"


class Diagnosis(models.Model):
    conversation = models.OneToOneField(Conversation, related_name="diagnosis", on_delete=models.CASCADE)
    category = models.CharField(max_length=64, blank=True)
    summary = models.TextField()
    probable_causes = models.JSONField(default=list, blank=True)
    suggested_repair = models.TextField()
    urgency = models.CharField(
        max_length=16,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")],
        default="medium",
    )
    used_ai = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diagnosis for {self.conversation.session_id}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    conversation = models.ForeignKey(Conversation, related_name="bookings", on_delete=models.CASCADE)
    diagnosis = models.ForeignKey(Diagnosis, null=True, blank=True, on_delete=models.SET_NULL)
    customer_name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=32)
    preferred_date = models.DateField()
    preferred_time_slot = models.CharField(max_length=32, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking #{self.id} for {self.customer_name} ({self.status})"
