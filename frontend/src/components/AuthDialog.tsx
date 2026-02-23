/**
 * 认证对话框组件
 *
 * 基于 v0 设计还原 (auth-dialog.tsx)
 * 移除所有内联样式，使用 Tailwind 类名
 */

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { login, register } from '@/api/auth.api';
import { X, Loader2 } from 'lucide-react';
import clsx from 'clsx';

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

  useEffect(() => {
    if (isOpen) {
      setActiveTab(defaultTab);
    }
  }, [isOpen, defaultTab]);

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-md bg-white rounded-xl shadow-lg p-6 animate-in zoom-in-95 duration-200"
        role="dialog" 
        aria-modal="true"
      >
        <button
          onClick={handleClose}
          className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        >
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </button>

        <div className="mb-6 space-y-1">
          <h2 className="text-lg font-semibold leading-none tracking-tight">账户登录</h2>
          <p className="text-sm text-muted-foreground">
            登录或注册以保存您的分析结果和访问高级功能
          </p>
        </div>

        <div className="w-full">
          <div className="grid w-full grid-cols-2 bg-muted p-1 rounded-lg mb-6">
            <button
              onClick={() => { setActiveTab('login'); setError(null); }}
              className={clsx(
                "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                activeTab === 'login' ? "bg-white text-foreground shadow-sm" : "text-muted-foreground hover:bg-white/50"
              )}
            >
              登录
            </button>
            <button
              onClick={() => { setActiveTab('register'); setError(null); }}
              className={clsx(
                "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                activeTab === 'register' ? "bg-white text-foreground shadow-sm" : "text-muted-foreground hover:bg-white/50"
              )}
            >
              注册
            </button>
          </div>

          {error && (
            <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive border border-destructive/20">
              {error}
            </div>
          )}

          {activeTab === 'login' && (
            <div className="space-y-4 animate-in fade-in slide-in-from-left-2 duration-300">
              <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6 space-y-4">
                <div className="space-y-1.5">
                  <h3 className="font-semibold leading-none tracking-tight">登录账户</h3>
                  <p className="text-sm text-muted-foreground">输入您的邮箱和密码登录</p>
                </div>
                <form onSubmit={handleLoginSubmit(handleLogin)} className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70" htmlFor="login-email">
                      邮箱
                    </label>
                    <input
                      id="login-email"
                      type="email"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      placeholder="your@email.com"
                      {...registerLoginForm('email', { required: '请输入邮箱' })}
                    />
                    {loginErrors.email && <p className="text-xs text-destructive">{loginErrors.email.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70" htmlFor="login-password">
                      密码
                    </label>
                    <input
                      id="login-password"
                      type="password"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      {...registerLoginForm('password', { required: '请输入密码', minLength: { value: 8, message: '密码至少8个字符' } })}
                    />
                    {loginErrors.password && <p className="text-xs text-destructive">{loginErrors.password.message}</p>}
                  </div>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 w-full"
                  >
                    {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    登录
                  </button>
                </form>
              </div>
            </div>
          )}

          {activeTab === 'register' && (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-300">
              <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6 space-y-4">
                <div className="space-y-1.5">
                  <h3 className="font-semibold leading-none tracking-tight">创建账户</h3>
                  <p className="text-sm text-muted-foreground">注册新账户开始使用</p>
                </div>
                <form onSubmit={handleRegisterSubmit(handleRegister)} className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70" htmlFor="register-name">
                      姓名
                    </label>
                    <input
                      id="register-name"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      {...registerRegisterForm('name', { required: '请输入姓名', minLength: { value: 2, message: '姓名至少2个字符' } })}
                    />
                    {registerErrors.name && <p className="text-xs text-destructive">{registerErrors.name.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70" htmlFor="register-email">
                      邮箱
                    </label>
                    <input
                      id="register-email"
                      type="email"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      placeholder="your@email.com"
                      {...registerRegisterForm('email', { required: '请输入邮箱' })}
                    />
                    {registerErrors.email && <p className="text-xs text-destructive">{registerErrors.email.message}</p>}
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70" htmlFor="register-password">
                      密码
                    </label>
                    <input
                      id="register-password"
                      type="password"
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      {...registerRegisterForm('password', { required: '请输入密码', minLength: { value: 8, message: '密码至少8个字符' } })}
                    />
                    {registerErrors.password && <p className="text-xs text-destructive">{registerErrors.password.message}</p>}
                  </div>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 w-full"
                  >
                    {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    注册
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuthDialog;