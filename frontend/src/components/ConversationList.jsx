import React, { useState, useEffect } from 'react';
import { Trash2, MessageSquare, Clock, Download, X } from 'lucide-react';
import ConfirmModal from './ConfirmModal';
import './ConversationList.css';

export default function ConversationList({ 
  isOpen, 
  onClose, 
  conversations, 
  currentConversationId, 
  onSelect, 
  onDelete, 
  onClearAll,
  onExport 
}) {
  const [showConfirmClear, setShowConfirmClear] = useState(false);

  // Close drawer on escape
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.round(diffMs / 60000);
    const diffHours = Math.round(diffMs / 3600000);
    const diffDays = Math.round(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) return `${diffHours} hr ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  const handleClearConfirm = () => {
    setShowConfirmClear(false);
    onClearAll();
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="conversation-drawer">
        <div className="drawer-header">
          <h3>Chat History</h3>
          <button className="btn-icon" onClick={onClose} title="Close">
            <X size={20} />
          </button>
        </div>

        <div className="conversation-list">
          {conversations.length === 0 ? (
            <div className="empty-history">
              <MessageSquare size={32} opacity={0.5} />
              <p>No saved conversations</p>
            </div>
          ) : (
            conversations.map(chat => (
              <div 
                key={chat.id} 
                className={`conversation-item ${chat.id === currentConversationId ? 'active' : ''}`}
                onClick={() => onSelect(chat.id)}
              >
                <div className="chat-title-row">
                  <span className="chat-title" title={chat.title}>{chat.title}</span>
                  <button 
                    className="btn-delete-chat" 
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(chat.id);
                    }}
                    title="Delete Conversation"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="chat-meta-row">
                  <span className="chat-time">
                    <Clock size={12} />
                    {formatDate(chat.updatedAt)}
                  </span>
                  <span className="chat-count">
                    {chat.messageCount} msg{chat.messageCount !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="drawer-footer">
          {conversations.length > 0 && (
            <>
              <button 
                className="btn btn-ghost btn-export-all" 
                onClick={onExport}
                title="Export conversations as JSON"
              >
                <Download size={16} />
                <span>Export All</span>
              </button>
              <button 
                className="btn btn-ghost btn-logout btn-clear-all" 
                onClick={() => setShowConfirmClear(true)}
              >
                <Trash2 size={16} />
                <span>Clear All</span>
              </button>
            </>
          )}
        </div>

        <ConfirmModal 
          isOpen={showConfirmClear}
          title="Clear Chat History"
          message="This will permanently delete all saved conversations for your account. This action cannot be undone."
          confirmLabel="Confirm Delete All"
          onConfirm={handleClearConfirm}
          onCancel={() => setShowConfirmClear(false)}
        />
      </div>
    </>
  );
}
