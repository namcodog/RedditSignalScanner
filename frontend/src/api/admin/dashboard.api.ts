import { apiClient } from '../client';

export interface DashboardStats {
  total_users: number;
  total_tasks: number;
  tasks_today: number;
  tasks_completed_today: number;
  avg_processing_time: number;
  cache_hit_rate: number;
  active_workers: number;
  pipeline_health: Record<string, any>;
}

export const getAdminDashboardStats = async (): Promise<DashboardStats> => {
  const response = await apiClient.get<DashboardStats>('/admin/dashboard/stats');
  return response.data;
};
