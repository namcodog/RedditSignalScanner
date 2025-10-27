/**
 * Auth 页面测试
 *
 * 验证 PRD-06 登录/注册/404 页面骨架是否可渲染。
 * 注意：登录和注册页面现在重定向到首页，不再渲染独立页面
 */

import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import LoginPage from '../LoginPage';
import RegisterPage from '../RegisterPage';
import NotFoundPage from '../NotFoundPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Auth Pages', () => {
  it('登录页面重定向到首页', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    // 验证重定向被调用
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
  });

  it('注册页面重定向到首页', () => {
    mockNavigate.mockClear();
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    );

    // 验证重定向被调用
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
  });

  it('渲染 404 页面并提供返回链接', () => {
    render(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: '404' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回首页' })).toHaveAttribute('href', '/');
  });
});
