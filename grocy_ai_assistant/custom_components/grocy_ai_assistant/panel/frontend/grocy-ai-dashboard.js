const PANEL_SLUG = 'grocy-ai';
const PANEL_TITLE = 'Grocy AI Dashboard';
const DEFAULT_LEGACY_URL = '/api/hassio_ingress/grocy_ai_assistant/';
const STYLE_URL = new URL('./grocy-ai-dashboard.css', import.meta.url);

class GrocyAIDashboardPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this._route = null;
    this._panel = null;
    this._narrow = false;
    this._boundHandleOpenLegacy = () => this._openLegacyDashboard();
  }

  connectedCallback() {
    this._render();
  }

  disconnectedCallback() {
    const legacyButton = this.shadowRoot?.getElementById('open-legacy-dashboard');
    legacyButton?.removeEventListener('click', this._boundHandleOpenLegacy);
  }

  set hass(value) {
    this._hass = value;
    this._render();
  }

  set route(value) {
    this._route = value;
    this._render();
  }

  set panel(value) {
    this._panel = value;
    this._render();
  }

  set narrow(value) {
    this._narrow = Boolean(value);
    this._render();
  }

  _getPanelConfig() {
    return this._panel?.config ?? {};
  }

  _getLegacyDashboardUrl() {
    return this._getPanelConfig().legacy_dashboard_url || DEFAULT_LEGACY_URL;
  }

  _getUserLabel() {
    return this._hass?.user?.name || this._hass?.user?.id || 'Unbekannter Benutzer';
  }

  _getRouteLabel() {
    return this._route?.path || this._route?.prefix || `/${PANEL_SLUG}`;
  }

  _getThemeSummary() {
    const styles = getComputedStyle(this);
    const primary = styles.getPropertyValue('--primary-color').trim() || 'nicht gesetzt';
    const background = styles.getPropertyValue('--primary-background-color').trim() || 'nicht gesetzt';
    return { primary, background };
  }

  _openLegacyDashboard() {
    window.location.assign(this._getLegacyDashboardUrl());
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }

    const theme = this._getThemeSummary();

    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="${STYLE_URL.href}">
      <section class="page-shell">
        <header class="hero-card">
          <div>
            <p class="eyebrow">Grocy AI Assistant</p>
            <h1>${PANEL_TITLE}</h1>
            <p class="description">
              Dieses Dashboard läuft jetzt als natives Home-Assistant-Panel. Das Frontend-Modul erhält den aktuellen
              <code>hass</code>-Status, Routing-Kontext und die aktiven Theme-Variablen direkt aus Home Assistant.
            </p>
          </div>
          <button id="open-legacy-dashboard" type="button">Legacy-Dashboard öffnen</button>
        </header>

        <section class="context-grid">
          <article class="info-card">
            <h2>Home Assistant Kontext</h2>
            <dl>
              <div>
                <dt>Benutzer</dt>
                <dd>${this._escapeHtml(this._getUserLabel())}</dd>
              </div>
              <div>
                <dt>Schmale Ansicht</dt>
                <dd>${this._narrow ? 'Ja' : 'Nein'}</dd>
              </div>
              <div>
                <dt>Route</dt>
                <dd><code>${this._escapeHtml(this._getRouteLabel())}</code></dd>
              </div>
            </dl>
          </article>

          <article class="info-card">
            <h2>Theme-Variablen</h2>
            <dl>
              <div>
                <dt>--primary-color</dt>
                <dd>${this._escapeHtml(theme.primary)}</dd>
              </div>
              <div>
                <dt>--primary-background-color</dt>
                <dd>${this._escapeHtml(theme.background)}</dd>
              </div>
              <div>
                <dt>Legacy-Fallback</dt>
                <dd><code>${this._escapeHtml(this._getLegacyDashboardUrl())}</code></dd>
              </div>
            </dl>
          </article>
        </section>

        <article class="info-card roadmap-card">
          <h2>Natives Frontend-Bundle aktiv</h2>
          <p>
            Die Sidebar-Route <code>/${PANEL_SLUG}</code> bleibt stabil. Weitere Dashboard-Inhalte können nun schrittweise
            direkt im Home-Assistant-Frontend gerendert werden, ohne dass ein iframe benötigt wird.
          </p>
        </article>
      </section>
    `;

    const legacyButton = this.shadowRoot.getElementById('open-legacy-dashboard');
    legacyButton?.addEventListener('click', this._boundHandleOpenLegacy);
  }

  _escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }
}

if (!customElements.get('grocy-ai-dashboard-panel')) {
  customElements.define('grocy-ai-dashboard-panel', GrocyAIDashboardPanel);
}
