import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import DocumentList from '@/components/DocumentList';

// Mock the api helper so we don't exercise the network or Zod in unit tests.
const mockFetch = vi.fn();
vi.mock('@/lib/api', () => ({
  apiFetch: (...args: unknown[]) => mockFetch(...args),
}));

// Stub next-intl translations/format so the component renders.
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string, vars?: Record<string, unknown>) =>
    vars ? `${key}:${JSON.stringify(vars)}` : key,
  useFormatter: () => ({
    dateTime: (_d: Date) => 'formatted-date',
  }),
}));

describe('DocumentList', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('renders the loading spinner on first render', () => {
    mockFetch.mockReturnValue(new Promise(() => {})); // never resolves
    render(<DocumentList refreshKey={0} />);
    expect(screen.getByRole('status', { name: /loading documents/i })).toBeInTheDocument();
  });

  it('renders the empty state when the API returns an empty list', async () => {
    mockFetch.mockResolvedValueOnce([]);
    render(<DocumentList refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('empty')).toBeInTheDocument();
    });
  });

  it('renders a card per document returned by the API', async () => {
    mockFetch.mockResolvedValueOnce([
      { id: 1, file_name: 'pitch.pdf', status: 'processed', created_at: '2026-06-01T00:00:00Z' },
      { id: 2, file_name: 'overview.docx', status: 'pending', created_at: '2026-06-02T00:00:00Z' },
    ]);
    render(<DocumentList refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('pitch.pdf')).toBeInTheDocument();
      expect(screen.getByText('overview.docx')).toBeInTheDocument();
    });
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });

  it('shows the correct status label for each document state', async () => {
    mockFetch.mockResolvedValueOnce([
      { id: 1, file_name: 'done.pdf', status: 'processed', created_at: '2026-06-01T00:00:00Z' },
      { id: 2, file_name: 'broken.pdf', status: 'failed', created_at: '2026-06-01T00:00:00Z' },
      { id: 3, file_name: 'pending.pdf', status: 'pending', created_at: '2026-06-01T00:00:00Z' },
    ]);
    render(<DocumentList refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText(/98% match/i)).toBeInTheDocument();
      expect(screen.getByText(/failed/i)).toBeInTheDocument();
      expect(screen.getByText(/analyzing/i)).toBeInTheDocument();
    });
  });
});
