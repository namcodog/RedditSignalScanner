import { execFileSync } from 'node:child_process';
import path from 'node:path';

import type { APIRequestContext, Page } from '@playwright/test';

const repoRoot = path.resolve(process.cwd(), '..');
const backendRoot = path.join(repoRoot, 'backend');

export const API_BASE_URL = process.env.PLAYWRIGHT_API_BASE_URL ?? 'http://localhost:8006/api';
export const ACCEPTANCE_EMAIL = process.env.PLAYWRIGHT_ACCEPTANCE_EMAIL ?? 'test@test.com';
export const ACCEPTANCE_PASSWORD = process.env.PLAYWRIGHT_ACCEPTANCE_PASSWORD ?? 'Test123!';
export const STRONG_REPORT_PRODUCT_DESCRIPTION =
  process.env.PLAYWRIGHT_REPORT_PRODUCT_DESCRIPTION ??
  '跨境电商卖家多平台回款与手续费管理工具，覆盖 Amazon/Etsy/Shopify/TikTok Shop，解决结算周期长、费率不透明、资金分散的问题。';

const sleep = async (milliseconds: number): Promise<void> =>
  new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });

const authHeaders = (token: string): Record<string, string> => ({
  Authorization: `Bearer ${token}`,
});

export const createUniqueEmail = (prefix: string): string =>
  `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;

export const registerUserViaApi = async (
  api: APIRequestContext,
  options: {
    email: string;
    password: string;
    membershipLevel?: 'free' | 'pro';
  },
): Promise<string> => {
  const response = await api.post(`${API_BASE_URL}/auth/register`, {
    data: {
      email: options.email,
      password: options.password,
      membership_level: options.membershipLevel ?? 'free',
    },
  });

  if (!response.ok()) {
    throw new Error(`register failed: ${response.status()} ${response.statusText()}`);
  }

  const payload = (await response.json()) as { access_token: string };
  return payload.access_token;
};

export const loginUserViaApi = async (
  api: APIRequestContext,
  options: {
    email: string;
    password: string;
  },
): Promise<string> => {
  const response = await api.post(`${API_BASE_URL}/auth/login`, {
    data: {
      email: options.email,
      password: options.password,
    },
  });

  if (!response.ok()) {
    throw new Error(`login failed: ${response.status()} ${response.statusText()}`);
  }

  const payload = (await response.json()) as { access_token: string };
  return payload.access_token;
};

export const loginSeededUserViaApi = async (
  api: APIRequestContext,
  options: {
    email?: string;
    password?: string;
  } = {},
): Promise<string> =>
  loginUserViaApi(api, {
    email: options.email ?? ACCEPTANCE_EMAIL,
    password: options.password ?? ACCEPTANCE_PASSWORD,
  });

export const injectAuthToken = async (page: Page, token: string): Promise<void> => {
  await page.addInitScript((value) => {
    window.localStorage.setItem('auth_token', value);
  }, token);
};

export interface RealReportSample {
  taskId: string;
  userId: string;
  userEmail: string;
  membershipLevel: string;
  reportTier: string;
}

export const createAcceptanceTokenForUser = (userId: string, email: string): string =>
  execFileSync(
    'python',
    [
      '-c',
      [
        'from app.core.security import create_access_token',
        `token,_=create_access_token('${userId}', email='${email}')`,
        'print(token)',
      ].join('; '),
    ],
    {
      cwd: backendRoot,
      encoding: 'utf-8',
      env: {
        ...process.env,
        PYTHONWARNINGS: 'ignore',
      },
    },
  ).trim();

export const findLatestRealReportSample = (
  options: {
    reportTier?: string;
    reportLimit?: number;
    requireUnblocked?: boolean;
    membershipLevels?: string[];
  } = {},
): RealReportSample => {
  const raw = execFileSync(
    'python',
    [
      'backend/scripts/acceptance/find_real_product_samples.py',
      '--report-limit',
      String(options.reportLimit ?? 12),
    ],
    {
      cwd: repoRoot,
      encoding: 'utf-8',
    },
  ).trim();

  const payload = JSON.parse(raw) as {
    report_samples?: Array<{
      task_id?: string;
      user_id?: string;
      user_email?: string | null;
      membership_level?: string | null;
      report_tier?: string | null;
      analysis_blocked?: string | null;
    }>;
  };

  const reportTier = options.reportTier ?? 'A_full';
  const requireUnblocked = options.requireUnblocked ?? true;
  const membershipLevels = (options.membershipLevels ?? ['pro', 'enterprise']).map((item) =>
    item.toLowerCase(),
  );
  const task = (payload.report_samples ?? []).find((sample) => {
    const tierMatches = String(sample.report_tier ?? '').trim() === reportTier;
    const blocked = String(sample.analysis_blocked ?? '').trim();
    const membershipLevel = String(sample.membership_level ?? '').toLowerCase();
    return (
      tierMatches &&
      (!requireUnblocked || !blocked) &&
      membershipLevels.includes(membershipLevel)
    );
  });

  const taskId = String(task?.task_id ?? '').trim();
  const userId = String(task?.user_id ?? '').trim();
  const userEmail = String(task?.user_email ?? '').trim();
  const membershipLevel = String(task?.membership_level ?? '').trim();
  if (!taskId || !userId || !userEmail || !membershipLevel) {
    throw new Error(`unable to find a real ${reportTier} report sample`);
  }

  return {
    taskId,
    userId,
    userEmail,
    membershipLevel,
    reportTier,
  };
};

export const createLiveReportTask = async (
  api: APIRequestContext,
  options: {
    authToken?: string;
    productDescription?: string;
    pollAttempts?: number;
    pollIntervalMs?: number;
    reportPollAttempts?: number;
    reportPollIntervalMs?: number;
    requireReportTier?: string;
    allowBlocked?: boolean;
  } = {},
): Promise<{
  taskId: string;
  authToken: string;
  reportTier: string;
  analysisBlocked: string;
}> => {
  const authToken = options.authToken ?? (await loginSeededUserViaApi(api));
  const productDescription = options.productDescription ?? STRONG_REPORT_PRODUCT_DESCRIPTION;
  const response = await api.post(`${API_BASE_URL}/analyze`, {
    data: {
      product_description: productDescription,
    },
    headers: authHeaders(authToken),
  });

  if (!response.ok()) {
    throw new Error(`create analysis task failed: ${response.status()} ${response.statusText()}`);
  }

  const payload = (await response.json()) as { task_id?: string; status?: string };
  const taskId = String(payload.task_id ?? '').trim();
  if (!taskId) {
    throw new Error('create analysis task failed: task_id missing');
  }

  const pollAttempts = options.pollAttempts ?? 90;
  const pollIntervalMs = options.pollIntervalMs ?? 2000;
  const reportPollAttempts = options.reportPollAttempts ?? 30;
  const reportPollIntervalMs = options.reportPollIntervalMs ?? 1000;
  const requireReportTier = options.requireReportTier ?? 'A_full';
  const allowBlocked = options.allowBlocked ?? false;

  for (let attempt = 1; attempt <= pollAttempts; attempt += 1) {
    const statusResponse = await api.get(`${API_BASE_URL}/status/${taskId}`, {
      headers: authHeaders(authToken),
    });

    if (!statusResponse.ok()) {
      throw new Error(`poll status failed: ${statusResponse.status()} ${statusResponse.statusText()}`);
    }

    const statusPayload = (await statusResponse.json()) as { status?: string };
    const status = String(statusPayload.status ?? '').toLowerCase();

    if (status === 'completed') {
      break;
    }

    if (status === 'failed') {
      throw new Error(`analysis task failed: ${taskId}`);
    }

    if (attempt === pollAttempts) {
      throw new Error(`analysis task timed out after ${pollAttempts} polls: ${taskId}`);
    }

    await sleep(pollIntervalMs);
  }

  for (let attempt = 1; attempt <= reportPollAttempts; attempt += 1) {
    const reportResponse = await api.get(`${API_BASE_URL}/report/${taskId}`, {
      headers: authHeaders(authToken),
    });
    if (reportResponse.ok()) {
      const reportPayload = (await reportResponse.json()) as {
        sources?: {
          report_tier?: string | null;
          analysis_blocked?: string | null;
        };
      };
      const reportTier = String(reportPayload.sources?.report_tier ?? '').trim();
      const analysisBlocked = String(reportPayload.sources?.analysis_blocked ?? '').trim();

      if (!allowBlocked && analysisBlocked) {
        throw new Error(`analysis blocked for ${taskId}: ${analysisBlocked}`);
      }

      if (requireReportTier && reportTier !== requireReportTier) {
        throw new Error(
          `unexpected report tier for ${taskId}: expected ${requireReportTier}, got ${reportTier || 'unknown'}`,
        );
      }

      return { taskId, authToken, reportTier, analysisBlocked };
    }

    if (reportResponse.status() === 409 && attempt < reportPollAttempts) {
      await sleep(reportPollIntervalMs);
      continue;
    }

    const errorBody = await reportResponse.text();
    throw new Error(
      `load report failed for ${taskId}: ${reportResponse.status()} ${reportResponse.statusText()} ${errorBody}`,
    );
  }

  throw new Error(`report for ${taskId} not ready after ${reportPollAttempts} polls`);
};

export const ensureSeededTestAccounts = (): void => {
  execFileSync('python', ['scripts/seed/seed_test_accounts.py'], {
    cwd: backendRoot,
    encoding: 'utf-8',
  });
};
