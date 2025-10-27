import type { AxiosError } from 'axios';

export enum ReportErrorType {
  NETWORK_ERROR = 'network',
  NOT_FOUND = 'not_found',
  PERMISSION_DENIED = 'permission_denied',
  REPORT_NOT_READY = 'not_ready',
  UNKNOWN = 'unknown',
}

export interface ReportErrorState {
  type: ReportErrorType;
  message: string;
  action?: string;
  retryable: boolean;
}

const createState = (
  type: ReportErrorType,
  message: string,
  options?: Partial<Pick<ReportErrorState, 'action' | 'retryable'>>
): ReportErrorState => ({
  type,
  message,
  action: options?.action,
  retryable: options?.retryable ?? false,
});

const isAxiosError = (error: unknown): error is AxiosError => {
  return typeof error === 'object' && error !== null && 'isAxiosError' in error;
};

export const classifyReportError = (error: unknown): ReportErrorState => {
  if (isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;

    if (!axiosError.response) {
      return createState(ReportErrorType.NETWORK_ERROR, '网络连接异常，请检查网络后重试。', {
        action: '请检查网络连接后再次尝试。',
        retryable: true,
      });
    }

    const { status, data } = axiosError.response;
    const detail = data?.detail;

    if (status === 404) {
      return createState(
        ReportErrorType.NOT_FOUND,
        detail ?? '未能找到对应的分析报告。',
        { action: '请返回任务列表，确认任务是否已完成。' }
      );
    }

    if (status === 403) {
      return createState(
        ReportErrorType.PERMISSION_DENIED,
        detail ?? '您暂无权限查看该报告。',
        { action: '请确认是否登录正确账号或联系管理员开启访问权限。' }
      );
    }

    if (status === 409) {
      return createState(
        ReportErrorType.REPORT_NOT_READY,
        detail ?? '报告正在生成中，请稍后再次尝试。',
        { action: '稍等片刻后重新加载即可继续查看。', retryable: true }
      );
    }

    if (status >= 500) {
      return createState(
        ReportErrorType.UNKNOWN,
        '服务器开小差了，我们已记录该问题。',
        { action: '请稍后重试，若问题持续请反馈给团队。' }
      );
    }
  }

  return createState(
    ReportErrorType.UNKNOWN,
    '获取报告失败，请稍后重试。',
    { action: '请刷新页面或稍后再试。' }
  );
};
