export const DEFAULT_TAB = 'shopping';
export const TAB_ORDER = ['shopping', 'recipes', 'storage'];

export function normalizeTab(tab) {
  const normalized = String(tab || '').trim().toLowerCase();
  return TAB_ORDER.includes(normalized) ? normalized : DEFAULT_TAB;
}

export function resolveTabFromLocation(locationLike, route = null) {
  const tabFromSearch = readTabFromSearch(locationLike?.search);
  if (tabFromSearch) return tabFromSearch;

  const tabFromHash = readTabFromHash(locationLike?.hash);
  if (tabFromHash) return tabFromHash;

  const tabFromRoute = readTabFromRoute(route);
  if (tabFromRoute) return tabFromRoute;

  return DEFAULT_TAB;
}

export function buildPanelUrlWithTab(locationLike, tab) {
  const url = new URL(locationLike?.href || '/', 'http://localhost');
  url.searchParams.set('tab', normalizeTab(tab));
  url.hash = '';
  return `${url.pathname}${url.search}${url.hash}`;
}

function readTabFromSearch(search) {
  const params = new URLSearchParams(search || '');
  const tab = params.get('tab');
  if (!tab) return null;
  return normalizeTab(tab);
}

function readTabFromHash(hash) {
  const normalizedHash = String(hash || '').replace(/^#/, '').trim();
  if (!normalizedHash) return null;
  const params = new URLSearchParams(normalizedHash);
  const hashTab = params.get('tab');
  if (!hashTab) return null;
  return normalizeTab(hashTab);
}

function readTabFromRoute(route) {
  const routePath = [route?.prefix, route?.path].filter(Boolean).join('/');
  const match = routePath.match(/(?:^|\/)grocy-ai\/(shopping|recipes|storage)(?:\/|$)/i);
  if (!match) return null;
  return normalizeTab(match[1]);
}
