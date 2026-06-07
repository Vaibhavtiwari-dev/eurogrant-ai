import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import CompanyProfile from '@/components/CompanyProfile';

const mockFetch = vi.fn();
vi.mock('@/lib/api', () => ({
  apiFetch: (...args: unknown[]) => mockFetch(...args),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

describe('CompanyProfile', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('renders the loading state initially', () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<CompanyProfile refreshKey={0} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders the no-profile fallback when sector is missing', async () => {
    mockFetch.mockResolvedValueOnce({
      name: 'Acme',
      subscription_tier: 'growth',
      sector: null,
    });
    render(<CompanyProfile refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('noProfileTitle')).toBeInTheDocument();
    });
  });

  it('renders the populated profile with metrics and tags', async () => {
    mockFetch.mockResolvedValueOnce({
      name: 'Acme',
      subscription_tier: 'scale',
      sector: 'EnergyTech',
      headcount_range: '11-50',
      revenue_tier: '1M-10M',
      legal_entity_type: 'GmbH',
      countries_of_operation: JSON.stringify(['Germany', 'France']),
      core_technologies: JSON.stringify(['AI', 'IoT']),
    });
    render(<CompanyProfile refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('EnergyTech')).toBeInTheDocument();
      expect(screen.getByText('Germany')).toBeInTheDocument();
      expect(screen.getByText('AI')).toBeInTheDocument();
    });
    // All three progress bars are present
    expect(screen.getAllByRole('progressbar')).toHaveLength(3);
  });

  it('handles malformed JSON in countries_of_operation gracefully', async () => {
    mockFetch.mockResolvedValueOnce({
      name: 'Acme',
      subscription_tier: 'growth',
      sector: 'FinTech',
      headcount_range: '1-10',
      legal_entity_type: 'LLC',
      countries_of_operation: '{not valid json',
      core_technologies: undefined,
    });
    render(<CompanyProfile refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('FinTech')).toBeInTheDocument();
    });
    // Should not throw; the catch branch returns [] and renders nothing extra
  });
});
