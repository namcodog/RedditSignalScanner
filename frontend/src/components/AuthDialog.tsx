/**
 * 认证对话框组件
 * 
 * 基于 PRD-06 用户认证系统
 * 参考实现: https://v0-reddit-business-signals.vercel.app
 * 
 * 功能:
 * - Tab切换（登录/注册）
 * - 表单验证
 * - 集成auth.api
 */

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { login, register } from '@/api/auth.api';
import { X } from 'lucide-react';

interface AuthDialogProps {
  isOpen: boolean;
  onClose: () => void;
  defaultTab?: 'login' | 'register';
}

interface LoginFormData {
  email: string;
  password: string;
}

interface RegisterFormData {
  name: string;
  email: string;
  password: string;
}

export const AuthDialog: React.FC<AuthDialogProps> = ({
  isOpen,
  onClose,
  defaultTab = 'login',
}) => {
  const [activeTab, setActiveTab] = useState<'login' | 'register'>(defaultTab);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register: registerLoginForm,
    handleSubmit: handleLoginSubmit,
    formState: { errors: loginErrors },
    reset: resetLoginForm,
  } = useForm<LoginFormData>();

  const {
    register: registerRegisterForm,
    handleSubmit: handleRegisterSubmit,
    formState: { errors: registerErrors },
    reset: resetRegisterForm,
  } = useForm<RegisterFormData>();

  const handleLogin = async (data: LoginFormData) => {
    setIsSubmitting(true);
    setError(null);
    try {
      await login(data);
      resetLoginForm();
      onClose();
      // 刷新页面以更新认证状态
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败，请检查邮箱和密码');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegister = async (data: RegisterFormData) => {
    setIsSubmitting(true);
    setError(null);
    try {
      await register({
        email: data.email,
        password: data.password,
      });
      resetRegisterForm();
      onClose();
      // 刷新页面以更新认证状态
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册失败，请稍后重试');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    resetLoginForm();
    resetRegisterForm();
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-labelledby="auth-dialog-title"
      aria-describedby="auth-dialog-description"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
      }}
      onClick={handleClose}
    >
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '24px',
          maxWidth: '400px',
          width: '90%',
          maxHeight: '90vh',
          overflow: 'auto',
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 关闭按钮 */}
        <button
          onClick={handleClose}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            padding: '4px',
            border: 'none',
            background: 'transparent',
            cursor: 'pointer',
            color: '#6b7280',
          }}
          aria-label="关闭"
        >
          <X size={20} />
        </button>

        {/* 标题 */}
        <h2
          id="auth-dialog-title"
          style={{
            fontSize: '24px',
            fontWeight: '600',
            marginBottom: '8px',
            color: '#111827',
          }}
        >
          账户登录
        </h2>
        <p
          id="auth-dialog-description"
          style={{
            fontSize: '14px',
            color: '#6b7280',
            marginBottom: '24px',
          }}
        >
          登录或注册以保存您的分析结果和访问高级功能
        </p>

        {/* Tab切换 */}
        <div
          role="tablist"
          aria-orientation="horizontal"
          style={{
            display: 'flex',
            borderBottom: '1px solid #e5e7eb',
            marginBottom: '24px',
          }}
        >
          <button
            role="tab"
            aria-selected={activeTab === 'login'}
            aria-controls="login-panel"
            onClick={() => {
              setActiveTab('login');
              setError(null);
            }}
            style={{
              flex: 1,
              padding: '12px',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              color: activeTab === 'login' ? '#2563eb' : '#6b7280',
              borderBottom: activeTab === 'login' ? '2px solid #2563eb' : 'none',
            }}
          >
            登录
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'register'}
            aria-controls="register-panel"
            onClick={() => {
              setActiveTab('register');
              setError(null);
            }}
            style={{
              flex: 1,
              padding: '12px',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              color: activeTab === 'register' ? '#2563eb' : '#6b7280',
              borderBottom: activeTab === 'register' ? '2px solid #2563eb' : 'none',
            }}
          >
            注册
          </button>
        </div>

        {/* 错误提示 */}
        {error && (
          <div
            role="alert"
            style={{
              padding: '12px',
              marginBottom: '16px',
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '4px',
              color: '#991b1b',
              fontSize: '14px',
            }}
          >
            {error}
          </div>
        )}

        {/* 登录面板 */}
        {activeTab === 'login' && (
          <div role="tabpanel" id="login-panel" aria-labelledby="login-tab">
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
              登录账户
            </h3>
            <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '16px' }}>
              输入您的邮箱和密码登录
            </p>
            <form onSubmit={handleLoginSubmit(handleLogin)}>
              <div style={{ marginBottom: '16px' }}>
                <label
                  htmlFor="login-email"
                  style={{
                    display: 'block',
                    fontSize: '14px',
                    fontWeight: '500',
                    marginBottom: '4px',
                    color: '#374151',
                  }}
                >
                  邮箱
                </label>
                <input
                  id="login-email"
                  type="email"
                  {...registerLoginForm('email', {
                    required: '请输入邮箱',
                    pattern: {
                      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                      message: '请输入有效的邮箱地址',
                    },
                  })}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    fontSize: '14px',
                  }}
                />
                {loginErrors.email && (
                  <p style={{ color: '#dc2626', fontSize: '12px', marginTop: '4px' }}>
                    {loginErrors.email.message}
                  </p>
                )}
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label
                  htmlFor="login-password"
                  style={{
                    display: 'block',
                    fontSize: '14px',
                    fontWeight: '500',
                    marginBottom: '4px',
                    color: '#374151',
                  }}
                >
                  密码
                </label>
                <input
                  id="login-password"
                  type="password"
                  {...registerLoginForm('password', {
                    required: '请输入密码',
                    minLength: {
                      value: 8,
                      message: '密码至少8个字符',
                    },
                  })}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    fontSize: '14px',
                  }}
                />
                {loginErrors.password && (
                  <p style={{ color: '#dc2626', fontSize: '12px', marginTop: '4px' }}>
                    {loginErrors.password.message}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                style={{
                  width: '100%',
                  padding: '10px',
                  backgroundColor: isSubmitting ? '#9ca3af' : '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                }}
              >
                {isSubmitting ? '登录中...' : '登录'}
              </button>
            </form>
          </div>
        )}

        {/* 注册面板 */}
        {activeTab === 'register' && (
          <div role="tabpanel" id="register-panel" aria-labelledby="register-tab">
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
              创建账户
            </h3>
            <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '16px' }}>
              注册新账户开始使用
            </p>
            <form onSubmit={handleRegisterSubmit(handleRegister)}>
              <div style={{ marginBottom: '16px' }}>
                <label
                  htmlFor="register-name"
                  style={{
                    display: 'block',
                    fontSize: '14px',
                    fontWeight: '500',
                    marginBottom: '4px',
                    color: '#374151',
                  }}
                >
                  姓名
                </label>
                <input
                  id="register-name"
                  type="text"
                  {...registerRegisterForm('name', {
                    required: '请输入姓名',
                    minLength: {
                      value: 2,
                      message: '姓名至少2个字符',
                    },
                  })}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    fontSize: '14px',
                  }}
                />
                {registerErrors.name && (
                  <p style={{ color: '#dc2626', fontSize: '12px', marginTop: '4px' }}>
                    {registerErrors.name.message}
                  </p>
                )}
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label
                  htmlFor="register-email"
                  style={{
                    display: 'block',
                    fontSize: '14px',
                    fontWeight: '500',
                    marginBottom: '4px',
                    color: '#374151',
                  }}
                >
                  邮箱
                </label>
                <input
                  id="register-email"
                  type="email"
                  {...registerRegisterForm('email', {
                    required: '请输入邮箱',
                    pattern: {
                      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                      message: '请输入有效的邮箱地址',
                    },
                  })}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    fontSize: '14px',
                  }}
                />
                {registerErrors.email && (
                  <p style={{ color: '#dc2626', fontSize: '12px', marginTop: '4px' }}>
                    {registerErrors.email.message}
                  </p>
                )}
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label
                  htmlFor="register-password"
                  style={{
                    display: 'block',
                    fontSize: '14px',
                    fontWeight: '500',
                    marginBottom: '4px',
                    color: '#374151',
                  }}
                >
                  密码
                </label>
                <input
                  id="register-password"
                  type="password"
                  {...registerRegisterForm('password', {
                    required: '请输入密码',
                    minLength: {
                      value: 8,
                      message: '密码至少8个字符',
                    },
                  })}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '4px',
                    fontSize: '14px',
                  }}
                />
                {registerErrors.password && (
                  <p style={{ color: '#dc2626', fontSize: '12px', marginTop: '4px' }}>
                    {registerErrors.password.message}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                style={{
                  width: '100%',
                  padding: '10px',
                  backgroundColor: isSubmitting ? '#9ca3af' : '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  fontSize: '14px',
                  fontWeight: '500',
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                }}
              >
                {isSubmitting ? '注册中...' : '注册'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuthDialog;

