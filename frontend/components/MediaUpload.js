import { useRef, useState } from "react";

const ACCEPT_BY_TYPE = {
  image: "image/png,image/jpeg,image/webp",
  audio: "audio/mpeg,audio/wav,audio/mp4,audio/ogg",
  video: "video/mp4,video/quicktime,video/webm",
};

export default function MediaUpload({ onUpload, disabled }) {
  const [pendingType, setPendingType] = useState(null);
  const inputRef = useRef(null);

  function triggerPicker(mediaType) {
    setPendingType(mediaType);
    inputRef.current.setAttribute("accept", ACCEPT_BY_TYPE[mediaType]);
    inputRef.current.click();
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file && pendingType) {
      onUpload(file, pendingType);
    }
    e.target.value = "";
  }

  return (
    <div className="media-upload-row">
      <input
        type="file"
        ref={inputRef}
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
      <button
        type="button"
        className="icon-btn"
        disabled={disabled}
        title="Attach a photo"
        onClick={() => triggerPicker("image")}
      >
        📷 Photo
      </button>
      <button
        type="button"
        className="icon-btn"
        disabled={disabled}
        title="Attach audio"
        onClick={() => triggerPicker("audio")}
      >
        🎙️ Audio
      </button>
      <button
        type="button"
        className="icon-btn"
        disabled={disabled}
        title="Attach video"
        onClick={() => triggerPicker("video")}
      >
        🎥 Video
      </button>
    </div>
  );
}
