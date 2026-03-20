import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Loader2, ShieldAlert } from 'lucide-react';
import { isAuthenticated, apiClient } from '@/api';
import ProductStatePanel from '@/components/product/ProductStatePanel';
import { ROUTES } from '@/router/routes';

interface AdminRouteProps {
  children: React.ReactNode;
}

const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
  const location = useLocation();
  const [status, setStatus] = useState<'loading' | 'authorized' | 'unauthorized' | 'forbidden'>('loading');

  useEffect(() => {
    let active = true;

    const checkAdmin = async () => {
      if (!isAuthenticated()) {
        if (active) {
          setStatus('unauthorized');
        }
        return;
      }

      try {
        await apiClient.get('/admin/dashboard/stats');
        if (active) {
          setStatus('authorized');
        }
      } catch (error: any) {
        console.error('[AdminRoute] Access check failed:', error);
        if (!active) {
          return;
        }

        if (error.status === 401) {
          setStatus('unauthorized');
        } else {
          setStatus('forbidden');
        }
      }
    };

    void checkAdmin();
    return () => {
      active = false;
    };
  }, [location.pathname]);

  if (status === 'loading') {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-3xl items-center px-4 py-10">
        <div className="surface-panel w-full rounded-[32px] p-8 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
            <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
          </div>
          <div className="surface-section-kicker mt-5 justify-center">Admin Access</div>
          <h1 className="mt-3 text-2xl font-semibold text-foreground">正在确认管理员权限</h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">
            这一步只做一件事：确认你能不能进入控制面。等权限确认完，页面会自动继续。
          </p>
        </div>
      </div>
    );
  }

  if (status === 'unauthorized') {
    return <Navigate to={ROUTES.LOGIN} state={{ from: location }} replace />;
  }

  if (status === 'forbidden') {
    return (
      <div className="mx-auto flex min-h-screen w-full max-w-3xl items-center px-4 py-10">
        <ProductStatePanel
          tone="error"
          title="这不是你的控制面权限"
          description="你已经登录了，但当前账号没有管理员权限，所以系统不会放你进入后台控制面。"
          nextStep="如果你本来就该有权限，先确认是不是登录错账号；如果不是管理员账号，就回首页继续走普通产品链路。"
          actions={[
            { label: '回首页', to: ROUTES.HOME, tone: 'primary' },
          ]}
          className="w-full"
        />
        <div className="sr-only">
          <ShieldAlert aria-hidden="true" />
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default AdminRoute;
