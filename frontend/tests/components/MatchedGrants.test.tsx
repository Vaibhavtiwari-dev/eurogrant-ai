import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MatchedGrants from '@/components/dashboard/MatchedGrants';

const {mockFetch, mockToast} = vi.hoisted(() => ({
  mockFetch: vi.fn(),
  mockToast: {info: vi.fn(), error: vi.fn(), success: vi.fn()},
}));

vi.mock('@/lib/api', () => ({
  apiFetch: (...args: unknown[]) => mockFetch(...args),
}));

vi.mock('sonner', () => ({
  toast: mockToast,
}));

describe('MatchedGrants', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockToast.info.mockClear();
  });

  it('renders the loading state on first render', () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<MatchedGrants refreshKey={0} />);
    expect(screen.getByText(/evaluating match matrices/i)).toBeInTheDocument();
  });

  it('renders the empty state when no matches are returned', async () => {
    mockFetch.mockResolvedValueOnce([]);
    render(<MatchedGrants refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText(/no high-probability matches detected/i)).toBeInTheDocument();
    });
  });

  it('renders a card for each match with score percentage and deadline', async () => {
    mockFetch.mockResolvedValueOnce([
      {
        id: 1,
        organization_id: 1,
        grant_id: 1,
        score: 0.92,
        explanation: 'Strong alignment with your AI focus.',
        created_at: '2026-06-01T00:00:00Z',
        grant: {
          id: 1,
          external_id: 'EIC-1',
          title: 'AI Accelerator Grant',
          description: 'Funding for AI startups in Europe.',
          deadline: '2026-12-31T00:00:00Z',
          funding_range: '€500K - €2M',
          source_url: 'https://example.com',
        },
      },
    ]);
    render(<MatchedGrants refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('AI Accelerator Grant')).toBeInTheDocument();
      expect(screen.getByText('92% Compatible')).toBeInTheDocument();
      expect(screen.getByText(/Strong alignment/i)).toBeInTheDocument();
    });
  });

  it('re-fetches when refreshKey changes', async () => {
    mockFetch.mockResolvedValue([]);
    const {rerender} = render(<MatchedGrants refreshKey={0} />);
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
    rerender(<MatchedGrants refreshKey={1} />);
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  it('replaces alert() with sonner toast on Draft Proposal click', async () => {
    mockFetch.mockResolvedValueOnce([
      {
        id: 1,
        organization_id: 1,
        grant_id: 1,
        score: 0.85,
        explanation: null,
        created_at: '2026-06-01T00:00:00Z',
        grant: {
          id: 1,
          external_id: 'EIC-1',
          title: 'Climate Fund',
          description: 'Climate projects.',
          deadline: '2026-12-31T00:00:00Z',
        },
      },
    ]);
    const user = userEvent.setup();
    render(<MatchedGrants refreshKey={0} />);
    const draftBtn = await screen.findByText(/draft proposal/i);
    await user.click(draftBtn);
    expect(mockToast.info).toHaveBeenCalledWith(
      expect.stringContaining('RAG proposal generation is scheduled')
    );
  });
});
