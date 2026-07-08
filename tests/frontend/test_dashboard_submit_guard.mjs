import test from 'node:test';
import assert from 'node:assert/strict';

class FakeNode extends EventTarget {
  constructor(tagName = '') {
    super();
    this.tagName = String(tagName || '').toUpperCase();
    this.children = [];
    this.parentNode = null;
    this.ownerDocument = null;
    this.isConnected = false;
  }

  append(...nodes) {
    nodes.forEach((node) => this.appendChild(node));
  }

  appendChild(node) {
    node.parentNode = this;
    node.ownerDocument = this.ownerDocument;
    this.children.push(node);
    return node;
  }

  querySelector() {
    return null;
  }
}

class FakeHTMLElement extends FakeNode {
  constructor(tagName = 'div') {
    super(tagName);
    this.style = { setProperty() {} };
  }

  attachShadow() {
    this.shadowRoot = new FakeNode('#shadow-root');
    this.shadowRoot.ownerDocument = this.ownerDocument;
    return this.shadowRoot;
  }
}

class FakeDocument extends FakeNode {
  constructor() {
    super('#document');
    this.ownerDocument = this;
    this.hidden = false;
    this.body = new FakeHTMLElement('body');
    this.body.ownerDocument = this;
  }

  createElement(tagName) {
    const ctor = globalThis.customElements.get(tagName);
    const element = ctor ? new ctor() : new FakeHTMLElement(tagName);
    element.tagName = String(tagName).toUpperCase();
    element.ownerDocument = this;
    return element;
  }
}

function installDomGlobals() {
  const registry = new Map();
  globalThis.HTMLElement = FakeHTMLElement;
  globalThis.document = new FakeDocument();
  globalThis.CustomEvent = class CustomEvent extends Event {
    constructor(type, options = {}) {
      super(type, options);
      this.detail = options.detail;
    }
  };
  globalThis.customElements = {
    define(name, ctor) {
      registry.set(name, ctor);
    },
    get(name) {
      return registry.get(name);
    },
  };
  globalThis.window = new EventTarget();
  globalThis.window.location = { origin: 'http://localhost' };
  globalThis.window.setTimeout = setTimeout;
  globalThis.window.clearTimeout = clearTimeout;
  globalThis.window.addEventListener = globalThis.window.addEventListener.bind(globalThis.window);
  globalThis.window.removeEventListener = globalThis.window.removeEventListener.bind(globalThis.window);
}

installDomGlobals();
await import('../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js');

test('dashboard shopping submit event guard ignores duplicate submits while the first API call is running', async () => {
  const DashboardPanel = customElements.get('grocy-ai-dashboard-panel');
  const panel = new DashboardPanel();
  let releaseSearch;
  let apiCalls = 0;

  panel._api.searchProduct = async () => {
    apiCalls += 1;
    await new Promise((resolve) => {
      releaseSearch = resolve;
    });
    return {
      response: { ok: true },
      payload: { success: true, message: 'Produkt verarbeitet.' },
    };
  };
  panel._getDashboardApiOrThrow = async () => panel._api;
  panel._loadShoppingList = async () => {};
  panel._shoppingSearch.actions.setQuery('Milch');
  panel._bindEvents();

  panel.shadowRoot.dispatchEvent(new CustomEvent('shopping-submit-query'));
  await Promise.resolve();
  panel.shadowRoot.dispatchEvent(new CustomEvent('shopping-submit-query'));
  await Promise.resolve();

  assert.equal(apiCalls, 1);
  assert.doesNotMatch(panel._store.getState().topbarStatus, /Fehler/i);

  releaseSearch();
  await new Promise((resolve) => setTimeout(resolve, 0));
});
