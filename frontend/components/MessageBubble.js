export default function MessageBubble({ sender, text }) {
  const isBot = sender === "bot";
  return (
    <div className={`bubble-row ${isBot ? "bot-row" : "user-row"}`}>
      <div className={`bubble ${isBot ? "bot-bubble" : "user-bubble"}`}>
        <span className="bubble-label">{isBot ? "Mechanic Bot" : "You"}</span>
        <p>{text}</p>
      </div>
    </div>
  );
}
