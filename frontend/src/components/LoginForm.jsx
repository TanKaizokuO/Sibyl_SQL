import { useState } from 'react'
import { Brain, Lock, User, Loader2, AlertCircle } from 'lucide-react'
import { login } from '../api/agent'
import './LoginForm.css'

export default function LoginForm({ onLoginSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) {
      setError('Please fill in all fields')
      return
    }

    setError('')
    setLoading(true)

    try {
      const data = await login(username, password)
      onLoginSuccess(data)
    } catch (err) {
      setError(
        err.response?.data?.detail || 
        err.message || 
        'Invalid username or password'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-wrapper">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo-container">
            <Brain className="login-logo" />
          </div>
          <h2 className="login-title">Sybil-SQL Security</h2>
          <p className="login-subtitle">Cognitive Database Agent</p>
        </div>

        {error && (
          <div className="login-error-alert">
            <AlertCircle className="icon-sm" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label htmlFor="username">Username</label>
            <div className="input-with-icon">
              <User className="input-icon" />
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                disabled={loading}
                required
              />
            </div>
          </div>

          <div className="input-group">
            <label htmlFor="password">Password</label>
            <div className="input-with-icon">
              <Lock className="input-icon" />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                disabled={loading}
                required
              />
            </div>
          </div>

          <button type="submit" className="login-btn btn btn-primary" disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="spinner icon-sm" />
                <span>Signing in...</span>
              </>
            ) : (
              <span>Sign In</span>
            )}
          </button>
        </form>

        <div className="login-footer">
          <p>Demo accounts available:</p>
          <ul>
            <li><code>admin_user</code> / <code>admin123</code> (Admin)</li>
            <li><code>north_manager</code> / <code>manager123</code> (Manager - North)</li>
            <li><code>viewer_user</code> / <code>viewer123</code> (Viewer)</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
