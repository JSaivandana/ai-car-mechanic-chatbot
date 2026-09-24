import os

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import ai_client, bot_logic
from .models import Booking, Conversation, Diagnosis, MediaUpload, Message
from .serializers import (
    BookingSerializer,
    ConversationSerializer,
    DiagnosisSerializer,
    MediaUploadSerializer,
)


def _get_or_create_conversation(session_id):
    conversation, _ = Conversation.objects.get_or_create(session_id=session_id)
    return conversation


class ChatView(APIView):
    """
    POST /api/chat/
    Body: {"session_id": "<string>", "message": "<string>"}

    Runs the rule-based bot engine (bot_logic.handle_user_message) on the
    user's message and returns the bot's reply. Falls back to Gemini only
    inside bot_logic for genuinely ambiguous topic classification.
    """

    def post(self, request):
        session_id = request.data.get("session_id")
        text = request.data.get("message", "")

        if not session_id:
            return Response({"error": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not text or not text.strip():
            return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

        conversation = _get_or_create_conversation(session_id)
        Message.objects.create(conversation=conversation, sender="user", text=text)

        media_analysis = (conversation.context or {}).get("media_analysis")
        reply, ready_for_diagnosis = bot_logic.handle_user_message(conversation, text, media_analysis)
        conversation.save()

        bot_message = Message.objects.create(conversation=conversation, sender="bot", text=reply)

        return Response(
            {
                "conversation_id": conversation.id,
                "session_id": conversation.session_id,
                "stage": conversation.stage,
                "reply": reply,
                "message_id": bot_message.id,
                "ready_for_diagnosis": ready_for_diagnosis,
            },
            status=status.HTTP_200_OK,
        )


class UploadView(APIView):
    """
    POST /api/upload/
    multipart/form-data: session_id, file, media_type (image|audio|video)

    Saves the file, then calls the AI client to analyze it (the ONLY way
    to interpret binary media — traditional logic can't do this). The
    resulting analysis text is attached to the conversation context so it
    feeds into the eventual diagnosis.
    """

    def post(self, request):
        session_id = request.data.get("session_id")
        media_type = request.data.get("media_type")
        uploaded_file = request.FILES.get("file")

        if not session_id or not uploaded_file or not media_type:
            return Response(
                {"error": "session_id, media_type and file are all required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if media_type not in dict(MediaUpload.MEDIA_TYPE_CHOICES):
            return Response({"error": "invalid media_type"}, status=status.HTTP_400_BAD_REQUEST)

        conversation = _get_or_create_conversation(session_id)
        media = MediaUpload.objects.create(
            conversation=conversation, file=uploaded_file, media_type=media_type
        )

        mime_type = uploaded_file.content_type or "application/octet-stream"
        analysis = ai_client.analyze_media(media.file.path, media_type, mime_type)
        if analysis:
            media.ai_analysis = analysis
            media.save(update_fields=["ai_analysis"])

            ctx = conversation.context or {}
            ctx["media_analysis"] = analysis
            conversation.context = ctx
            conversation.save(update_fields=["context"])

        Message.objects.create(
            conversation=conversation,
            sender="user",
            text=f"[uploaded {media_type}: {os.path.basename(media.file.name)}]",
            media=media,
        )

        serializer = MediaUploadSerializer(media)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DiagnosisView(APIView):
    """
    POST /api/diagnosis/
    Body: {"conversation_id": <int>}

    Diagnosis is computed by rule-based scoring in bot_logic.build_diagnosis.
    Gemini is used only inside that function, and only to phrase the
    already-decided diagnosis in natural language (optional, with a
    template fallback).
    """

    def post(self, request):
        conversation_id = request.data.get("conversation_id")
        if not conversation_id:
            return Response({"error": "conversation_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        conversation = get_object_or_404(Conversation, id=conversation_id)

        if conversation.stage not in ("ready_for_diagnosis", "diagnosed"):
            return Response(
                {"error": "Not enough information yet. Continue the conversation via /api/chat/ first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        diagnosis_data = bot_logic.build_diagnosis(conversation)

        diagnosis, _ = Diagnosis.objects.update_or_create(
            conversation=conversation,
            defaults=diagnosis_data,
        )
        conversation.stage = "diagnosed"
        conversation.save(update_fields=["stage"])

        Message.objects.create(
            conversation=conversation,
            sender="bot",
            text=diagnosis.summary + f"\n\nSuggested next step: {diagnosis.suggested_repair}",
        )

        serializer = DiagnosisSerializer(diagnosis)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BookingView(APIView):
    """
    POST /api/booking/
    Body: {conversation_id, customer_name, phone_number, preferred_date,
           preferred_time_slot?, notes?}

    Pure traditional backend logic — no AI involved in booking at all.
    """

    def post(self, request):
        conversation_id = request.data.get("conversation_id")
        conversation = get_object_or_404(Conversation, id=conversation_id)

        diagnosis = getattr(conversation, "diagnosis", None)

        serializer = BookingSerializer(data={
            "conversation": conversation.id,
            "diagnosis": diagnosis.id if diagnosis else None,
            "customer_name": request.data.get("customer_name"),
            "phone_number": request.data.get("phone_number"),
            "preferred_date": request.data.get("preferred_date"),
            "preferred_time_slot": request.data.get("preferred_time_slot", ""),
            "notes": request.data.get("notes", ""),
        })
        serializer.is_valid(raise_exception=True)
        booking = serializer.save(status="confirmed")

        conversation.stage = "booked"
        conversation.save(update_fields=["stage"])

        Message.objects.create(
            conversation=conversation,
            sender="bot",
            text=(
                f"Your mechanic booking is confirmed for {booking.preferred_date} "
                f"({booking.preferred_time_slot or 'any time'}). Booking reference: #{booking.id}."
            ),
        )

        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    """
    GET /api/booking/{id}/
    """

    def get(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)
        return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)


class ConversationDetailView(APIView):
    """
    GET /api/conversation/{session_id}/
    Convenience endpoint (beyond the minimum spec) so the frontend can
    reload chat + diagnosis history on refresh.
    """

    def get(self, request, session_id):
        conversation = get_object_or_404(Conversation, session_id=session_id)
        return Response(ConversationSerializer(conversation).data, status=status.HTTP_200_OK)
