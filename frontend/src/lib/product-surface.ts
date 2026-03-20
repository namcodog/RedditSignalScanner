import type { DashboardStats, TaskLedgerItem } from '@/api/admin.api';
import type { ReportResponse } from '@/types';
import type { HotPostMode, HotPostResponse } from '@/types/hotpost';

import type { SurfaceHeroBadge, SurfaceHeroMetric, SurfaceHeroProps } from '@/components/product/SurfaceHero';

type UserFacingReadiness = 'ready' | 'directional' | 'enriching';

export interface ProductDecisionReason {
  title: string;
  description: string;
}

export interface ProductDecisionSignal {
  label: string;
  value: string;
  help?: string;
}

export interface ProductDecisionSummary {
  verdictTitle: string;
  verdictDescription: string;
  reasons: ProductDecisionReason[];
  signals: ProductDecisionSignal[];
  nextStepTitle: string;
  nextStepDescription: string;
}

export interface ProductActionPlan {
  primaryLabel: string;
  secondaryLabel: string;
  tertiaryLabel?: string;
  primaryIntent: 'open-full-report' | 'restart-analysis' | 'generate-deep-dive' | 'review-evidence';
  secondaryIntent: 'open-dimensions' | 'review-evidence' | 'retry-search';
  tertiaryIntent?: 'restart-analysis' | 'retry-search';
  sectionEyebrow: string;
  sectionTitle: string;
  sectionDescription: string;
}

const REPORT_TIER_LABELS: Record<string, string> = {
  A_full: '完整结论',
  B_trimmed: '方向判断',
  C_scouting: '方向判断',
  X_blocked: '线索预览',
};

const HOTPOST_MODE_LABELS: Record<HotPostMode, string> = {
  trending: '热点快报',
  rant: '痛点快扫',
  opportunity: '机会快扫',
};

const formatPercent = (value: number | null | undefined): string => {
  if (!Number.isFinite(value)) return '-';
  return `${(Number(value) * 100).toFixed(0)}%`;
};

const formatLocalTime = (value: string | null | undefined): string => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

const parseCommunityWeight = (value: unknown): number => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const numeric = Number.parseFloat(value.replace('%', '').trim());
    return Number.isFinite(numeric) ? numeric : 0;
  }
  return 0;
};

const ADMIN_TASK_STATUS_LABELS: Record<string, string> = {
  completed: '已完成',
  failed: '失败',
  processing: '进行中',
  pending: '排队中',
  queued: '排队中',
  running: '进行中',
};

const toAdminTaskStatusLabel = (value: string | null | undefined): string => {
  const raw = String(value ?? '').trim().toLowerCase();
  if (!raw) {
    return '暂时空闲';
  }
  return ADMIN_TASK_STATUS_LABELS[raw] ?? raw;
};

const signalStrengthBadge = (score: number | null | undefined): SurfaceHeroBadge => {
  if (!Number.isFinite(score)) {
    return { label: '正在补证据', tone: 'warning' };
  }
  const numeric = Number(score);
  if (numeric >= 0.8) return { label: `信号扎实 ${formatPercent(numeric)}`, tone: 'success' };
  if (numeric >= 0.6) return { label: `方向已浮现 ${formatPercent(numeric)}`, tone: 'info' };
  return { label: `先看线索 ${formatPercent(numeric)}`, tone: 'warning' };
};

const readinessBadge = (readiness: UserFacingReadiness): SurfaceHeroBadge => {
  switch (readiness) {
    case 'ready':
      return { label: '可直接看结论', tone: 'success' };
    case 'directional':
      return { label: '先判断方向', tone: 'info' };
    default:
      return { label: '系统正在补证据', tone: 'warning' };
  }
};

const resolveReportTier = (report: ReportResponse): string =>
  report.sources?.report_tier ?? 'A_full';

const resolveReportBlockedReason = (report: ReportResponse): string =>
  String(report.sources?.analysis_blocked ?? '').trim();

const resolveReportCommunityCount = (report: ReportResponse): number =>
  report.sources?.communities?.length ?? report.overview.top_communities?.length ?? 0;

const resolveReportPostsAnalyzed = (report: ReportResponse): number =>
  report.sources?.posts_analyzed ?? 0;

const resolveReportTopCommunity = (report: ReportResponse): string =>
  report.overview.top_communities?.[0]?.name || '公开讨论还没集中到单一社区';

const hasCjk = (value: string): boolean => /[\u3400-\u9FFF]/.test(value);
const cjkRatio = (value: string): number => {
  const content = value.replace(/\s+/g, '');
  if (!content) return 0;
  const cjkCount = (content.match(/[\u3400-\u9FFF]/g) ?? []).length;
  return cjkCount / content.length;
};

const stripMarkdownNoise = (value: string): string =>
  value
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '$1')
    .replace(/https?:\/\/\S+/g, '')
    .replace(/\s+/g, ' ')
    .trim();

const toUserFacingSnippet = (value: string | null | undefined, fallback: string, maxLength = 72): string => {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return fallback;
  }

  const cleaned = stripMarkdownNoise(raw);
  if (!cleaned) {
    return fallback;
  }

  if (!hasCjk(cleaned)) {
    return fallback;
  }

  if (cjkRatio(cleaned) < 0.35) {
    return fallback;
  }

  return cleaned.length > maxLength ? `${cleaned.slice(0, maxLength).trimEnd()}…` : cleaned;
};

const selectSurfaceLabel = (
  fallback: string,
  ...candidates: Array<string | null | undefined>
): string => {
  let firstAsciiCandidate: string | null = null;

  for (const candidate of candidates) {
    const text = String(candidate ?? '').trim();
    if (!text) continue;

    if (hasCjk(text) && text.length >= 6) {
      return text;
    }

    if (!firstAsciiCandidate) {
      firstAsciiCandidate = text;
    }
  }

  for (const candidate of candidates) {
    const text = String(candidate ?? '').trim();
    if (hasCjk(text)) return text;
  }

  if (firstAsciiCandidate) {
    return fallback;
  }

  return fallback;
};

const resolveReportTopOpportunity = (report: ReportResponse): string =>
  selectSurfaceLabel(
    '讨论里已经出现可追机会，建议先看完整报告确认优先级。',
    report.report_structured?.opportunities?.[0]?.product_positioning,
    report.report_structured?.opportunities?.[0]?.title,
    report.report.opportunities?.[0]?.description,
    report.report.opportunities?.[0]?.text,
    report.report.opportunities?.[0]?.title,
    report.report.executive_summary.top_opportunity,
  );

const resolveReportTopPain = (report: ReportResponse): string =>
  selectSurfaceLabel(
    '讨论里有反复出现的抱怨，建议先看完整报告定位原因。',
    report.report_structured?.pain_points?.[0]?.title,
    report.report.pain_points?.[0]?.text,
    report.report.pain_points?.[0]?.description,
  );

const reportStrengthBadge = (report: ReportResponse): SurfaceHeroBadge => {
  const tier = resolveReportTier(report);
  const blockedReason = resolveReportBlockedReason(report);

  if (tier === 'A_full') {
    return { label: '结论已成型', tone: 'success' };
  }
  if (tier === 'B_trimmed') {
    return { label: '方向已浮现', tone: 'info' };
  }
  if (blockedReason === 'insufficient_samples') {
    return { label: '先看公开线索', tone: 'info' };
  }
  if (tier === 'C_scouting') {
    return { label: '先看方向', tone: 'info' };
  }
  if (tier === 'X_blocked') {
    return { label: '先看线索', tone: 'warning' };
  }
  return signalStrengthBadge(report.metadata.confidence_score);
};

const dataSourceBadge = (report: ReportResponse): SurfaceHeroBadge | null => {
  const dataSource = String(report.sources?.data_source ?? '').trim().toLowerCase();
  if (dataSource === 'real') {
    return { label: '真实讨论', tone: 'success' };
  }
  return null;
};

const resolveReportReadiness = (report: ReportResponse): UserFacingReadiness => {
  const tier = resolveReportTier(report);
  if (tier === 'A_full') {
    return 'ready';
  }
  if (tier === 'X_blocked') {
    return 'enriching';
  }
  if (tier === 'B_trimmed' || tier === 'C_scouting') {
    return 'directional';
  }
  if ((report.metadata.confidence_score ?? 0) >= 0.8) {
    return 'ready';
  }
  return 'directional';
};

export const buildReportSurfaceHero = (report: ReportResponse): SurfaceHeroProps => {
  const tier = resolveReportTier(report);
  const tierLabel = REPORT_TIER_LABELS[tier] ?? '市场洞察报告';
  const blockedReason = resolveReportBlockedReason(report);
  const communityCount = resolveReportCommunityCount(report);
  const postsAnalyzed = resolveReportPostsAnalyzed(report);
  const topCommunity = resolveReportTopCommunity(report);
  const topOpportunity = resolveReportTopOpportunity(report);
  const topPain = resolveReportTopPain(report);
  const readiness = resolveReportReadiness(report);
  const nextSteps =
    readiness === 'ready'
      ? [
          topOpportunity ? `先盯这条机会：${topOpportunity}` : '先盯最值得追的机会。',
          '不够再往下拆，不用整页通读。',
        ]
      : blockedReason === 'insufficient_samples'
        ? [
            '先决定这个方向要不要继续追。',
            '不够再放大范围。',
          ]
        : tier === 'X_blocked'
          ? [
              '这轮先看已抓到的线索，不直接下结论。',
              '要继续就补关键词、时间窗或社区范围再跑。',
            ]
        : [
            topOpportunity ? `先看这条机会：${topOpportunity}` : '先把方向定下来。',
            '不够再补成完整结论。',
          ];

  const readinessCopy =
    readiness === 'ready'
      ? {
          eyebrow: tierLabel,
          title: '这次已经值得继续做',
          description: `这轮已经覆盖 ${communityCount} 个社区、处理 ${postsAnalyzed} 条帖子，已经够你先决定追不追、为什么、下一步投不投时间。`,
          warning: null,
          warningTitle: null,
          warningNextStep: null,
        }
      : blockedReason === 'insufficient_samples'
        ? {
            eyebrow: tierLabel,
            title: '这次先决定追不追',
            description: '公开讨论还早，但已经够你先决定要不要继续追。',
            warning: null,
            warningTitle: null,
            warningNextStep: null,
          }
        : tier === 'X_blocked'
          ? {
              eyebrow: tierLabel,
              title: '这次先看已抓到的线索',
              description: '这轮还不够给最终判断，先看现有线索，再决定是否放大范围重跑。',
              warning: null,
              warningTitle: null,
              warningNextStep: null,
            }
        : {
            eyebrow: tierLabel,
            title: '这次先把方向定下来',
            description: '这轮信号已经够你先定方向和优先级。先判断追不追，再决定要不要补成完整结论。',
            warning: null,
            warningTitle: null,
            warningNextStep: null,
          };

  const sourceBadge = dataSourceBadge(report);
  const metrics: SurfaceHeroMetric[] = [
    {
      label: '当前最活跃社区',
      value: topCommunity,
    },
    {
      label: '最明显的用户抱怨',
      value: topPain,
    },
    {
      label: '最值得追的机会',
      value: topOpportunity,
    },
    {
      label: '覆盖范围',
      value: `${communityCount} 个社区 / ${postsAnalyzed} 条帖子`,
      help: `最近生成：${formatLocalTime(report.generated_at)}`,
    },
  ];

  return {
    eyebrow: readinessCopy.eyebrow,
    title: readinessCopy.title,
    description: readinessCopy.description,
    badges: [
      readinessBadge(readiness),
      ...(sourceBadge ? [sourceBadge] : []),
      { label: tierLabel, tone: readiness === 'ready' ? 'success' : readiness === 'directional' ? 'info' : 'warning' },
      reportStrengthBadge(report),
    ],
    metrics,
    nextSteps,
    warning:
      String(report.sources?.data_source ?? '').trim().toLowerCase() === 'example'
        ? '当前是示例回放，不代表刚刚真的抓了 Reddit。'
        : readinessCopy.warning,
    warningTitle:
      String(report.sources?.data_source ?? '').trim().toLowerCase() === 'example'
        ? '当前不是实时结果'
        : readinessCopy.warningTitle,
    warningNextStep:
      String(report.sources?.data_source ?? '').trim().toLowerCase() === 'example'
        ? '要看真流程，请从输入页重新发起一次真实分析。'
        : readinessCopy.warningNextStep,
  };
};

export const buildReportDecisionSummary = (report: ReportResponse): ProductDecisionSummary => {
  const readiness = resolveReportReadiness(report);
  const blockedReason = resolveReportBlockedReason(report);
  const reasons =
    report.report_structured?.decision_cards?.slice(0, 2).map((card) => ({
      title: card.title,
      description: card.details[0] || card.conclusion,
    })) ?? [];

  if (reasons.length === 0) {
    reasons.push(
      {
        title: '讨论有没有持续冒头',
        description: '先看同类声音是不是在重复出现。',
      },
      {
        title: '抱怨是不是具体可解',
        description: '先看抱怨够不够具体，值不值得做解法。',
      },
    );
  }

  return {
    verdictTitle:
      readiness === 'ready'
        ? '可以拍第一板'
        : blockedReason === 'insufficient_samples'
          ? '先定要不要放大'
          : readiness === 'directional'
          ? '先定值不值得追'
          : '先把它当成方向线索',
    verdictDescription:
      readiness === 'ready'
        ? '这一屏已经够你先拍板。'
        : blockedReason === 'insufficient_samples'
          ? '样本还轻，先决定要不要放大。'
        : readiness === 'directional'
          ? '方向已冒头，先决定值不值得追。'
          : '先把它当成方向线索。',
    reasons,
    signals: [],
    nextStepTitle: '下一步动作',
    nextStepDescription:
      readiness === 'ready'
        ? '先挑最影响拍板的一块看。'
        : blockedReason === 'insufficient_samples'
          ? '要么现在停在这里，要么放大范围再跑。'
        : readiness === 'directional'
          ? '先扫机会和证据，再决定要不要补完整报告。'
          : '够判断就停，不够再往下拆。',
  };
};

export const buildReportActionPlan = (report: ReportResponse): ProductActionPlan => {
  const readiness = resolveReportReadiness(report);
  const blockedReason = resolveReportBlockedReason(report);

  if (readiness === 'ready') {
    return {
      primaryLabel: '看完整报告',
      secondaryLabel: '逐维探索',
      tertiaryLabel: '回输入页重跑',
      primaryIntent: 'open-full-report',
      secondaryIntent: 'open-dimensions',
      tertiaryIntent: 'restart-analysis',
      sectionEyebrow: '下一步',
      sectionTitle: '如果还想继续，再往下看',
      sectionDescription: '先挑最影响拍板的一块，不用整页通读。',
    };
  }

  return {
    primaryLabel: '放大范围再跑',
    secondaryLabel: '逐维探索',
    tertiaryLabel: '换方向再看',
    primaryIntent: 'restart-analysis',
    secondaryIntent: 'open-dimensions',
    tertiaryIntent: 'restart-analysis',
    sectionEyebrow: '下一步',
    sectionTitle:
      blockedReason === 'insufficient_samples'
        ? '如果这轮还不够，就放大范围再跑'
        : '如果这轮还不够，就继续往下拆',
    sectionDescription:
      blockedReason === 'insufficient_samples'
        ? '先挑最想确认的一块；不够再带回输入页放大范围。'
        : '先挑最影响判断的一块；有戏再补更完整的一轮。',
  };
};

const hotpostSourceLabel = (payload: HotPostResponse): SurfaceHeroBadge => {
  const responseSource = payload.debug_info?.response_source;
  if (payload.from_cache || responseSource === 'cache') {
    return { label: '最近一次扫描', tone: 'info' };
  }
  if (responseSource === 'fallback') {
    return { label: '快速整理结果', tone: 'warning' };
  }
  return { label: '刚刚扫描', tone: 'success' };
};

const hotpostConfidenceBadge = (payload: HotPostResponse): SurfaceHeroBadge => {
  switch (payload.confidence) {
    case 'high':
      return { label: `信号扎实 ${payload.evidence_count} 条`, tone: 'success' };
    case 'medium':
      return { label: `方向已浮现 ${payload.evidence_count} 条`, tone: 'info' };
    case 'low':
      return { label: `先看线索 ${payload.evidence_count} 条`, tone: 'warning' };
    default:
      return { label: '系统正在补证据', tone: 'warning' };
  }
};

const resolveHotpostPrimaryAngle = (payload: HotPostResponse): string => {
  if (payload.mode === 'opportunity') {
    return toUserFacingSnippet(
      payload.unmet_needs?.[0]?.need ||
      payload.unmet_needs?.[0]?.summary ||
      payload.opportunities?.[0]?.need ||
      payload.opportunities?.[0]?.summary ||
      payload.summary,
      '这波机会已经冒头，先看证据再决定要不要继续追。'
    );
  }
  if (payload.mode === 'rant') {
    return toUserFacingSnippet(
      payload.pain_points?.[0]?.category ||
      payload.pain_points?.[0]?.description ||
      payload.summary,
      '这波抱怨正在集中，先看证据再判断是不是稳定痛点。'
    );
  }
  return toUserFacingSnippet(
    payload.topics?.[0]?.key_takeaway || payload.topics?.[0]?.topic || payload.summary,
    '这波讨论热度正在集中，先看证据再决定要不要继续追。'
  );
};

const resolveHotpostLeadCommunity = (payload: HotPostResponse): { name: string; share: string } => {
  const topEntry =
    Object.entries(payload.community_distribution || {}).sort(
      (a, b) => parseCommunityWeight(b[1]) - parseCommunityWeight(a[1]),
    )[0] ?? null;

  if (!topEntry) {
    const firstCommunity = Array.isArray(payload.communities)
      ? payload.communities[0]
      : null;
    if (typeof firstCommunity === 'string') {
      return { name: firstCommunity, share: '已开始出现' };
    }
    if (firstCommunity && typeof firstCommunity === 'object' && 'name' in firstCommunity) {
      return { name: String(firstCommunity.name), share: '已开始出现' };
    }
    return { name: '社区还没收拢到一个主战场', share: '还在扩散' };
  }

  return { name: topEntry[0], share: String(topEntry[1]) };
};

const resolveHotpostReadiness = (payload: HotPostResponse): UserFacingReadiness => {
  if (payload.confidence === 'high') {
    return 'ready';
  }
  if (payload.confidence === 'medium') {
    return 'directional';
  }
  if (payload.confidence === 'low' || payload.confidence === 'none') {
    return 'enriching';
  }

  const degradedReason =
    payload.debug_info?.degraded_reasons?.[0] ||
    payload.debug_info?.summary_degraded_reason ||
    payload.debug_info?.report_degraded_reason ||
    payload.debug_info?.query_degraded_reason;
  if (degradedReason) {
    return 'directional';
  }
  return 'ready';
};

export const buildHotpostSurfaceHero = (payload: HotPostResponse): SurfaceHeroProps => {
  const modeLabel = HOTPOST_MODE_LABELS[payload.mode] ?? '快反结果';
  const communityCount = Array.isArray(payload.communities) ? payload.communities.length : Object.keys(payload.community_distribution || {}).length;
  const readiness = resolveHotpostReadiness(payload);
  const primaryAngle = resolveHotpostPrimaryAngle(payload);
  const leadCommunity = resolveHotpostLeadCommunity(payload);

  const nextSteps =
    readiness === 'ready'
      ? [
          payload.mode === 'opportunity'
            ? '先看最明显的未满足需求。'
            : payload.mode === 'rant'
              ? '先看最集中的抱怨。'
              : '先看摘要，再翻前几条证据帖。',
          payload.next_steps?.deepdive_available
            ? '觉得有戏，就直接转深度报告。'
            : '方向还不稳，就换个更具体的关键词重扫。',
        ]
      : readiness === 'directional'
        ? [
            '先把这页当作方向判断页。',
            payload.next_steps?.deepdive_available
              ? '方向对，就直接转深度报告。'
              : '方向还不稳，就换词或补社区。',
          ]
        : [
            '先看摘要和社区分布。',
            payload.next_steps?.deepdive_available
              ? '如果已经够吸引你，就直接转深度报告。'
              : '还拿不准，就换词再扫一次。',
          ];

  const readinessCopy =
    readiness === 'ready'
      ? {
          title: '这波值得马上继续追',
          description: `这次快扫已经抓到 ${payload.evidence_count} 条真实证据，够你先决定现在追，还是先放过。`,
          warning: null,
          warningTitle: null,
          warningNextStep: null,
        }
      : readiness === 'directional'
        ? {
            title: '这波先决定追不追',
            description: '这轮快扫已经够你先定方向，再决定要不要转成正式报告。',
            warning: null,
            warningTitle: null,
            warningNextStep: null,
          }
        : {
            title: '先把这波当成方向线索',
            description: '这次快扫已经捞到第一批信号，先看值不值得继续追。',
            warning: null,
            warningTitle: null,
            warningNextStep: null,
          };

  return {
    eyebrow: modeLabel,
    title: readinessCopy.title,
    description: readinessCopy.description,
    badges: [
      readinessBadge(readiness),
      { label: modeLabel, tone: 'info' },
      hotpostSourceLabel(payload),
      hotpostConfidenceBadge(payload),
    ],
    metrics: [
      {
        label: payload.mode === 'opportunity' ? '最值得追的机会' : payload.mode === 'rant' ? '最明显的抱怨' : '最热的话题',
        value: primaryAngle,
      },
      {
        label: '最值得盯的社区',
        value: leadCommunity.name,
      },
      {
        label: '证据强度',
        value: `${payload.evidence_count} 条`,
        help: `${communityCount} 个社区共同支撑这次判断。`,
      },
      {
        label: '下一步',
        value: payload.next_steps?.deepdive_available ? '可深挖' : '先快扫',
        help: payload.next_steps?.deepdive_available ? '已经满足继续生成深度报告的条件' : '建议先确认热度真假再深挖',
      },
    ],
    nextSteps,
    warning: readinessCopy.warning,
    warningTitle: readinessCopy.warningTitle,
    warningNextStep: readinessCopy.warningNextStep,
  };
};

export const buildHotpostDecisionSummary = (payload: HotPostResponse): ProductDecisionSummary => {
  const readiness = resolveHotpostReadiness(payload);
  const topOpportunity =
    payload.unmet_needs?.[0]?.need ||
    payload.unmet_needs?.[0]?.summary ||
    payload.opportunities?.[0]?.need ||
    payload.opportunities?.[0]?.summary;
  const topPain =
    payload.pain_points?.[0]?.category ||
    payload.pain_points?.[0]?.description;
  const topTopic = payload.topics?.[0]?.topic;
  const primaryReason =
    payload.mode === 'opportunity'
      ? toUserFacingSnippet(topOpportunity || payload.summary, '用户需求开始重复出现，值得继续验证。')
      : payload.mode === 'rant'
        ? toUserFacingSnippet(topPain || payload.summary, '用户抱怨开始聚焦，值得继续验证。')
        : toUserFacingSnippet(
            payload.topics?.[0]?.key_takeaway || topTopic || payload.summary,
            '核心话题开始集中，值得继续验证。',
          );
  const secondaryReason =
    payload.mode === 'opportunity'
      ? '同一需求在重复出现，值得继续追。'
      : payload.mode === 'rant'
        ? '抱怨已经开始聚焦，值得判断是不是稳定痛点。'
        : '话题已经开始集中，值得判断是真热还是短噪音。';

  return {
    verdictTitle:
      readiness === 'ready'
        ? '值得马上继续追'
      : readiness === 'directional'
          ? '先定追不追'
          : '先把这波当方向线索',
    verdictDescription:
      readiness === 'ready'
        ? '这次快扫已经够你先拍板。'
        : readiness === 'directional'
          ? '这次快扫已经够你先定追不追。'
          : '这次更适合先看方向和真伪。',
    reasons: [
      {
        title: '用户现在最在意什么',
        description: primaryReason,
      },
      {
        title: '为什么这波值得继续看',
        description: secondaryReason,
      },
    ],
    signals: [],
    nextStepTitle: '下一步动作',
    nextStepDescription: payload.next_steps?.deepdive_available
      ? '值钱就继续深挖。'
      : '拿不准就换关键词重扫。',
  };
};

export const buildHotpostActionPlan = (payload: HotPostResponse): ProductActionPlan => {
  if (payload.next_steps?.deepdive_available) {
    return {
      primaryLabel: '继续深挖',
      secondaryLabel: '先看关键证据',
      tertiaryLabel: '回搜索页重扫',
      primaryIntent: 'generate-deep-dive',
      secondaryIntent: 'review-evidence',
      tertiaryIntent: 'retry-search',
      sectionEyebrow: '下一步动作',
      sectionTitle: '这波已经够你先定追不追',
      sectionDescription: '有价值就深挖；拿不准先看证据。',
    };
  }

  return {
    primaryLabel: '先看关键证据',
    secondaryLabel: '回搜索页重扫',
    primaryIntent: 'review-evidence',
    secondaryIntent: 'retry-search',
    sectionEyebrow: '下一步动作',
    sectionTitle: '先确认真假，再决定要不要继续追',
    sectionDescription: '先看关键证据；不稳就换词重扫。',
  };
};

export const buildAdminSurfaceHero = (stats: DashboardStats, recentTasks: TaskLedgerItem[]): SurfaceHeroProps => {
  const isHealthy = stats.active_workers > 0;
  const lastTask = recentTasks[0];
  const warning = !isHealthy
    ? '当前没有活跃 worker，这不是看报告的地方，先回到控制面排查任务链。'
    : stats.cache_hit_rate < 0.3
      ? '缓存命中率偏低，系统能跑，但最近更像在硬算，值得盯一下成本和时延。'
      : null;

  return {
    eyebrow: '系统驾驶舱',
    title: isHealthy ? '今天可以放心开工' : '今天先别开新任务',
    description: '这里不回答市场值不值，只回答今天这套机器能不能放心开工。',
    badges: [
      { label: isHealthy ? `活跃节点 ${stats.active_workers}` : '无活跃节点', tone: isHealthy ? 'success' : 'danger' },
      {
        label: `缓存命中 ${formatPercent(stats.cache_hit_rate)}`,
        tone: stats.cache_hit_rate >= 0.5 ? 'success' : stats.cache_hit_rate >= 0.3 ? 'warning' : 'danger',
      },
      {
        label: `今日完成 ${stats.tasks_completed_today} 个任务`,
        tone: stats.tasks_completed_today > 0 ? 'info' : 'warning',
      },
    ],
    metrics: [
      { label: '总用户数', value: `${stats.total_users}`, help: '累计接入的账户规模' },
      { label: '累计任务', value: `${stats.total_tasks}`, help: `今天新增 ${stats.tasks_today} 个任务` },
      { label: '平均耗时', value: `${stats.avg_processing_time}s`, help: '看系统今天跑得快不快' },
      {
        label: '最近任务',
        value: lastTask ? toAdminTaskStatusLabel(lastTask.status) : '暂时空闲',
        help: lastTask ? `最近一单来自 ${lastTask.user_email}` : '最近还没有新的任务进来',
      },
    ],
    nextSteps: [
      '先看最近任务，确认今天最新这批分析有没有正常完成。',
      '如果状态不稳，先查 worker、缓存命中和任务账本，再决定要不要继续跑新任务。',
    ],
    warning,
    warningTitle: warning ? '系统今天有提醒，先别直接看结论' : null,
    warningNextStep: warning ? '先看最近任务、worker 和缓存，再决定是否继续跑新任务。' : null,
  };
};
