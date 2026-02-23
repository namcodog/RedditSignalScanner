import { createBrowserRouter } from 'react-router-dom';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import InputPage from '@/pages/InputPage';
import ProgressPage from '@/pages/ProgressPage';
import ReportPage from '@/pages/ReportPage';
import NotFoundPage from '@/pages/NotFoundPage';
import InsightPage from '@/pages/InsightsPage';
import DecisionUnitPage from '@/pages/DecisionUnitsPage';
import AdminRoute from '@/components/AdminRoute';
import AdminLayout from '@/components/AdminLayout';

// Admin Pages
import AdminDashboardPage from '@/pages/AdminDashboardPage';
import DiscoveredCommunitiesPage from '@/pages/admin/DiscoveredCommunitiesPage';
import CommunityPoolPage from '@/pages/admin/CommunityPoolPage';
import TaskLedgerPage from '@/pages/admin/TaskLedgerPage';
import CommunityImportPage from '@/pages/admin/CommunityImport';

// Other Pages
import DashboardPage from '@/pages/DashboardPage';
import HotPostSearchPage from '@/pages/hotpost/HotPostSearchPage';
import HotPostResultPage from '@/pages/hotpost/HotPostResultPage';

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/',
    element: <InputPage />,
  },
  {
    path: '/hotpost',
    element: <HotPostSearchPage />,
  },
  {
    path: '/hotpost/result/:queryId',
    element: <HotPostResultPage />,
  },
  {
    path: '/progress/:taskId',
    element: <ProgressPage />,
  },
  {
    path: '/report/:taskId',
    element: <ReportPage />,
  },
  {
    path: '/insights',
    element: <InsightPage />,
  },
  {
    path: '/insights/:taskId',
    element: <InsightPage />,
  },
  {
    path: '/decision-units',
    element: <DecisionUnitPage />,
  },
  {
    path: '/dashboard',
    element: <DashboardPage />,
  },
  {
    path: '/admin',
    element: (
      <AdminRoute>
        <AdminLayout />
      </AdminRoute>
    ),
    children: [
      {
        index: true,
        element: <AdminDashboardPage />,
      },
      {
        path: 'communities/discovered',
        element: <DiscoveredCommunitiesPage />,
      },
      {
        path: 'communities/pool',
        element: <CommunityPoolPage />,
      },
      {
        path: 'communities/import',
        element: <CommunityImportPage />,
      },
      {
        path: 'tasks/ledger',
        element: <TaskLedgerPage />,
      },
      // 复盘页详情路由 (Task Ledger) - using same component with ID handling
      {
        path: 'tasks/:taskId/ledger',
        element: <TaskLedgerPage />,
      }
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]);

export default router;

// --- Path Constants ---
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  HOTPOST: '/hotpost',
  HOTPOST_RESULT: (queryId: string) => `/hotpost/result/${queryId}`,
  PROGRESS: (taskId: string) => `/progress/${taskId}`,
  REPORT: (taskId: string) => `/report/${taskId}`,
  INSIGHTS: '/insights',
  DECISION_UNITS: '/decision-units',
  DASHBOARD: '/dashboard',
  ADMIN_DASHBOARD: '/admin',
  ADMIN_CANDIDATES: '/admin/communities/discovered',
  ADMIN_POOL: '/admin/communities/pool',
  ADMIN_COMMUNITY_IMPORT: '/admin/communities/import',
  ADMIN_TASK_LEDGER: '/admin/tasks/ledger',
  INSIGHTS_TASK: (taskId: string) => `/insights/${taskId}`,
};
