import test from 'node:test';
import assert from 'node:assert/strict';

class FakeNode extends EventTarget {
  constructor(tagName = '') {
    super();
    this.tagName = String(tagName || '').toUpperCase();
    this.children = [];
    this.parentNode = null;
    this.ownerDocument = null;
    this.dataset = {};
    this.attributes = new Map();
    this.className = '';
    this.id = '';
    this.value = '';
    this.type = '';
    this.disabled = false;
    this.placeholder = '';
    this.autocomplete = '';
    this.enterKeyHint = '';
    this.textContent = '';
    this.isConnected = false;
    this.selectionStart = 0;
    this.selectionEnd = 0;
  }

  append(...nodes) {
    nodes.forEach((node) => this.appendChild(node));
  }

  appendChild(node) {
    if (!node) return node;
    node.parentNode = this;
    node.ownerDocument = this.ownerDocument;
    this.children.push(node);
    if (this.isConnected) {
      connectTree(node, this.ownerDocument);
    }
    return node;
  }

  replaceChildren(...nodes) {
    this.children.forEach((child) => disconnectTree(child));
    this.children = [];
    nodes.forEach((node) => {
      if (!node) return;
      node.parentNode = this;
      node.ownerDocument = this.ownerDocument;
      this.children.push(node);
      if (this.isConnected) {
        connectTree(node, this.ownerDocument);
      }
    });
  }

  setAttribute(name, value) {
    const normalizedValue = String(value);
    this.attributes.set(name, normalizedValue);
    if (name === 'class') this.className = normalizedValue;
    if (name === 'id') this.id = normalizedValue;
    if (name.startsWith('data-')) {
      const key = name
        .slice(5)
        .replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
      this.dataset[key] = normalizedValue;
    }
  }

  getAttribute(name) {
    if (name === 'class') return this.className;
    if (name === 'id') return this.id;
    return this.attributes.get(name) ?? null;
  }

  focus() {
    if (this.ownerDocument) {
      this.ownerDocument.activeElement = this;
    }
  }

  setSelectionRange(start, end) {
    this.selectionStart = Number(start);
    this.selectionEnd = Number(end);
  }

  matches(selector) {
    if (selector.startsWith('[')) {
      const match = selector.match(/^\[([^=]+)="([^"]+)"\]$/);
      if (!match) return false;
      const attributeName = match[1];
      if (attributeName.startsWith('data-')) {
        const dataKey = attributeName
          .slice(5)
          .replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
        return String(this.dataset[dataKey] ?? '') === match[2];
      }
      return this.getAttribute(attributeName) === match[2];
    }
    return this.tagName.toLowerCase() === selector.toLowerCase();
  }

  closest(selector) {
    let current = this;
    while (current) {
      if (current.matches?.(selector)) return current;
      current = current.parentNode;
    }
    return null;
  }

  querySelector(selector) {
    for (const child of this.children) {
      if (child.matches?.(selector)) return child;
      const nested = child.querySelector?.(selector);
      if (nested) return nested;
    }
    return null;
  }
}

class FakeHTMLElement extends FakeNode {
  constructor(tagName = 'div') {
    super(tagName);
  }
}

class FakeDocument extends FakeNode {
  constructor() {
    super('#document');
    this.ownerDocument = this;
    this.activeElement = null;
    this.body = new FakeHTMLElement('body');
    this.body.ownerDocument = this;
    this.body.isConnected = true;
  }

  createElement(tagName) {
    const ctor = globalThis.customElements.get(tagName);
    const element = ctor ? new ctor() : new FakeHTMLElement(tagName);
    element.tagName = String(tagName).toUpperCase();
    element.ownerDocument = this;
    return element;
  }
}

function connectTree(node, ownerDocument) {
  node.ownerDocument = ownerDocument;
  node.isConnected = true;
  node.connectedCallback?.();
  node.children?.forEach((child) => connectTree(child, ownerDocument));
}

function disconnectTree(node) {
  node.isConnected = false;
  node.children?.forEach((child) => disconnectTree(child));
}

function installDomGlobals() {
  const registry = new Map();
  globalThis.document = new FakeDocument();
  globalThis.HTMLElement = FakeHTMLElement;
  globalThis.CustomEvent = class CustomEvent extends Event {
    constructor(type, options = {}) {
      super(type, options);
      this.detail = options.detail;
    }
  };
  globalThis.DOMException = globalThis.DOMException || class DOMException extends Error {};
  globalThis.customElements = {
    define(name, ctor) {
      registry.set(name, ctor);
    },
    get(name) {
      return registry.get(name);
    },
  };
  globalThis.window = { location: { origin: 'http://localhost' } };
}

installDomGlobals();
await import('../../grocy_ai_assistant/custom_components/grocy_ai_assistant/panel/frontend/grocy-ai-dashboard.js');

function createBaseViewModel(overrides = {}) {
  return {
    active: true,
    status: 'Bereit.',
    list: [],
    listLoading: false,
    query: '',
    parsedAmount: null,
    variants: [],
    isLoadingVariants: false,
    isSubmitting: false,
    statusMessage: 'Bereit.',
    errorMessage: '',
    clearButtonVisible: false,
    flowState: 'idle',
    ...overrides,
  };
}

test('shopping search input keeps focus and cursor after setQuery-style updates', () => {
  const ShoppingTab = customElements.get('grocy-ai-shopping-tab');
  const tab = new ShoppingTab();
  document.body.appendChild(tab);

  tab.viewModel = createBaseViewModel();
  const searchBar = tab.querySelector('grocy-ai-shopping-search-bar');
  const input = searchBar.querySelector('[data-role="shopping-query"]');

  input.value = 'milc';
  input.focus();
  input.setSelectionRange(4, 4);

  tab.viewModel = createBaseViewModel({
    query: 'milc',
    clearButtonVisible: true,
    statusMessage: 'Tippe weiter für Live-Vorschläge oder bestätige mit Enter.',
    flowState: 'typing',
  });

  const sameSearchBar = tab.querySelector('grocy-ai-shopping-search-bar');
  const sameInput = sameSearchBar.querySelector('[data-role="shopping-query"]');
  assert.equal(sameSearchBar, searchBar);
  assert.equal(sameInput, input);
  assert.equal(document.activeElement, input);
  assert.equal(input.selectionStart, 4);
  assert.equal(input.selectionEnd, 4);
});

test('shopping search input keeps focus and cursor while variants load and settle', () => {
  const ShoppingTab = customElements.get('grocy-ai-shopping-tab');
  const tab = new ShoppingTab();
  document.body.appendChild(tab);

  tab.viewModel = createBaseViewModel({
    query: '2 Hafermilch',
    parsedAmount: 2,
    clearButtonVisible: true,
    flowState: 'typing',
    statusMessage: 'Tippe weiter für Live-Vorschläge oder bestätige mit Enter.',
  });

  const input = tab.querySelector('[data-role="shopping-query"]');
  input.focus();
  input.setSelectionRange(2, 6);

  tab.viewModel = createBaseViewModel({
    query: '2 Hafermilch',
    parsedAmount: 2,
    clearButtonVisible: true,
    flowState: 'loading_variants',
    isLoadingVariants: true,
    statusMessage: 'Lade Live-Vorschläge…',
  });

  assert.equal(document.activeElement, input);
  assert.equal(input.selectionStart, 2);
  assert.equal(input.selectionEnd, 6);

  tab.viewModel = createBaseViewModel({
    query: '2 Hafermilch',
    parsedAmount: 2,
    clearButtonVisible: true,
    flowState: 'variants_ready',
    statusMessage: 'Wähle einen Treffer oder starte die Suche mit Enter.',
    variants: [{ id: 7, name: 'Hafermilch Barista', source: 'grocy' }],
  });

  const sameInput = tab.querySelector('[data-role="shopping-query"]');
  assert.equal(sameInput, input);
  assert.equal(document.activeElement, input);
  assert.equal(input.selectionStart, 2);
  assert.equal(input.selectionEnd, 6);

  const variantButton = tab.querySelector('[data-action="shopping-select-variant"]');
  assert.ok(variantButton);

  tab.viewModel = createBaseViewModel({
    query: '2 Hafermilch',
    parsedAmount: 2,
    clearButtonVisible: true,
    flowState: 'typing',
    statusMessage: 'Keine Live-Vorschläge. Mit Enter direkt suchen.',
    variants: [{ id: 7, name: 'Hafermilch Barista', source: 'grocy' }],
  });

  assert.equal(tab.querySelector('[data-action="shopping-select-variant"]'), variantButton);
  assert.equal(document.activeElement, input);
  assert.equal(input.selectionStart, 2);
  assert.equal(input.selectionEnd, 6);
});
