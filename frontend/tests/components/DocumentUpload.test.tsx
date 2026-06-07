import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DocumentUpload from '@/components/DocumentUpload';

const mockFetch = vi.fn();
const mockRefresh = vi.fn();

vi.mock('@/lib/api', () => ({
  apiFetch: (...args: unknown[]) => mockFetch(...args),
}));

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

describe('DocumentUpload', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockRefresh.mockReset();
  });

  it('renders the upload form with a file input and submit button', () => {
    render(<DocumentUpload onUploadSuccess={mockRefresh} />);
    expect(screen.getByLabelText(/file/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload/i })).toBeInTheDocument();
  });

  it('rejects files that exceed the 25MB limit', async () => {
    render(<DocumentUpload onUploadSuccess={mockRefresh} />);
    const bigFile = new File(['x'.repeat(26 * 1024 * 1024)], 'big.pdf', { type: 'application/pdf' });
    const input = screen.getByLabelText(/file/i) as HTMLInputElement;
    await userEvent.upload(input, bigFile);
    const submitBtn = screen.getByRole('button', { name: /upload/i });
    await userEvent.click(submitBtn);
    // No fetch should occur for an over-limit file
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('rejects unsupported file extensions', async () => {
    render(<DocumentUpload onUploadSuccess={mockRefresh} />);
    const exe = new File(['fake'], 'malware.exe', { type: 'application/octet-stream' });
    const input = screen.getByLabelText(/file/i) as HTMLInputElement;
    await userEvent.upload(input, exe);
    const submitBtn = screen.getByRole('button', { name: /upload/i });
    await userEvent.click(submitBtn);
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('uploads a valid PDF and calls onUploadSuccess', async () => {
    // Magic bytes for a valid PDF
    const pdfHeader = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34]);
    const pdfContent = new Blob([pdfHeader, new Uint8Array(1000)], { type: 'application/pdf' });
    const pdfFile = new File([pdfContent], 'pitch.pdf', { type: 'application/pdf' });

    mockFetch.mockResolvedValueOnce({
      id: 1,
      file_name: 'pitch.pdf',
      status: 'pending',
      created_at: '2026-06-01T00:00:00Z',
    });

    const user = userEvent.setup();
    render(<DocumentUpload onUploadSuccess={mockRefresh} />);
    const input = screen.getByLabelText(/file/i) as HTMLInputElement;
    await user.upload(input, pdfFile);
    const submitBtn = screen.getByRole('button', { name: /upload/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
      expect(mockRefresh).toHaveBeenCalled();
    });
  });
});
