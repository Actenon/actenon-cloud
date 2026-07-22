/**
 * App shell — top bar, left nav, footer.
 *
 * Brand voice: declarative, security-serious, en-GB.
 * Role disclaimer: "Control plane — verification happens at the kernel edge."
 */
import { useState } from 'react';
import { NavLink, Outlet, useRouteError } from 'react-router-dom';
import { useAuthSession, useApprovals } from '../api/hooks';
import { setToken, clearToken } from '../api/client';
import { Badge, Button } from '../design/primitives';

const INVARIANT = 'No valid proof, no execution.';

export function AppShell() {
  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <TopBar />
      <div className="flex flex-1">
        <SideNav />
        <main id="main" className="flex-1 px-6 py-6 lg:px-10 lg:py-8 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
      <Footer />
    </div>
  );
}

// ── TopBar ──────────────────────────────────────────────────────────

function TopBar() {
  const sessionQuery = useAuthSession();
  const [showAuth, setShowAuth] = useState(false);
  const [tokenInput, setTokenInput] = useState('');

  const session = sessionQuery.data;
  const isAuthenticated = !sessionQuery.isError && !!session;

  const handleSetToken = () => {
    if (tokenInput.trim()) {
      setToken(tokenInput.trim());
      setTokenInput('');
      setShowAuth(false);
      sessionQuery.refetch();
    }
  };

  const handleClearToken = () => {
    clearToken();
    sessionQuery.refetch();
  };

  return (
    <header className="border-b border-edge bg-surface sticky top-0 z-30">
      <div className="flex items-center justify-between px-6 lg:px-10 h-14">
        {/* Wordmark + invariant */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div
              className="h-7 w-7 rounded-md flex items-center justify-center font-bold text-paper text-sm"
              style={{ background: 'linear-gradient(135deg, rgb(var(--c-accent)), rgb(var(--c-allow)))' }}
              aria-hidden="true"
            >
              A
            </div>
            <div className="leading-tight">
              <div className="text-sm font-bold text-ink">Actenon Cloud</div>
              <div className="text-2xs text-muted uppercase tracking-wide">Control Plane</div>
            </div>
          </div>
          <span className="hidden md:block text-2xs text-muted italic" aria-label="Invariant">
            {INVARIANT}
          </span>
        </div>

        {/* Right: tenant + auth */}
        <div className="flex items-center gap-3">
          {isAuthenticated && session && (
            <>
              {session.tenant_access.length > 0 && (
                <Badge tone="muted" className="hidden sm:inline-flex">
                  {session.tenant_access[0].tenant_id}
                </Badge>
              )}
              <span className="text-2xs text-muted hidden lg:inline">
                {session.display_name}
              </span>
              <Button size="sm" variant="ghost" onClick={handleClearToken}>
                Sign out
              </Button>
            </>
          )}
          {!isAuthenticated && (
            <Button size="sm" variant="secondary" onClick={() => setShowAuth((s) => !s)}>
              Dev auth
            </Button>
          )}
        </div>
      </div>

      {/* Dev auth bar */}
      {showAuth && !isAuthenticated && (
        <div className="border-t border-edge bg-surface-2 px-6 py-3 flex items-center gap-2 flex-wrap">
          <label htmlFor="dev-token" className="text-2xs font-semibold uppercase tracking-wide text-muted">
            Bearer token
          </label>
          <input
            id="dev-token"
            type="password"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSetToken()}
            placeholder="Paste a dev operator token"
            className="flex-1 min-w-[200px] h-7 px-2 text-2xs font-mono bg-surface border border-edge rounded-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <Button size="sm" variant="primary" onClick={handleSetToken}>
            Set token
          </Button>
          <span className="text-2xs text-muted">
            Obtain via <code className="font-mono">POST /api/v1/auth/dev/operator-token</code>
          </span>
        </div>
      )}
    </header>
  );
}

// ── SideNav ─────────────────────────────────────────────────────────

function SideNav() {
  // Count badges
  const approvalsQuery = useApprovals({ status: 'pending' });
  const pendingCount = approvalsQuery.data?.length ?? 0;

  const navItems = [
    { to: '/', label: 'Trust Surface', end: true },
    { to: '/review', label: 'Review Queue', badge: pendingCount },
    { to: '/ledger', label: 'Action Ledger' },
    { to: '/styleguide', label: 'Styleguide' },
  ];

  return (
    <nav
      className="w-52 shrink-0 border-r border-edge bg-surface py-4 hidden md:block"
      aria-label="Primary"
    >
      <ul className="space-y-0.5 px-3">
        {navItems.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors ${
                  isActive
                    ? 'bg-accent/10 text-accent font-semibold'
                    : 'text-muted hover:text-ink hover:bg-surface-2'
                }`
              }
            >
              <span>{item.label}</span>
              {item.badge != null && item.badge > 0 && (
                <span className="font-mono text-2xs bg-pending/15 text-pending px-1.5 py-0.5 rounded-xs">
                  {item.badge}
                </span>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

// ── Footer ──────────────────────────────────────────────────────────

function Footer() {
  return (
    <footer className="border-t border-edge bg-surface px-6 lg:px-10 py-3">
      <div className="flex items-center justify-between gap-4 flex-wrap text-2xs text-muted">
        <span>
          Control plane &mdash; verification happens at the kernel edge.
        </span>
        <span>
          The agent may ask. The protected boundary decides.
        </span>
      </div>
    </footer>
  );
}

// ── Error boundary ──────────────────────────────────────────────────

export function RootErrorBoundary() {
  const error = useRouteError();
  const message = error instanceof Error ? error.message : 'An unexpected error occurred.';
  return (
    <div className="flex flex-col items-center justify-center py-20 px-6 text-center">
      <h1 className="text-lg font-semibold text-ink mb-2">Something went wrong</h1>
      <p className="text-sm text-muted max-w-md">{message}</p>
      <Button
        variant="secondary"
        size="sm"
        className="mt-4"
        onClick={() => window.location.reload()}
      >
        Reload
      </Button>
    </div>
  );
}
