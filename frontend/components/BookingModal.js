import { useState } from "react";

export default function BookingModal({ onClose, onSubmit, submitting, error }) {
  const [form, setForm] = useState({
    customer_name: "",
    phone_number: "",
    preferred_date: "",
    preferred_time_slot: "",
    notes: "",
  });

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    onSubmit(form);
  }

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>Book a Mechanic</h2>
        <form onSubmit={handleSubmit}>
          <label>
            Name
            <input
              required
              value={form.customer_name}
              onChange={(e) => update("customer_name", e.target.value)}
            />
          </label>
          <label>
            Phone Number
            <input
              required
              value={form.phone_number}
              onChange={(e) => update("phone_number", e.target.value)}
            />
          </label>
          <label>
            Preferred Date
            <input
              type="date"
              required
              value={form.preferred_date}
              onChange={(e) => update("preferred_date", e.target.value)}
            />
          </label>
          <label>
            Preferred Time Slot
            <input
              placeholder="e.g. 10:00 AM"
              value={form.preferred_time_slot}
              onChange={(e) => update("preferred_time_slot", e.target.value)}
            />
          </label>
          <label>
            Notes
            <textarea
              value={form.notes}
              onChange={(e) => update("notes", e.target.value)}
              rows={2}
            />
          </label>

          {error && <p className="error-text">{error}</p>}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? "Booking..." : "Confirm Booking"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
