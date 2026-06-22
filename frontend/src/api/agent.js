import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Axios Request Interceptor to inject JWT Bearer Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const login = async (username, password) => {
  try {
    const response = await api.post('/api/auth/login', { username, password });
    if (response.data && response.data.access_token) {
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('role', response.data.role);
      localStorage.setItem('region', response.data.region || '');
      localStorage.setItem('username', username);
    }
    return response.data;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};

export const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('role');
  localStorage.removeItem('region');
  localStorage.removeItem('username');
};

export const chatWithAgent = async (message, dryRun = false, conversationId = null) => {
  try {
    const response = await api.post('/api/chat', {
      message,
      include_rag: true,
      dry_run: dryRun,
      conversation_id: conversationId,
    });
    return response.data;
  } catch (error) {
    console.error('Chat error:', error);
    throw error;
  }
};

export const chatWithAgentStream = async (message, conversationId, onEvent) => {
  try {
    const token = localStorage.getItem('token');
    const headers = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        include_rag: true,
        dry_run: false,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      let errMessage = 'Failed to connect to stream';
      try {
        const parsed = JSON.parse(errText);
        errMessage = parsed.detail || errMessage;
      } catch (_) {}
      throw new Error(errMessage);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          const dataStr = trimmed.slice(6);
          try {
            const data = JSON.parse(dataStr);
            onEvent(data);
          } catch (e) {
            console.error('Error parsing SSE event data:', e, dataStr);
          }
        }
      }
    }
  } catch (error) {
    console.error('Chat stream error:', error);
    throw error;
  }
};

export const resetConversation = async (conversationId) => {
  try {
    const response = await api.delete('/api/session', {
      params: { conversation_id: conversationId },
    });
    return response.data;
  } catch (error) {
    console.error('Reset conversation error:', error);
    throw error;
  }
};

export const getRoles = async () => {
  try {
    const response = await api.get('/api/roles');
    return response.data;
  } catch (error) {
    console.error('Get roles error:', error);
    throw error;
  }
};

export const getHealth = async () => {
  try {
    const response = await api.get('/api/health');
    return response.data;
  } catch (error) {
    console.error('Health check error:', error);
    throw error;
  }
};

export const getAuditLogs = async (limit = 50, role = null, action = null) => {
  try {
    const params = { limit };
    if (role) params.role = role;
    if (action) params.action = action;
    const response = await api.get('/api/audit', { params });
    return response.data;
  } catch (error) {
    console.error('Get audit logs error:', error);
    throw error;
  }
};

export default api;
