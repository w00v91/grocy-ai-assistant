const INGRESS_PREFIX_PATTERN = /^\/api\/hassio_ingress\/[^/]+/;

function normalizeBasePath(value) {
  const normalized = String(value || '').trim().replace(/\/+$/, '');
  return normalized || '';
}

export function detectIngressBasePath(pathname = '') {
  const match = String(pathname || '').match(INGRESS_PREFIX_PATTERN);
  return match ? match[0] : '';
}

export async function resolveDashboardApiBasePath({ panelConfig = {}, location = null } = {}) {
  const configuredApiBasePath = normalizeBasePath(
    panelConfig.dashboard_api_base_path || panelConfig.api_base_path,
  );
  if (configuredApiBasePath) return configuredApiBasePath;

  const ingressBasePath = detectIngressBasePath(location?.pathname || '');
  if (ingressBasePath) return ingressBasePath;

  return '';
}

export function buildLegacyDashboardUrl(apiBasePath, fallbackUrl = '') {
  const normalizedApiBasePath = normalizeBasePath(apiBasePath);
  if (normalizedApiBasePath) return `${normalizedApiBasePath}/`;

  const normalizedFallbackUrl = String(fallbackUrl || '').trim();
  return normalizedFallbackUrl || '/';
}
