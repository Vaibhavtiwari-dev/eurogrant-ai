import { describe, it, expect, vi } from 'vitest';
import { z } from 'zod';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Simple schema for testing
const TestSchema = z.object({
  id: z.number(),
  name: z.string(),
});

describe('apiFetch Zod Validation', () => {
  it('should validate and return parsed data when schema is provided', async () => {
    const mockData = { id: 1, name: 'Test Item' };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockData,
    });

    // We import dynamically to ensure mocks are applied
    const { apiFetch } = await import('../src/lib/api');
    
    const result = await apiFetch('/test', {}, TestSchema);
    expect(result).toEqual(mockData);
  });

  it('should throw when data does not match schema', async () => {
    const invalidData = { id: 'not-a-number', name: 'Test Item' };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => invalidData,
    });

    const { apiFetch } = await import('../src/lib/api');
    
    await expect(apiFetch('/test', {}, TestSchema)).rejects.toThrow();
  });
});
