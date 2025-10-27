import { describe, it, expect } from 'vitest';

import { classifyReportError, ReportErrorType } from '@/utils/report-error';

describe('classifyReportError', () => {
  it('将没有响应的 axios 错误识别为网络错误', () => {
    const networkError = {
      isAxiosError: true,
      code: 'ERR_NETWORK',
      message: 'Network Error',
    };

    const result = classifyReportError(networkError);

    expect(result.type).toBe(ReportErrorType.NETWORK_ERROR);
    expect(result.retryable).toBe(true);
  });

  it('将 404 错误识别为报告不存在', () => {
    const responseError = {
      isAxiosError: true,
      response: {
        status: 404,
        data: { detail: 'Not Found' },
      },
    };

    const result = classifyReportError(responseError);

    expect(result.type).toBe(ReportErrorType.NOT_FOUND);
    expect(result.retryable).toBe(false);
  });

  it('将 409 错误识别为报告未准备好并支持重试', () => {
    const conflictError = {
      isAxiosError: true,
      response: {
        status: 409,
        data: { detail: 'Report not ready' },
      },
    };

    const result = classifyReportError(conflictError);

    expect(result.type).toBe(ReportErrorType.REPORT_NOT_READY);
    expect(result.retryable).toBe(true);
  });

  it('未知异常时返回默认错误', () => {
    const result = classifyReportError(new Error('boom'));

    expect(result.type).toBe(ReportErrorType.UNKNOWN);
    expect(result.retryable).toBe(false);
  });
});
