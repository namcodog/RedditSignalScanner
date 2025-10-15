/**
 * Auth 页面测试
 *
 * 验证 PRD-06 登录/注册/404 页面骨架是否可渲染。
 */

import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import LoginPage from '../LoginPage';
import RegisterPage from '../RegisterPage';
import NotFoundPage from '../NotFoundPage';

describe('Auth Pages', () => {
  it('渲染登录页面骨架', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: '登录' })).toBeInTheDocument();
    expect(screen.getByText(/登录页面骨架/i)).toBeInTheDocument();
  });

  it('渲染注册页面骨架', () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: '注册' })).toBeInTheDocument();
    expect(screen.getByText(/注册页面骨架/i)).toBeInTheDocument();
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
