import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AdminLayout from '../AdminLayout';

describe('AdminLayout', () => {
  it('侧栏应包含社区导入入口', () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<div>stub</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    const link = screen.getByRole('link', { name: /社区导入/ });
    expect(link).toHaveAttribute('href', '/admin/communities/import');
  });
});
