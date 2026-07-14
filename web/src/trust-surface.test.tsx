/**
 * Smoke test: Trust Surface renders the demo DENY with failure_code,
 * mutation-refused diff, and chain-verify badge.
 *
 * Uses the canned demo data (no API calls).
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TrustSurface } from './screens/TrustSurface';

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter
        initialEntries={['/']}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        {ui}
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Trust Surface', () => {
  it('renders the entry state with a demo replay button', () => {
    renderWithProviders(<TrustSurface />);
    expect(screen.getByText('Replay the demo incident')).toBeInTheDocument();
  });

  it('renders a DENY verdict with ACTION_MISMATCH after replaying the demo', () => {
    renderWithProviders(<TrustSurface />);

    // Click the demo button
    fireEvent.click(screen.getByText('Replay the demo incident'));

    // The verdict should show REFUSED (appears in verdict + mutation-refused badge)
    const refused = screen.getAllByText('REFUSED');
    expect(refused.length).toBeGreaterThan(0);

    // The failure code should be visible (in verdict + mutation-refused)
    const codes = screen.getAllByText('ACTION_MISMATCH');
    expect(codes.length).toBeGreaterThan(0);

    // The mutation-refused diff should show both amounts.
    // Amounts appear in multiple places (boundary + diff), so use getAllByText.
    const authorised = screen.getAllByText(/\$20\.00/);
    expect(authorised.length).toBeGreaterThan(0);
    const attempted = screen.getAllByText(/\$99,999\.00/);
    expect(attempted.length).toBeGreaterThan(0);
  });

  it('shows the chain-verify badge and is honest in demo mode (no fake green tick)', () => {
    renderWithProviders(<TrustSurface />);
    fireEvent.click(screen.getByText('Replay the demo incident'));

    // The chain-verify badge should be present
    const verifyButton = screen.getByRole('button', { name: /verify/i });
    expect(verifyButton).toBeInTheDocument();

    // Click to verify — in demo mode (no backend), it must show "Preview",
    // NOT a fake "verified" green tick. This is the honesty guarantee.
    fireEvent.click(verifyButton);
    expect(screen.getByText(/Preview/i)).toBeInTheDocument();
    // Crucially, the fake "CHAIN VERIFIED" must never appear in demo mode.
    expect(screen.queryByText('CHAIN VERIFIED')).not.toBeInTheDocument();
  });

  it('renders the evaluation trace table', () => {
    renderWithProviders(<TrustSurface />);
    fireEvent.click(screen.getByText('Replay the demo incident'));

    // The evaluation trace should show check names
    expect(screen.getByText('grant_signature')).toBeInTheDocument();
    expect(screen.getByText('pccb_bound')).toBeInTheDocument();
  });
});
