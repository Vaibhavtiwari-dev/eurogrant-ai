import {render, screen, waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {beforeEach, describe, expect, it, vi} from 'vitest';

import SettingsPage from '@/app/[locale]/settings/page';

const mockFetch = vi.fn();

vi.mock('@/lib/api', () => ({
  apiFetch: (...args: unknown[]) => mockFetch(...args),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: 'admin@example.com',
      full_name: 'Browser Admin',
      role: 'admin',
      organization_id: 1,
      created_at: '2026-06-11T00:00:00Z',
    },
    loading: false,
    logout: vi.fn(),
  }),
}));

vi.mock('@/components/dashboard/Sidebar', () => ({default: () => null}));
vi.mock('@/components/dashboard/Header', () => ({default: () => null}));
vi.mock('@/lib/animations', () => ({containerVariants: {}, itemVariants: {}}));

describe('SettingsPage', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('does not show password success after saving only the profile', async () => {
    mockFetch.mockResolvedValueOnce({ok: true});
    render(<SettingsPage />);

    await userEvent.click(screen.getByRole('button', {name: /save profile/i}));

    await waitFor(() => {
      expect(screen.getByText('Profile updated successfully.')).toBeInTheDocument();
    });
    expect(screen.queryByText('Password updated successfully.')).not.toBeInTheDocument();
  });
});
