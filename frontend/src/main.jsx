import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { ArrowRight, Bot, BrainCircuit, CheckCircle2, FileText, Headphones, LayoutDashboard, LockKeyhole, MessageSquareText, PlugZap, Radio, ShieldCheck, Sparkles, Trash2, UserPlus, UsersRound, X } from 'lucide-react';
import './styles.css';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8080';
const WS_URL = API_URL.replace(/^http/, 'ws');

function api(path, options = {}) {
  const token = localStorage.getItem('clarent_token');
  const isPublicAuthRequest = path === '/api/auth/login' || path === '/api/auth/register';
  const isFormData = options.body instanceof FormData;
  return fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token && !isPublicAuthRequest ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers
    }
  }).then(async (response) => {
    const payload = await response.json().catch(() => ({}));
    if (response.status === 401) {
      localStorage.removeItem('clarent_token');
      localStorage.removeItem('clarent_user');
    }
    if (!response.ok) {
      throw new Error(payload.message || 'Request failed');
    }
    return payload;
  });
}

function sendStompFrame(socket, command, headers = {}, body = '') {
  const headerLines = Object.entries(headers).map(([key, value]) => `${key}:${value}`).join('\n');
  socket.send(`${command}\n${headerLines}\n\n${body}\0`);
}

function parseStompFrame(rawFrame) {
  const trimmed = rawFrame.replace(/^\n+/, '');
  if (!trimmed.trim()) {
    return null;
  }

  const separatorIndex = trimmed.indexOf('\n\n');
  const headerBlock = separatorIndex >= 0 ? trimmed.slice(0, separatorIndex) : trimmed;
  const body = separatorIndex >= 0 ? trimmed.slice(separatorIndex + 2) : '';
  const [command, ...headerLines] = headerBlock.split('\n');
  const headers = Object.fromEntries(
    headerLines
      .map((line) => line.split(':'))
      .filter(([key, value]) => key && value)
      .map(([key, ...value]) => [key, value.join(':')])
  );
  return { command, headers, body };
}

function useReveal() {
  useEffect(() => {
    const elements = document.querySelectorAll('[data-reveal]');
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
        }
      });
    }, { threshold: 0.18 });

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);
}

function HomePage() {
  useReveal();
  const visuals = [
    {
      src: 'https://images.unsplash.com/photo-1553877522-43269d4ea984?auto=format&fit=crop&w=1200&q=80',
      title: 'Customer calls become product context'
    },
    {
      src: 'https://images.unsplash.com/photo-1551434678-e076c223a692?auto=format&fit=crop&w=1200&q=80',
      title: 'Teams receive clearer implementation tasks'
    },
    {
      src: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80',
      title: 'Local AI keeps sensitive meetings private'
    }
  ];

  return (
    <main className="site-shell">
      <nav className="nav">
        <Link className="brand" to="/">
          <span className="brand-mark">C</span>
          Clarent
        </Link>
        <div className="nav-actions">
          <Link className="ghost-link" to="/login">Log in</Link>
          <Link className="primary-link" to="/register">Register</Link>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-copy" data-reveal>
          <p className="eyebrow">AI meeting intelligence for product teams</p>
          <h1>Clarent turns customer conversations into clearer development work.</h1>
          <p className="hero-text">
            A local-first assistant that listens to consented meetings, captures the client voice,
            and helps product managers preserve context before it disappears.
          </p>
          <div className="hero-actions">
            <Link className="primary-link large" to="/register">
              Start with Clarent <ArrowRight size={18} />
            </Link>
            <Link className="ghost-link large" to="/login">I already have access</Link>
          </div>
        </div>
        <div className="hero-stage" data-reveal>
          <div className="meeting-card floating">
            <div className="meeting-top">
              <span className="live-dot" />
              Live customer meeting
            </div>
            <div className="wave-row">
              <span /><span /><span /><span /><span /><span />
            </div>
            <div className="question-card">
              <Sparkles size={18} />
              What exact approval rules should this workflow support?
            </div>
          </div>
          <div className="task-strip floating slow">
            <CheckCircle2 size={18} />
            Draft task generated: Add configurable approval matrix
          </div>
        </div>
      </section>

      <section className="image-band">
        {visuals.map((visual) => (
          <article className="photo-tile" key={visual.title} data-reveal>
            <img src={visual.src} alt={visual.title} />
            <p>{visual.title}</p>
          </article>
        ))}
      </section>

      <section className="feature-grid">
        <Feature icon={<Bot />} title="Meeting bot" text="Joins approved calls and streams transcript chunks to the backend." />
        <Feature icon={<BrainCircuit />} title="Local AI" text="Uses local speech recognition and later local reasoning models for privacy." />
        <Feature icon={<MessageSquareText />} title="Clarifying questions" text="Surfaces ambiguity while the customer is still available." />
        <Feature icon={<LayoutDashboard />} title="Task dashboard" text="Managers review generated work before assigning it to the team." />
      </section>
    </main>
  );
}

function Feature({ icon, title, text }) {
  return (
    <article className="feature" data-reveal>
      <div className="feature-icon">{icon}</div>
      <h2>{title}</h2>
      <p>{text}</p>
    </article>
  );
}

function AuthLayout({ mode }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    fullName: '',
    email: '',
    password: '',
    role: 'MANAGER'
  });
  const [error, setError] = useState('');
  const isRegister = mode === 'register';

  async function submit(event) {
    event.preventDefault();
    setError('');
    try {
      const payload = isRegister
        ? form
        : { email: form.email, password: form.password };
      const data = await api(`/api/auth/${isRegister ? 'register' : 'login'}`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      localStorage.setItem('clarent_token', data.token);
      localStorage.setItem('clarent_user', JSON.stringify(data));
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main className="auth-page">
      <Link className="brand auth-brand" to="/">
        <span className="brand-mark">C</span>
        Clarent
      </Link>
      <section className="auth-panel">
        <div>
          <p className="eyebrow">{isRegister ? 'Create workspace access' : 'Welcome back'}</p>
          <h1>{isRegister ? 'Register for Clarent' : 'Log in to Clarent'}</h1>
        </div>
        <form onSubmit={submit} className="auth-form">
          {isRegister && (
            <label>
              Full name
              <input value={form.fullName} onChange={(event) => setForm({ ...form, fullName: event.target.value })} required />
            </label>
          )}
          <label>
            Email
            <input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required />
          </label>
          <label>
            Password
            <input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required minLength={8} />
          </label>
          {isRegister && (
            <div className="role-picker">
              <button type="button" className={form.role === 'MANAGER' ? 'selected' : ''} onClick={() => setForm({ ...form, role: 'MANAGER' })}>
                <LockKeyhole size={18} /> Manager
              </button>
              <button type="button" className={form.role === 'TEAM_MEMBER' ? 'selected' : ''} onClick={() => setForm({ ...form, role: 'TEAM_MEMBER' })}>
                <UsersRound size={18} /> Team member
              </button>
            </div>
          )}
          {error && <p className="form-error">{error}</p>}
          <button className="submit-button" type="submit">{isRegister ? 'Create account' : 'Log in'}</button>
        </form>
        <p className="switch-auth">
          {isRegister ? 'Already registered?' : 'Need an account?'}
          <Link to={isRegister ? '/login' : '/register'}>{isRegister ? 'Log in' : 'Register'}</Link>
        </p>
      </section>
    </main>
  );
}

function Dashboard() {
  const user = JSON.parse(localStorage.getItem('clarent_user') || 'null');
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <main className="dashboard">
      <nav className="nav compact">
        <Link className="brand" to="/">
          <span className="brand-mark">C</span>
          Clarent
        </Link>
        <button className="ghost-button" onClick={() => {
          localStorage.removeItem('clarent_token');
          localStorage.removeItem('clarent_user');
          window.location.href = '/';
        }}>Log out</button>
      </nav>
      <section className="dashboard-grid">
        <div>
          <p className="eyebrow">{user.role === 'MANAGER' ? 'Manager dashboard' : 'Team member dashboard'}</p>
          <h1>Hello, {user.fullName}</h1>
          <p className="hero-text">
            {user.role === 'MANAGER'
              ? 'Your next workspace tools will manage meetings, live questions, transcripts, and generated tasks.'
              : 'Your next workspace tools will focus on assigned tasks, implementation context, and status updates.'}
          </p>
        </div>
        <div className="dashboard-card">
          <LayoutDashboard size={22} />
          <h2>Authentication ready</h2>
          <p>JWT and role-based routing are wired. Workspace and meeting modules come next.</p>
        </div>
      </section>
      <section className="manager-actions">
        {user.role === 'MANAGER' ? (
          <>
            <Link className="action-panel" to="/meeting-assistant">
              <div className="action-icon"><Headphones size={22} /></div>
              <div>
                <p className="eyebrow">Live workspace</p>
                <h2>Meeting assistant</h2>
                <p>Connect Clarent to a customer meeting and watch the transcript stream into your workspace.</p>
              </div>
              <ArrowRight size={20} />
            </Link>
            <Link className="action-panel" to="/manage-team">
              <div className="action-icon"><UsersRound size={22} /></div>
              <div>
                <p className="eyebrow">Team workspace</p>
                <h2>Manage team</h2>
                <p>Add or remove team members and prepare shared documents for generated meeting work.</p>
              </div>
              <ArrowRight size={20} />
            </Link>
          </>
        ) : (
          <Link className="action-panel" to="/team">
            <div className="action-icon"><UsersRound size={22} /></div>
            <div>
              <p className="eyebrow">Team workspace</p>
              <h2>View team</h2>
              <p>See the people in your Clarent team and the shared workspace you belong to.</p>
            </div>
            <ArrowRight size={20} />
          </Link>
        )}
      </section>
    </main>
  );
}

const PLATFORM_LABELS = {
  TEAMS: 'Microsoft Teams',
  GOOGLE_MEET: 'Google Meet',
  ZOOM: 'Zoom'
};

function MeetingAssistantPage() {
  const user = JSON.parse(localStorage.getItem('clarent_user') || 'null');
  const [modalOpen, setModalOpen] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState('');
  const [meeting, setMeeting] = useState(null);
  const [segments, setSegments] = useState([]);
  const [questionSets, setQuestionSets] = useState([]);
  const [socketState, setSocketState] = useState('idle');
  const [connectionMessage, setConnectionMessage] = useState('');
  const [questionError, setQuestionError] = useState('');
  const [questionNotice, setQuestionNotice] = useState('');
  const [generatingSegmentId, setGeneratingSegmentId] = useState(null);
  const [markingQuestionId, setMarkingQuestionId] = useState(null);
  const [form, setForm] = useState({
    platform: 'TEAMS',
    inviteLink: ''
  });

  useEffect(() => {
    if (!meeting?.meetingId) {
      return undefined;
    }

    let closed = false;
    const socket = new WebSocket(`${WS_URL}/ws`);
    setSocketState('connecting');

    socket.addEventListener('open', () => {
      sendStompFrame(socket, 'CONNECT', {
        'accept-version': '1.2',
        'heart-beat': '10000,10000'
      });
    });

    socket.addEventListener('message', (event) => {
      String(event.data).split('\0').forEach((rawFrame) => {
        const frame = parseStompFrame(rawFrame);
        if (!frame) {
          return;
        }

        if (frame.command === 'CONNECTED') {
          setSocketState('connected');
          sendStompFrame(socket, 'SUBSCRIBE', {
            id: `transcript-${meeting.meetingId}`,
            destination: meeting.transcriptTopic
          });
          sendStompFrame(socket, 'SUBSCRIBE', {
            id: `status-${meeting.meetingId}`,
            destination: meeting.statusTopic
          });
          setConnectionMessage('Clarent is connecting to the meeting.');
        }

        if (frame.command === 'MESSAGE' && frame.body) {
          const payload = JSON.parse(frame.body);
          if (frame.headers.destination === meeting.transcriptTopic) {
            setSegments((current) => [...current, payload]);
          }
          if (frame.headers.destination === meeting.statusTopic) {
            setMeeting((current) => current ? { ...current, status: payload.status, message: payload.message } : current);
            setConnectionMessage(payload.message);
          }
        }
      });
    });

    socket.addEventListener('close', () => {
      if (!closed) {
        setSocketState('closed');
      }
    });

    socket.addEventListener('error', () => {
      setSocketState('error');
      setConnectionMessage('The live transcript socket could not connect.');
    });

    return () => {
      closed = true;
      if (socket.readyState === WebSocket.OPEN) {
        sendStompFrame(socket, 'DISCONNECT', { receipt: `disconnect-${meeting.meetingId}` });
      }
      socket.close();
    };
  }, [meeting?.meetingId]);

  useEffect(() => {
    if (!meeting?.meetingId) {
      setQuestionSets([]);
      return;
    }

    api(`/api/manager/meeting-assistant/${meeting.meetingId}/questions`)
      .then(setQuestionSets)
      .catch((err) => setQuestionError(err.message));
  }, [meeting?.meetingId]);

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== 'MANAGER') {
    return <Navigate to="/dashboard" replace />;
  }

  async function connectMeeting(event) {
    event.preventDefault();
    setConnecting(true);
    setError('');
    try {
      const data = await api('/api/manager/meeting-assistant/connect', {
        method: 'POST',
        body: JSON.stringify(form)
      });
      setMeeting(data);
      setSegments([]);
      setQuestionSets([]);
      setConnectionMessage(data.message);
      setModalOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setConnecting(false);
    }
  }

  async function generateQuestions(segment) {
    setGeneratingSegmentId(segment.id);
    setQuestionError('');
    setQuestionNotice('');
    try {
      const data = await api(`/api/manager/meeting-assistant/${meeting.meetingId}/transcript/${segment.id}/questions`, {
        method: 'POST'
      });
      setQuestionSets((current) => [data, ...current.filter((item) => item.id !== data.id)]);
      setQuestionNotice('Questions generated for the selected transcript.');
    } catch (err) {
      setQuestionError(err.message);
    } finally {
      setGeneratingSegmentId(null);
    }
  }

  async function markQuestionAsked(questionId) {
    setMarkingQuestionId(questionId);
    setQuestionError('');
    setQuestionNotice('');
    try {
      const data = await api(`/api/manager/meeting-assistant/${meeting.meetingId}/questions/${questionId}/asked`, {
        method: 'POST'
      });
      setQuestionSets((current) => current.map((suggestion) => ({
        ...suggestion,
        questions: suggestion.questions.map((question) => question.id === data.id ? data : question)
      })));
      setQuestionNotice('Question marked as asked.');
    } catch (err) {
      setQuestionError(err.message);
    } finally {
      setMarkingQuestionId(null);
    }
  }

  return (
    <main className="assistant-page">
      <nav className="nav compact">
        <Link className="brand" to="/dashboard">
          <span className="brand-mark">C</span>
          Clarent
        </Link>
        <div className="nav-actions">
          <Link className="ghost-link" to="/dashboard">Dashboard</Link>
          <button className="primary-link" onClick={() => setModalOpen(true)}>
            <PlugZap size={18} /> Connect
          </button>
        </div>
      </nav>

      <section className="assistant-layout">
        <div className="assistant-copy">
          <p className="eyebrow">Manager workspace</p>
          <h1>Meeting assistant</h1>
          <p className="hero-text">
            Connect Clarent to a live meeting. The transcript stays locked until a meeting session is created,
            then updates as the local bot sends speech chunks back to the backend.
          </p>
        </div>
        <aside className="assistant-status">
          <div className="status-row">
            <Radio size={18} />
            <span>{meeting ? meeting.status.replaceAll('_', ' ') : 'Not connected'}</span>
          </div>
          <p>{connectionMessage || 'Choose a meeting platform and invite link to start the assistant.'}</p>
          {meeting && <small>{PLATFORM_LABELS[meeting.platform]} session</small>}
        </aside>
      </section>

      <section className="assistant-workspace">
        <section className={`transcript-stage ${meeting ? '' : 'locked'}`}>
          <div className="transcript-toolbar">
            <div>
              <p className="eyebrow">Live transcript</p>
              <h2>{meeting ? 'Clarent transcript stream' : 'Waiting for Clarent'}</h2>
            </div>
            <span className={`socket-pill ${socketState}`}>{socketState}</span>
          </div>

          {!meeting && (
            <div className="locked-state">
              <LockKeyhole size={28} />
              <h3>Transcript locked</h3>
              <p>Connect Clarent to a Teams, Google Meet, or Zoom invite link to unlock this screen.</p>
              <button className="primary-link" onClick={() => setModalOpen(true)}>
                <PlugZap size={18} /> Connect
              </button>
            </div>
          )}

          {meeting && segments.length === 0 && (
            <div className="empty-transcript">
              <ShieldCheck size={26} />
              <h3>Clarent is standing by</h3>
              <p>Once the bot is admitted and hears speech, transcript chunks will appear here.</p>
            </div>
          )}

          {segments.length > 0 && (
            <div className="transcript-list">
              {segments.map((segment) => (
                <article className="transcript-line" key={segment.id}>
                  <time>{new Date(segment.receivedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time>
                  <p>{segment.speaker && <strong>{segment.speaker}: </strong>}{segment.text}</p>
                  <div className="segment-actions">
                    {segment.language && <span>{segment.language}</span>}
                    <button
                      className="ghost-button mini-button"
                      disabled={generatingSegmentId === segment.id}
                      onClick={() => generateQuestions(segment)}
                    >
                      <Sparkles size={15} /> {generatingSegmentId === segment.id ? 'Generating' : 'Questions'}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className={`questions-stage ${meeting ? '' : 'locked'}`}>
          <div className="questions-toolbar">
            <div>
              <p className="eyebrow">Clarifying questions</p>
              <h2>Question workspace</h2>
            </div>
            <span className="socket-pill connected">{questionSets.length} sets</span>
          </div>

          {questionError && <p className="form-error question-message">{questionError}</p>}
          {questionNotice && <p className="form-success question-message">{questionNotice}</p>}

          {!meeting && (
            <div className="empty-transcript compact-empty">
              <BrainCircuit size={28} />
              <h3>No meeting selected</h3>
              <p>Question generation unlocks after Clarent connects to a meeting.</p>
            </div>
          )}

          {meeting && questionSets.length === 0 && (
            <div className="empty-transcript compact-empty">
              <Sparkles size={28} />
              <h3>No generated questions yet</h3>
              <p>Select a useful transcript chunk and generate 3 questions from the team context document.</p>
            </div>
          )}

          {questionSets.length > 0 && (
            <div className="question-set-list">
              {questionSets.map((suggestion) => (
                <article className="question-set" key={suggestion.id}>
                  <div className="question-set-header">
                    <div>
                      <p className="eyebrow">{new Date(suggestion.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                      <h3>From transcript</h3>
                    </div>
                    <span>{suggestion.modelName}</span>
                  </div>
                  <blockquote>{suggestion.transcriptText}</blockquote>
                  <div className="question-options">
                    {suggestion.questions.map((question) => (
                      <button
                        className={`question-choice ${question.asked ? 'asked' : ''}`}
                        disabled={question.asked || markingQuestionId === question.id}
                        key={question.id}
                        onClick={() => markQuestionAsked(question.id)}
                      >
                        <span>{question.text}</span>
                        <small>{question.asked ? 'Asked' : 'Mark asked'}</small>
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </section>

      {modalOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="connect-modal" role="dialog" aria-modal="true" aria-labelledby="connect-title">
            <button className="icon-button" aria-label="Close connect dialog" onClick={() => setModalOpen(false)}>
              <X size={18} />
            </button>
            <div>
              <p className="eyebrow">New session</p>
              <h2 id="connect-title">Connect Clarent</h2>
            </div>
            <form className="auth-form" onSubmit={connectMeeting}>
              <label>
                Platform
                <select value={form.platform} onChange={(event) => setForm({ ...form, platform: event.target.value })}>
                  <option value="TEAMS">Microsoft Teams</option>
                  <option value="GOOGLE_MEET">Google Meet</option>
                  <option value="ZOOM">Zoom</option>
                </select>
              </label>
              <label>
                Invite link
                <input
                  type="url"
                  value={form.inviteLink}
                  onChange={(event) => setForm({ ...form, inviteLink: event.target.value })}
                  placeholder="https://..."
                  required
                />
              </label>
              {error && <p className="form-error">{error}</p>}
              <button className="submit-button" disabled={connecting} type="submit">
                {connecting ? 'Connecting...' : 'Connect'}
              </button>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}

function TeamPage({ mode }) {
  const user = JSON.parse(localStorage.getItem('clarent_user') || 'null');
  const [team, setTeam] = useState(null);
  const [email, setEmail] = useState('');
  const [documentFile, setDocumentFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const isManagerMode = mode === 'manage';

  useEffect(() => {
    if (!user) {
      return;
    }
    if (isManagerMode && user.role !== 'MANAGER') {
      return;
    }

    const endpoint = isManagerMode ? '/api/manager/team' : '/api/member/team';
    setLoading(true);
    api(endpoint)
      .then(setTeam)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [isManagerMode]);

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (isManagerMode && user.role !== 'MANAGER') {
    return <Navigate to="/dashboard" replace />;
  }

  async function addMember(event) {
    event.preventDefault();
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const data = await api('/api/manager/team/members', {
        method: 'POST',
        body: JSON.stringify({ email })
      });
      setTeam(data);
      setEmail('');
      setNotice('Team member added.');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function removeMember(memberId) {
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const data = await api(`/api/manager/team/members/${memberId}`, {
        method: 'DELETE'
      });
      setTeam(data);
      setNotice('Team member removed.');
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function uploadDocument(event) {
    event.preventDefault();
    if (!documentFile) {
      setError('Choose a .txt, .pdf, .doc, or .docx file first.');
      return;
    }

    setUploading(true);
    setError('');
    setNotice('');
    try {
      const formData = new FormData();
      formData.append('file', documentFile);
      const data = await api('/api/manager/team/document', {
        method: 'POST',
        body: formData
      });
      setTeam(data);
      setDocumentFile(null);
      event.target.reset();
      setNotice('Team context document updated.');
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  const document = team?.document;

  return (
    <main className="assistant-page">
      <nav className="nav compact">
        <Link className="brand" to="/dashboard">
          <span className="brand-mark">C</span>
          Clarent
        </Link>
        <Link className="ghost-link" to="/dashboard">Dashboard</Link>
      </nav>

      <section className="assistant-layout">
        <div className="assistant-copy">
          <p className="eyebrow">{isManagerMode ? 'Manager workspace' : 'Team workspace'}</p>
          <h1>{isManagerMode ? 'Manage team' : 'View team'}</h1>
          <p className="hero-text">
            {isManagerMode
              ? 'Keep your Clarent workspace tied to the people who will receive tasks and review AI-generated documents.'
              : 'See the Clarent workspace you belong to and the people who will share generated meeting context.'}
          </p>
        </div>
        <aside className="assistant-status">
          <div className="status-row">
            <UsersRound size={18} />
            <span>{team?.teamName || 'No team yet'}</span>
          </div>
          <p>{team?.managerName ? `Managed by ${team.managerName}.` : 'You have not been added to a team yet.'}</p>
          <small>{team?.members?.length || 0} member{team?.members?.length === 1 ? '' : 's'}</small>
        </aside>
      </section>

      <section className="team-layout">
        {isManagerMode && (
          <aside className="team-panel">
            <div>
              <p className="eyebrow">Add member</p>
              <h2>Invite by account email</h2>
            </div>
            <form className="team-form" onSubmit={addMember}>
              <label>
                Team member email
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="member@company.com"
                  required
                />
              </label>
              <button className="submit-button" disabled={saving} type="submit">
                <UserPlus size={18} /> Add member
              </button>
            </form>
            <div className="document-box">
              <div>
                <p className="eyebrow">Team documents</p>
                <h2>Product context</h2>
                <p>The assistant will use this later when generating clarifying questions.</p>
              </div>
              {document && (
                <div className="document-meta">
                  <FileText size={18} />
                  <div>
                    <strong>{document.fileName}</strong>
                    <span>{(document.sizeBytes / 1024).toFixed(1)} KB · updated {new Date(document.updatedAt).toLocaleDateString()}</span>
                  </div>
                </div>
              )}
              <form className="team-form" onSubmit={uploadDocument}>
                <label>
                  Context document
                  <input
                    type="file"
                    accept=".txt,.pdf,.doc,.docx,text/plain,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    onChange={(event) => setDocumentFile(event.target.files?.[0] || null)}
                  />
                </label>
                <button className="ghost-button document-button" disabled={uploading} type="submit">
                  <FileText size={18} /> {document ? 'Replace document' : 'Upload document'}
                </button>
              </form>
            </div>
          </aside>
        )}

        <section className="team-panel members-panel">
          <div className="team-panel-header">
            <div>
              <p className="eyebrow">People</p>
              <h2>{loading ? 'Loading team' : team?.teamName || 'No team assigned'}</h2>
            </div>
            <span className="socket-pill connected">{team?.members?.length || 0} users</span>
          </div>

          {error && <p className="form-error">{error}</p>}
          {notice && <p className="form-success">{notice}</p>}
          {document && !isManagerMode && (
            <div className="document-meta member-document">
              <FileText size={18} />
              <div>
                <strong>{document.fileName}</strong>
                <span>Team context document updated {new Date(document.updatedAt).toLocaleDateString()}</span>
              </div>
            </div>
          )}

          {!loading && (!team?.members || team.members.length === 0) && (
            <div className="empty-transcript compact-empty">
              <UsersRound size={26} />
              <h3>No team members yet</h3>
              <p>{isManagerMode ? 'Add registered team member accounts by email.' : 'Ask your manager to add your account to their team.'}</p>
            </div>
          )}

          {team?.members?.length > 0 && (
            <div className="member-list">
              {team.members.map((member) => (
                <article className="member-row" key={member.userId}>
                  <div className="member-avatar">{member.fullName.slice(0, 1).toUpperCase()}</div>
                  <div>
                    <h3>{member.fullName}</h3>
                    <p>{member.email}</p>
                  </div>
                  <span className="role-chip">{member.manager ? 'Manager' : 'Team member'}</span>
                  {isManagerMode && !member.manager && (
                    <button className="icon-button inline" aria-label={`Remove ${member.fullName}`} disabled={saving} onClick={() => removeMember(member.userId)}>
                      <Trash2 size={17} />
                    </button>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<AuthLayout mode="login" />} />
        <Route path="/register" element={<AuthLayout mode="register" />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/meeting-assistant" element={<MeetingAssistantPage />} />
        <Route path="/manage-team" element={<TeamPage mode="manage" />} />
        <Route path="/team" element={<TeamPage mode="view" />} />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
