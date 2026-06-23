import React, { useEffect, useState } from 'react';
import './Toast.css';

export default function Toast({ message, onUndo, onDismiss, duration = 3000 }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        setVisible(false);
        setTimeout(() => {
          if (onDismiss) onDismiss();
        }, 300); // Wait for fade out animation
      }, duration);
      
      return () => clearTimeout(timer);
    }
  }, [duration, onDismiss]);

  if (!visible && !onDismiss) return null;

  return (
    <div className={`toast-container ${visible ? 'toast-enter' : 'toast-exit'}`}>
      <div className="toast-content">
        <span className="toast-message">{message}</span>
        {onUndo && (
          <button 
            className="toast-undo-btn" 
            onClick={() => {
              setVisible(false);
              onUndo();
              if (onDismiss) setTimeout(onDismiss, 300);
            }}
          >
            Undo
          </button>
        )}
      </div>
    </div>
  );
}
