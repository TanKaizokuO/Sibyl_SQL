import React from 'react';
import './ConfirmModal.css';

export default function ConfirmModal({ isOpen, title, message, confirmLabel = "Confirm", onConfirm, onCancel }) {
  if (!isOpen) return null;

  return (
    <div className="confirm-modal-backdrop" onClick={onCancel}>
      <div className="confirm-modal-content" onClick={e => e.stopPropagation()}>
        <h3 className="confirm-modal-title">{title}</h3>
        <p className="confirm-modal-message">{message}</p>
        <div className="confirm-modal-actions">
          <button className="btn btn-ghost" onClick={onCancel}>Cancel</button>
          <button className="btn btn-ghost btn-logout confirm-modal-danger-btn" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
