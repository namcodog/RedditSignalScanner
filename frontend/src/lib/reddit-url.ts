export const normalizeRedditUrl = (url?: string | null, permalink?: string | null): string | undefined => {
  const collapseDuplicatePrefix = (value: string) =>
    value
      .trim()
      .replace(
        /^https?:\/\/(?:www\.)?reddit\.comhttps?:\/\/(?:www\.)?reddit\.com/i,
        'https://www.reddit.com',
      );

  const direct = collapseDuplicatePrefix(url || '');
  const fallback = collapseDuplicatePrefix(permalink || '');
  const permalinkUrl =
    fallback.startsWith('http://') || fallback.startsWith('https://')
      ? fallback
      : fallback.startsWith('/')
        ? `https://www.reddit.com${fallback}`
        : undefined;

  const isMediaAsset = (value: string) =>
    value.includes('i.redd.it/') ||
    value.includes('preview.redd.it/') ||
    value.includes('external-preview.redd.it/');

  if (direct.startsWith('http://') || direct.startsWith('https://')) {
    if (permalinkUrl && isMediaAsset(direct)) {
      return permalinkUrl;
    }
    return direct;
  }
  if (direct.startsWith('/')) {
    return `https://www.reddit.com${direct}`;
  }

  return permalinkUrl;
};
