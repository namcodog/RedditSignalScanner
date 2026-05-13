import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { render, waitFor } from '@testing-library/react';

import StandardCasePage from '../StandardCasePage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

afterEach(() => {
  mockNavigate.mockReset();
});

describe('StandardCasePage', () => {
  it('redirects legacy standard-case routes to the standard report page', async () => {
    render(
      <MemoryRouter initialEntries={['/standard-case/cross-border-paypal']}>
        <Routes>
          <Route path="/standard-case/:slug" element={<StandardCasePage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/standard-report/cross-border-paypal', { replace: true });
    });
  });
});
