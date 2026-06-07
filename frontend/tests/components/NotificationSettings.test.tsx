import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NotificationSettings from '@/components/dashboard/NotificationSettings';

const mockFetch = vi.fn();
vi.mock('@/lib/api', () => ({
  apiFetch: (...args: unknown[]) => mockFetch(...args),
}));

describe('NotificationSettings', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('renders the loading state initially', () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<NotificationSettings />);
    expect(screen.getByText(/retrieving security profile/i)).toBeInTheDocument();
  });

  it('loads organization settings and renders the toggle and slider', async () => {
    mockFetch.mockResolvedValueOnce({
      id: 1,
      name: 'Acme',
      subscription_tier: 'growth',
      match_threshold: 0.7,
      alert_email_enabled: true,
      created_at: '2026-06-01T00:00:00Z',
    });
    render(<NotificationSettings />);
    await waitFor(() => {
      expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
    });
    const slider = screen.getByRole('slider') as HTMLInputElement;
    expect(slider.value).toBe('0.7');
  });

  it('toggles the email alert switch and persists via PUT', async () => {
    mockFetch
      .mockResolvedValueOnce({
        id: 1,
        name: 'Acme',
        subscription_tier: 'growth',
        match_threshold: 0.7,
        alert_email_enabled: true,
        created_at: '2026-06-01T00:00:00Z',
      })
      .mockResolvedValueOnce({
        id: 1,
        name: 'Acme',
        subscription_tier: 'growth',
        match_threshold: 0.7,
        alert_email_enabled: false,
        created_at: '2026-06-01T00:00:00Z',
      });
    const user = userEvent.setup();
    render(<NotificationSettings />);
    const toggle = await screen.findByRole('switch');
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-checked', 'false');

    const submitBtn = screen.getByRole('button', { name: /save alert rules/i });
    await user.click(submitBtn);

    await waitFor(() => {
      const putCall = mockFetch.mock.calls.find(
        ([, init]: [string, RequestInit]) => (init as { method?: string })?.method === 'PUT'
      );
      expect(putCall).toBeDefined();
    });
  });
});
