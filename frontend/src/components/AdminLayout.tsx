import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Boxes,
  Download,
  LayoutDashboard,
  LogOut,
  ScanSearch,
  ScrollText,
  ShieldCheck,
} from 'lucide-react';
import { logout } from '@/api';
import { ROUTES } from '@/router/routes';

type AdminNavItem = {
  to: string;
  label: string;
  icon: React.ReactNode;
  end?: boolean;
};

const NAV_SECTIONS: Array<{ title: string; items: AdminNavItem[] }> = [
  {
    title: '控制面',
    items: [
      {
        to: ROUTES.ADMIN_DASHBOARD,
        end: true,
        label: '系统控制面',
        icon: <LayoutDashboard className="h-4 w-4" aria-hidden="true" />,
      },
    ],
  },
  {
    title: '社区流转',
    items: [
      {
        to: ROUTES.ADMIN_CANDIDATES,
        label: '候选审核',
        icon: <ScanSearch className="h-4 w-4" aria-hidden="true" />,
      },
      {
        to: ROUTES.ADMIN_POOL,
        label: '社区池',
        icon: <Boxes className="h-4 w-4" aria-hidden="true" />,
      },
      {
        to: ROUTES.ADMIN_COMMUNITY_IMPORT,
        label: '社区导入',
        icon: <Download className="h-4 w-4" aria-hidden="true" />,
      },
    ],
  },
  {
    title: '任务追踪',
    items: [
      {
        to: ROUTES.ADMIN_TASK_LEDGER,
        label: '任务账本',
        icon: <ScrollText className="h-4 w-4" aria-hidden="true" />,
      },
    ],
  },
];

const AdminLayout: React.FC = () => {
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate(ROUTES.LOGIN);
  };

  return (
    <div className="min-h-screen bg-background lg:grid lg:grid-cols-[312px_minmax(0,1fr)]">
      <aside className="surface-admin-shell flex min-h-full flex-col border-b border-white/10 px-4 py-5 lg:border-b-0 lg:border-r lg:px-5 lg:py-6">
        <div className="space-y-4 border-b border-white/10 pb-5">
          <div className="flex items-center gap-3">
            <div className="surface-brand-mark flex h-12 w-12 items-center justify-center rounded-2xl text-primary-foreground">
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <div className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-primary/85">
                Control Desk
              </div>
              <div className="text-lg font-semibold text-white">Signal Admin</div>
            </div>
          </div>
          <p className="text-sm leading-6 text-white/70">
            这里先看系统稳不稳，再决定今天要不要处理社区和任务，不把后台做成第二个结果页。
          </p>
        </div>

        <nav className="mt-5 flex-1 space-y-5">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="space-y-2">
              <div className="px-2 text-[0.7rem] font-semibold uppercase tracking-[0.24em] text-white/45">
                {section.title}
              </div>
              <div className="space-y-2">
                {section.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end === true}
                    className={({ isActive }) =>
                      [
                        'group flex items-center justify-between rounded-2xl px-4 py-3 text-sm font-medium transition-colors',
                        'surface-admin-link',
                        isActive ? 'surface-admin-link-active' : '',
                      ].join(' ')
                    }
                  >
                    <span className="flex items-center gap-3">
                      <span className="text-current">{item.icon}</span>
                      <span>{item.label}</span>
                    </span>
                    <ArrowRight className="h-4 w-4 opacity-50 transition-transform group-hover:translate-x-0.5 group-hover:opacity-90" aria-hidden="true" />
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="space-y-3 border-t border-white/10 pt-5">
          <div className="rounded-[24px] border border-white/10 bg-white/5 px-4 py-4">
            <div className="text-sm font-semibold text-white">今天先看系统有没有跑顺</div>
            <p className="mt-2 text-sm leading-6 text-white/65">
              如果任务账本和控制面都正常，再去看候选审核和社区池，不要反着排。
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white/80 transition-colors hover:bg-white/10 hover:text-white"
          >
            <span className="flex items-center gap-3">
              <LogOut className="h-4 w-4" aria-hidden="true" />
              退出登录
            </span>
            <ArrowRight className="h-4 w-4 opacity-60" aria-hidden="true" />
          </button>
        </div>
      </aside>

      <main className="min-w-0 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default AdminLayout;
