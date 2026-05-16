import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom';
import { ArrowRight, Bot, BrainCircuit, CheckCircle2, LayoutDashboard, LockKeyhole, MessageSquareText, Sparkles, UsersRound } from 'lucide-react';
import './styles.css';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8080';

function api(path, options = {}) {
  const token = localStorage.getItem('clarent_token');
  const isPublicAuthRequest = path === '/api/auth/login' || path === '/api/auth/register';
  return fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
