/**
 * Chat Storage Utility
 * Manages client-side persistence of conversations using localStorage.
 */

/**
 * Safely decodes a JWT token using base64url parsing to extract the username (sub).
 * JWT is structured as Header.Payload.Signature. The second section (payload) contains
 * user claim objects including 'sub' (subject/username) and 'role'. This helper translates
 * base64url characters back to standard base64 for browser atob() decoding.
 *
 * @returns {string|null} The username or null if invalid/missing.
 */
export function getTokenUsername() {
  try {
    const token = localStorage.getItem('token');
    if (!token) return null;
    
    // JWT uses base64url, which requires replacing characters before atob()
    const base64Url = token.split('.')[1];
    if (!base64Url) return null;
    
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    
    const payload = JSON.parse(jsonPayload);
    return payload.sub || null;
  } catch (err) {
    console.error('Failed to decode JWT token:', err);
    return null;
  }
}

/**
 * Retrieves a user-scoped storage key based on the currently logged-in user.
 * This isolation ensures that different user accounts (e.g. north_manager vs admin_user)
 * have completely isolated conversation histories, preventing local privilege leaking.
 *
 * @returns {string|null} The storage key or null.
 */
function getStorageKey() {
  const username = getTokenUsername();
  return username ? `sybilsql_chats_${username}` : null;
}

function getStoredChats() {
  const key = getStorageKey();
  if (!key) return {};
  
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : {};
  } catch (err) {
    console.error('Failed to parse chats from localStorage:', err);
    return {};
  }
}

function writeStoredChats(chats) {
  const key = getStorageKey();
  if (!key) return false;
  
  try {
    localStorage.setItem(key, JSON.stringify(chats));
    return true;
  } catch (err) {
    console.error('Failed to write chats to localStorage (Quota exceeded?):', err);
    return false;
  }
}

/**
 * Generates a title based on the conversation history.
 */
function generateTitle(messages) {
  if (!messages || messages.length === 0) return `Conversation — ${new Date().toISOString().split('T')[0]}`;
  
  const greetingsBlocklist = ['hi', 'hello', 'hey', 'thanks', 'thank you', 'test', 'yo'];
  
  // Try to find a substantive user message
  const userMessages = messages.filter(m => m.role === 'user');
  for (const msg of userMessages) {
    const text = (msg.content || '').trim();
    if (text.length >= 10 && !greetingsBlocklist.includes(text.toLowerCase())) {
      return text.length > 60 ? text.substring(0, 60) + '...' : text;
    }
  }
  
  // Fallback to first assistant response
  const assistantMsg = messages.find(m => m.role === 'assistant' && m.content);
  if (assistantMsg) {
    const text = assistantMsg.content.trim();
    return text.length > 60 ? text.substring(0, 60) + '...' : text;
  }
  
  return `Conversation — ${new Date().toISOString().split('T')[0]}`;
}

/**
 * Saves a conversation to local storage.
 */
export function saveConversation(conversationId, messages, title = null) {
  if (!conversationId || !messages || messages.length === 0) return false;
  
  const chats = getStoredChats();
  const existingChat = chats[conversationId] || {};
  
  const updatedTitle = title || existingChat.title || generateTitle(messages);
  
  chats[conversationId] = {
    title: updatedTitle,
    messages: messages,
    createdAt: existingChat.createdAt || new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  
  return writeStoredChats(chats);
}

/**
 * Loads a single conversation.
 */
export function loadConversation(conversationId) {
  const chats = getStoredChats();
  return chats[conversationId] ? chats[conversationId].messages : [];
}

/**
 * Lists all conversations sorted by latest update.
 */
export function listConversations() {
  const chats = getStoredChats();
  const list = Object.keys(chats).map(id => ({
    id,
    title: chats[id].title,
    createdAt: chats[id].createdAt,
    updatedAt: chats[id].updatedAt,
    messageCount: chats[id].messages ? chats[id].messages.length : 0
  }));
  
  return list.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
}

/**
 * Deletes a single conversation.
 */
export function deleteConversation(conversationId) {
  const chats = getStoredChats();
  if (chats[conversationId]) {
    delete chats[conversationId];
    return writeStoredChats(chats);
  }
  return false;
}

/**
 * Clears all conversations for the current user.
 */
export function clearAllConversations() {
  const key = getStorageKey();
  if (!key) return false;
  localStorage.removeItem(key);
  return true;
}

/**
 * Evicts oldest conversations if exceeding maxCount.
 * Called only when creating a new conversation.
 */
export function pruneOldConversations(maxCount = 20) {
  const chats = getStoredChats();
  const keys = Object.keys(chats);
  
  if (keys.length <= maxCount) return true;
  
  // Sort by updatedAt descending
  const sorted = keys.map(id => ({ id, updatedAt: chats[id].updatedAt }))
    .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
    
  let changed = false;
  for (let i = maxCount; i < sorted.length; i++) {
    delete chats[sorted[i].id];
    changed = true;
  }
  
  if (changed) {
    return writeStoredChats(chats);
  }
  return true;
}

/**
 * Exports all conversations as a JSON string.
 */
export function exportConversations() {
  const chats = getStoredChats();
  const username = getTokenUsername();
  if (!username) return null;
  return JSON.stringify(chats, null, 2);
}
