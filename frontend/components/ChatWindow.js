import { useEffect, useRef, useState } from "react";
import MessageBubble from "./MessageBubble";
import MediaUpload from "./MediaUpload";
import BookingModal from "./BookingModal";
import {
  createBooking,
  getOrCreateSessionId,
  requestDiagnosis,
  resetSession,
  sendChatMessage,
  uploadMedia,
} from "../lib/api";

const WELCOME_MESSAGE = {
  sender: "bot",
  text:
    "Hi, I'm your virtual mechanic. Tell me what's going on with your vehicle — " +
    "for example, a strange noise, a warning light, or trouble starting.",
};

export default function ChatWindow() {
  const [sessionId, setSessionId] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [readyForDiagnosis, setReadyForDiagnosis] = useState(false);
  const [diagnosis, setDiagnosis] = useState(null);
  const [diagnosing, setDiagnosing] = useState(false);
  const [showBooking, setShowBooking] = useState(false);
  const [bookingSubmitting, setBookingSubmitting] = useState(false);
  const [bookingError, setBookingError] = useState("");
  const [confirmedBooking, setConfirmedBooking] = useState(null);
  const [errorBanner, setErrorBanner] = useState("");

  const scrollRef = useRef(null);

  useEffect(() => {
    setSessionId(getOrCreateSessionId());
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, diagnosis]);

  function pushMessage(sender, text) {
    setMessages((prev) => [...prev, { sender, text }]);
  }

  async function handleSend(e) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || sending || !sessionId) return;

    pushMessage("user", text);
    setInput("");
    setSending(true);
    setErrorBanner("");
    try {
      const data = await sendChatMessage(sessionId, text);
      setConversationId(data.conversation_id);
      pushMessage("bot", data.reply);
      setReadyForDiagnosis(Boolean(data.ready_for_diagnosis));
    } catch (err) {
      setErrorBanner(err.message || "Something went wrong. Please try again.");
    } finally {
      setSending(false);
    }
  }

  async function handleUpload(file, mediaType) {
    if (!sessionId) return;
    setUploading(true);
    setErrorBanner("");
    pushMessage("user", `[attached ${mediaType}: ${file.name}]`);
    try {
      const data = await uploadMedia(sessionId, file, mediaType);
      if (data.ai_analysis) {
        pushMessage(
          "bot",
          `Got it — I looked at the ${mediaType} you sent: ${data.ai_analysis}`
        );
      } else {
        pushMessage(
          "bot",
          `Thanks, I've attached that ${mediaType} to your case. Please continue describing the issue.`
        );
      }
    } catch (err) {
      setErrorBanner(err.message || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDiagnose() {
    if (!conversationId) return;
    setDiagnosing(true);
    setErrorBanner("");
    try {
      const data = await requestDiagnosis(conversationId);
      setDiagnosis(data);
      pushMessage(
        "bot",
        `${data.summary}\n\nSuggested next step: ${data.suggested_repair}`
      );
    } catch (err) {
      setErrorBanner(err.message || "Could not generate diagnosis yet.");
    } finally {
      setDiagnosing(false);
    }
  }

  async function handleBookingSubmit(form) {
    setBookingSubmitting(true);
    setBookingError("");
    try {
      const booking = await createBooking({
        conversation_id: conversationId,
        ...form,
      });
      setConfirmedBooking(booking);
      setShowBooking(false);
      pushMessage(
        "bot",
        `Your mechanic booking is confirmed for ${booking.preferred_date}` +
          `${booking.preferred_time_slot ? " (" + booking.preferred_time_slot + ")" : ""}.` +
          ` Booking reference: #${booking.id}.`
      );
    } catch (err) {
      setBookingError(err.message || "Booking failed. Please check the details.");
    } finally {
      setBookingSubmitting(false);
    }
  }

  function handleNewConversation() {
    setSessionId(resetSession());
    setConversationId(null);
    setMessages([WELCOME_MESSAGE]);
    setReadyForDiagnosis(false);
    setDiagnosis(null);
    setConfirmedBooking(null);
    setErrorBanner("");
  }

  return (
    <div className="chat-shell">
      <header className="chat-header">
        <div>
          <h1>AI Car Mechanic</h1>
          <p className="subtitle">Describe your issue and get a diagnosis</p>
        </div>
        <button className="btn-secondary" onClick={handleNewConversation}>
          New Conversation
        </button>
      </header>

      <div className="chat-body" ref={scrollRef}>
        {messages.map((m, idx) => (
          <MessageBubble key={idx} sender={m.sender} text={m.text} />
        ))}

        {diagnosis && (
          <div className="diagnosis-card">
            <h3>Diagnosis</h3>
            <p>
              <strong>Category:</strong> {diagnosis.category.replace("_", " ")}
            </p>
            <p>
              <strong>Urgency:</strong>{" "}
              <span className={`urgency urgency-${diagnosis.urgency}`}>
                {diagnosis.urgency}
              </span>
            </p>
            <p>{diagnosis.summary}</p>
            <p>
              <strong>Suggested repair:</strong> {diagnosis.suggested_repair}
            </p>
            {!confirmedBooking && (
              <button className="btn-primary" onClick={() => setShowBooking(true)}>
                Book Mechanic
              </button>
            )}
            {confirmedBooking && (
              <p className="booking-confirmed">
                ✅ Booking #{confirmedBooking.id} confirmed for{" "}
                {confirmedBooking.preferred_date}
              </p>
            )}
          </div>
        )}
      </div>

      {errorBanner && <div className="error-banner">{errorBanner}</div>}

      <div className="chat-footer">
        <MediaUpload onUpload={handleUpload} disabled={uploading || sending} />
        {uploading && <p className="uploading-note">Uploading & analyzing media…</p>}

        <form className="chat-input-row" onSubmit={handleSend}>
          <input
            type="text"
            placeholder="Describe what's wrong with your car..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={sending}
          />
          <button type="submit" className="btn-primary" disabled={sending || !input.trim()}>
            {sending ? "..." : "Send"}
          </button>
        </form>

        {readyForDiagnosis && !diagnosis && (
          <button
            className="btn-primary full-width"
            onClick={handleDiagnose}
            disabled={diagnosing}
          >
            {diagnosing ? "Diagnosing..." : "Get Diagnosis"}
          </button>
        )}
      </div>

      {showBooking && (
        <BookingModal
          onClose={() => setShowBooking(false)}
          onSubmit={handleBookingSubmit}
          submitting={bookingSubmitting}
          error={bookingError}
        />
      )}
    </div>
  );
}
