import { useState, useEffect, useRef } from 'react'
import { Brain, Database, Send, Loader2, AlertCircle, Code, Eye, LogOut, Shield, MapPin, ClipboardList, Menu } from 'lucide-react'
import { chatWithAgent, chatWithAgentStream, resetConversation, logout, getAuditLogs } from './api/agent'
import LoginForm from './components/LoginForm'
import DataVisualizerEnhanced from './components/DataVisualizerEnhanced'
import SuggestionChips from './components/SuggestionChips'
import ConversationList from './components/ConversationList'
import Toast from './components/Toast'
import {
  saveConversation, loadConversation, listConversations,
  deleteConversation, clearAllConversations, pruneOldConversations,
  exportConversations, getTokenUsername
} from './utils/chatStore'
import './components/DataVisualizer.css'
import './App.css'

const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

function Typewriter({ text, speed = 5, onComplete }) {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    let index = 0;
    setDisplayedText('');
    const interval = setInterval(() => {
      setDisplayedText((prev) => prev + text.charAt(index));
      index++;
      if (index >= text.length) {
        clearInterval(interval);
        if (onComplete) onComplete();
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  return <span className="streaming-text">{displayedText}</span>;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'))
  const [currentUser, setCurrentUser] = useState({
    username: localStorage.getItem('username') || '',
    role: localStorage.getItem('role') || '',
    region: localStorage.getItem('region') || ''
  })

  const [conversationId, setConversationId] = useState(generateUUID())
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [dryRun, setDryRun] = useState(false)

  const [showAuditLogs, setShowAuditLogs] = useState(false)
  const [auditLogs, setAuditLogs] = useState([])
  const [loadingLogs, setLoadingLogs] = useState(false)

  const [showConversationDrawer, setShowConversationDrawer] = useState(false)
  const [conversations, setConversations] = useState([])
  const [toastMessage, setToastMessage] = useState(null)

  const messagesRef = useRef(messages)
  const conversationIdRef = useRef(conversationId)

  useEffect(() => {
    messagesRef.current = messages;
    conversationIdRef.current = conversationId;
  }, [messages, conversationId]);

  // Load conversations on mount
  useEffect(() => {
    if (isAuthenticated) {
      setConversations(listConversations() || []);
    }
  }, [isAuthenticated]);

  // Auto-save debounce effect
  useEffect(() => {
    if (messages.length === 0 || !isAuthenticated) return;

    const timer = setTimeout(() => {
      saveConversation(conversationId, messages);
      setConversations(listConversations() || []);
    }, 500);

    return () => clearTimeout(timer);
  }, [messages, conversationId, isAuthenticated]);

  // Sync to local storage on beforeunload
  useEffect(() => {
    const handleBeforeUnload = () => {
      const msgs = messagesRef.current;
      const cId = conversationIdRef.current;
      if (msgs && msgs.length > 0 && isAuthenticated) {
        saveConversation(cId, msgs);
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isAuthenticated]);

  const handleLoginSuccess = (data) => {
    setIsAuthenticated(true)
    setCurrentUser({
      username: localStorage.getItem('username'),
      role: data.role,
      region: data.region
    })
    setMessages([])
  }

  const handleLogout = () => {
    logout()
    setIsAuthenticated(false)
    setCurrentUser({ username: '', role: '', region: '' })
    setMessages([])
    setShowAuditLogs(false)
    setShowConversationDrawer(false)
    setConversations([])
    setToastMessage(null)
    setConversationId(generateUUID())
  }

  const handleNewConversation = async () => {
    try {
      await resetConversation(conversationId)
    } catch (e) {
      console.error("Failed to reset session on server:", e)
    }

    if (messages.length > 0) {
      saveConversation(conversationId, messages);
    }
    pruneOldConversations();
    setConversations(listConversations() || []);

    setConversationId(generateUUID())
    setMessages([])
  }

  const handleSelectConversation = (id) => {
    const loadedMessages = loadConversation(id);
    if (loadedMessages) {
      const displayMessages = loadedMessages.map(msg => ({
        ...msg,
        completedTyping: true
      }));
      setMessages(displayMessages);
      setConversationId(generateUUID());
      setShowConversationDrawer(false);
    }
  }

  const handleDeleteConversation = (id) => {
    const chatToRestore = loadConversation(id);
    const chatsList = listConversations() || [];
    const chatSummary = chatsList.find(c => c.id === id);

    deleteConversation(id);
    setConversations(listConversations() || []);

    if (id === conversationId) {
      handleNewConversation();
    }

    setToastMessage({
      text: "Conversation deleted",
      onUndo: () => {
        saveConversation(id, chatToRestore, chatSummary?.title);
        setConversations(listConversations() || []);
      }
    });
  }

  const handleClearAll = () => {
    setToastMessage(null); // Cancel pending undo
    clearAllConversations();
    setConversations([]);
    handleNewConversation();
  }

  const handleExport = () => {
    const data = exportConversations();
    if (!data) return;
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sybilsql_export_${getTokenUsername()}_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const fetchAuditLogs = async () => {
    setLoadingLogs(true)
    try {
      const logs = await getAuditLogs(25)
      setAuditLogs(logs)
    } catch (error) {
      console.error('Error fetching audit logs:', error)
    } finally {
      setLoadingLogs(false)
    }
  }

  useEffect(() => {
    if (showAuditLogs && currentUser.role === 'admin') {
      fetchAuditLogs()
    }
  }, [showAuditLogs])

  const handleTypewriterComplete = (msgIdx) => {
    setMessages(prev => {
      const next = [...prev];
      if (next[msgIdx]) {
        next[msgIdx] = { ...next[msgIdx], completedTyping: true };
      }
      return next;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = {
      role: 'user',
      content: input + (dryRun ? ' [Dry Run / Plan Only]' : '')
    }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    // Add streaming placeholder message
    setMessages(prev => [
      ...prev,
      {
        role: 'assistant',
        content: '',
        intermediateSteps: [],
        success: true,
        agentRole: currentUser.role,
        dryRun: dryRun,
        completedTyping: false,
        visualizationHint: null,
        suggestions: []
      }
    ]);

    try {
      if (dryRun) {
        // Dry run is non-streaming
        const response = await chatWithAgent(input, dryRun, conversationId)
        setMessages(prev => {
          const newMsgs = [...prev];
          const isRls = !response.success && ((response.error || '').toLowerCase().includes('rls') || (response.error || '').toLowerCase().includes('permission denied'));
          newMsgs[newMsgs.length - 1] = {
            role: response.success ? 'assistant' : 'error',
            content: response.success ? (response.response || response.message || '') : (isRls ? '[❌ RLS INTERCEPT: PRIVILEGE ESCALATION TERMINATED BY KERNEL]\n' + response.error : response.error),
            intermediateSteps: response.intermediate_steps || [],
            success: response.success,
            agentRole: response.role,
            dryRun: response.dry_run,
            completedTyping: true,
            visualizationHint: response.visualization_hint || null,
            suggestions: response.suggestions || [],
            isRls
          };
          return newMsgs;
        });
        return;
      }

      // Streaming execution
      await chatWithAgentStream(input, conversationId, (event) => {
        setMessages(prev => {
          const newMsgs = [...prev];
          const lastMsg = { ...newMsgs[newMsgs.length - 1] };

          if (event.type === 'thought') {
            const steps = [...(lastMsg.intermediateSteps || [])];
            steps.push({
              type: 'action',
              tool: 'Thinking...',
              log: event.content,
              input: ''
            });
            lastMsg.intermediateSteps = steps;
          } else if (event.type === 'tool_start') {
            const steps = [...(lastMsg.intermediateSteps || [])];
            const existingIdx = steps.findLastIndex(s => s.type === 'action' && s.tool === 'Thinking...');
            if (existingIdx >= 0) {
              steps[existingIdx].tool = event.tool;
              steps[existingIdx].input = event.input;
              steps[existingIdx].log = `Thought: Calling tool ${event.tool}\nAction: ${event.tool}\nAction Input: ${event.input}`;
            } else {
              steps.push({
                type: 'action',
                tool: event.tool,
                input: event.input,
                log: `Action: ${event.tool}\nAction Input: ${event.input}`
              });
            }
            lastMsg.intermediateSteps = steps;
          } else if (event.type === 'tool_result') {
            const steps = [...(lastMsg.intermediateSteps || [])];
            let parsedData = null;
            try {
              const parsed = JSON.parse(event.output);
              if (parsed && parsed.data) {
                parsedData = parsed.data;
              }
            } catch (_) { }

            steps.push({
              type: 'observation',
              result: event.output,
              data: parsedData
            });
            lastMsg.intermediateSteps = steps;
          } else if (event.type === 'final_answer') {
            lastMsg.content = event.content;
          } else if (event.type === 'visualization_hint') {
            // LLM-provided chart type hint from [VIZ_HINT] block
            lastMsg.visualizationHint = event.hint;
          } else if (event.type === 'suggestions') {
            // Schema-aware follow-up suggestions
            lastMsg.suggestions = event.suggestions;
          } else if (event.type === 'error') {
            lastMsg.role = 'error';
            const isRls = (event.content || '').toLowerCase().includes('rls') || (event.content || '').toLowerCase().includes('permission denied');
            lastMsg.content = isRls ? '[❌ RLS INTERCEPT: PRIVILEGE ESCALATION TERMINATED BY KERNEL]\n' + event.content : event.content;
            lastMsg.success = false;
            lastMsg.isRls = isRls;
          }

          newMsgs[newMsgs.length - 1] = lastMsg;
          return newMsgs;
        });
      });

      // Once streaming successfully completes, check if we need to set content
      setMessages(prev => {
        const newMsgs = [...prev];
        const lastMsg = newMsgs[newMsgs.length - 1];
        if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
          lastMsg.content = 'Plan completed.';
        }
        return newMsgs;
      });

    } catch (error) {
      console.error('Submission failed:', error);
      setMessages(prev => {
        const newMsgs = [...prev];
        const isRls = (error.message || '').toLowerCase().includes('rls') || (error.message || '').toLowerCase().includes('permission denied');
        const formattedErr = isRls ? '[❌ RLS INTERCEPT: PRIVILEGE ESCALATION TERMINATED BY KERNEL]\n' + error.message : (error.message || 'An error occurred during streaming');
        if (newMsgs.length > 0 && newMsgs[newMsgs.length - 1].role === 'assistant') {
          newMsgs[newMsgs.length - 1] = {
            role: 'error',
            content: formattedErr,
            isRls
          };
        } else {
          newMsgs.push({
            role: 'error',
            content: formattedErr,
            isRls
          });
        }
        return newMsgs;
      });
    } finally {
      setLoading(false)
    }
  }

  const handleSuggestionClick = (question) => {
    if (loading) return;
    setInput(question);
    // Use a short timeout to let React flush the input state update, then auto-submit
    setTimeout(() => {
      document.getElementById('chat-submit-btn')?.click();
    }, 50);
  };

  const getVisualizationSteps = (steps) => {
    if (!steps) return [];
    return steps.map(step => {
      let visualizationData = step.data;
      if (!visualizationData && step.result) {
        try {
          const parsed = JSON.parse(step.result);
          if (parsed.success && parsed.data && Array.isArray(parsed.data) && parsed.data.length > 0) {
            visualizationData = parsed.data;
          }
        } catch (e) { }
      }
      if (visualizationData && Array.isArray(visualizationData) && visualizationData.length > 0) {
        return { ...step, visualizationData };
      }
      return null;
    }).filter(Boolean);
  };

  const renderSidebarSteps = () => {
    // Collect all steps from all messages
    const allSteps = [];
    messages.forEach(msg => {
      if (msg.intermediateSteps) {
        allSteps.push(...msg.intermediateSteps);
      }
    });

    if (allSteps.length === 0) {
      return (
        <div className="empty-logs" style={{ padding: '2rem 1rem', fontSize: '0.85rem' }}>
          Awaiting cognitive input...
        </div>
      );
    }

    return (
      <div className="intermediate-steps">
        {allSteps.map((step, idx) => (
          <div key={idx} className={`step step-${step.type}`}>
            {step.type === 'action' ? (
              <div className="step-action">
                <div className="step-label">
                  <Code className="icon-sm" />
                  [TOOL CALL] {step.tool}
                </div>
                {step.log && (
                  <div className="step-thinking">
                    <div className="step-label" style={{ color: 'var(--text-secondary)' }}>[THOUGHT]</div>
                    {step.log.split('\n').filter(line =>
                      line.includes('Thought:') || line.includes('Action:') || line.includes('Action Input:')
                    ).map((line, i) => (
                      <div key={i} className="thought-line">{line}</div>
                    ))}
                  </div>
                )}
                {step.input && (
                  <div className="step-input">
                    <code>{step.input}</code>
                  </div>
                )}
              </div>
            ) : (
              <div className="step-observation">
                <div className="step-label">
                  <Eye className="icon-sm" />
                  [EXECUTION STATE]
                </div>
                <div className="step-result">
                  <pre>{step.result}</pre>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }


  const renderAuditLogs = () => {
    return (
      <div className="audit-logs-view">
        <div className="audit-header">
          <div className="audit-title">
            <ClipboardList className="icon icon-primary" />
            <h3>System Query Audit Trail</h3>
          </div>
          <button className="btn btn-primary" onClick={fetchAuditLogs} disabled={loadingLogs}>
            {loadingLogs ? 'Refreshing...' : 'Refresh Logs'}
          </button>
        </div>

        {loadingLogs ? (
          <div className="logs-loading">
            <Loader2 className="spinner icon" />
            Loading query audit logs...
          </div>
        ) : auditLogs.length === 0 ? (
          <div className="empty-logs">No query log records found in the database.</div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Role Context</th>
                  <th>Action</th>
                  <th>Executed SQL Query</th>
                  <th>Status</th>
                  <th>Latency</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id} className={log.success ? 'log-row-success' : 'log-row-failed'}>
                    <td className="time-col">{new Date(log.created_at).toLocaleString()}</td>
                    <td>
                      <div className="log-user-info">
                        <span className="log-role-badge">{log.role}</span>
                        {log.region && <span className="log-region-badge">{log.region}</span>}
                      </div>
                    </td>
                    <td><span className={`log-action action-${log.action?.toLowerCase()}`}>{log.action}</span></td>
                    <td className="sql-col">
                      <code>{log.sql_query}</code>
                      {log.error_message && <div className="log-error-msg">{log.error_message}</div>}
                    </td>
                    <td>
                      <span className={`status-indicator ${log.success ? 'status-ok' : 'status-err'}`}>
                        {log.success ? 'Success' : 'Failed'}
                      </span>
                    </td>
                    <td>{log.execution_time_ms}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  // Render Login Form if unauthenticated
  if (!isAuthenticated) {
    return <LoginForm onLoginSuccess={handleLoginSuccess} />
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="header-title">
            <Brain className="icon icon-primary" />
            Sybil-SQL
          </div>

          <div className="user-profile-nav">
            <div className="user-badge">
              <Shield className="icon-primary icon-sm" />
              <span className="badge-username">{currentUser.username}</span>
              <span className="badge-role">{currentUser.role}</span>
              {currentUser.region && (
                <span className="badge-region">
                  <MapPin className="icon-sm" />
                  {currentUser.region}
                </span>
              )}
            </div>

            {currentUser.role === 'admin' && (
              <button
                className={`btn btn-ghost viz-btn ${showAuditLogs ? 'active' : ''}`}
                onClick={() => setShowAuditLogs(!showAuditLogs)}
              >
                <ClipboardList className="icon-sm" />
                {showAuditLogs ? 'Chat Console' : 'Audit Logs'}
              </button>
            )}

            <button className="btn btn-ghost" onClick={() => setShowConversationDrawer(true)}>
              <Menu className="icon-sm" />
              History
            </button>

            <button className="btn btn-ghost" onClick={handleNewConversation}>
              <Brain className="icon-sm" />
              New Conversation
            </button>

            <button className="btn btn-ghost btn-logout" onClick={handleLogout}>
              <LogOut className="icon-sm" />
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className={`main ${showAuditLogs && currentUser.role === 'admin' ? 'full-width' : ''}`}>
        {showAuditLogs && currentUser.role === 'admin' ? (
          renderAuditLogs()
        ) : (
          <>
            <div className="chat-container">
              <div className="messages">
                {messages.length === 0 ? (
                  <div className="empty-state">
                    <Database className="empty-state-icon" />
                    <h3 className="empty-state-title">Secure Natural Language Database Interface</h3>
                    <p className="empty-state-text">Your permissions are locked to role: <strong>{currentUser.role}</strong> {currentUser.region && `(${currentUser.region} region)`}.</p>
                    <p className="empty-state-text">Try: "Show total sales for 2023"</p>
                    <p className="empty-state-text">Or: "List all available tables in the database"</p>
                  </div>
                ) : (
                  messages.map((msg, idx) => {
                    console.log(`💬 [MESSAGE ${idx}] Rendering message:`, msg)
                    return (
                      <div key={idx} className={`message message-${msg.role}`}>
                        {msg.role === 'error' ? (
                          <div className={`alert ${msg.isRls ? 'alert-rls' : 'alert-error'}`}>
                            <AlertCircle className="icon" />
                            <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                          </div>
                        ) : msg.role === 'user' ? (
                          <div className="message-content">
                            {msg.content}
                          </div>
                        ) : (
                          <>
                            {getVisualizationSteps(msg.intermediateSteps).map((vizStep, vIdx) => (
                              <DataVisualizerEnhanced
                                key={vIdx}
                                stepData={vizStep.visualizationData}
                                llmVisualizationHint={msg.visualizationHint}
                              />
                            ))}

                            {idx === messages.length - 1 && loading && !msg.content && (
                              <div className="message-content thinking-indicator" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                                <Loader2 className="icon spinner icon-sm" />
                                Processing cognitive input...
                              </div>
                            )}

                            {msg.content && (
                              <div className="final-answer">
                                <div className="answer-header">
                                  {msg.dryRun ? 'Dry Run Plan (Not Executed):' : 'Final Answer:'}
                                </div>
                                <div className="message-content">
                                  {idx === messages.length - 1 && !msg.completedTyping && msg.content ? (
                                    <Typewriter
                                      text={msg.content}
                                      speed={5}
                                      onComplete={() => handleTypewriterComplete(idx)}
                                    />
                                  ) : (
                                    msg.content
                                  )}
                                </div>
                              </div>
                            )}

                            {/* Suggestion chips - appear after final answer */}
                            {msg.suggestions && msg.suggestions.length > 0 && (
                              <SuggestionChips
                                suggestions={msg.suggestions}
                                onSuggestionClick={handleSuggestionClick}
                              />
                            )}
                          </>
                        )}
                      </div>
                    )
                  })
                )}


              </div>

              <div className="input-area">
                <form onSubmit={handleSubmit} className="input-form">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask a database question..."
                    className={`input ${currentUser.role === 'viewer' ? 'input-viewer' : 'input-active'}`}
                    disabled={loading}
                  />

                  <div className="dry-run-control">
                    <label className="cyber-checkbox-label">
                      <input
                        type="checkbox"
                        checked={dryRun}
                        onChange={(e) => setDryRun(e.target.checked)}
                        disabled={loading}
                      />
                      <span className="cyber-checkbox"></span>
                      <span>Dry Run (Plan Only)</span>
                    </label>
                  </div>

                  <button
                    id="chat-submit-btn"
                    type="submit"
                    disabled={loading || !input.trim()}
                    className="btn btn-primary"
                  >
                    {loading ? (
                      <Loader2 className="icon spinner" />
                    ) : (
                      <Send className="icon" />
                    )}
                    Send
                  </button>
                </form>
              </div>
            </div>

            <div className="sidebar-terminal">
              <div className={`sidebar-header ${loading ? 'active' : ''}`}>
                <Code className="icon-sm" />
                Autonomous Cognitive Core
              </div>
              <div className="sidebar-content">
                {renderSidebarSteps()}
              </div>
            </div>
          </>
        )}
      </main>

      <ConversationList
        isOpen={showConversationDrawer}
        onClose={() => setShowConversationDrawer(false)}
        conversations={conversations}
        currentConversationId={conversationId}
        onSelect={handleSelectConversation}
        onDelete={handleDeleteConversation}
        onClearAll={handleClearAll}
        onExport={handleExport}
      />

      {toastMessage && (
        <Toast
          message={toastMessage.text}
          onUndo={toastMessage.onUndo}
          onDismiss={() => setToastMessage(null)}
          duration={3000}
        />
      )}
    </div>
  )
}

export default App
