export function createDashboardStore(initialState = {}) {
  let state = structuredCloneSafe(initialState);
  const listeners = new Set();

  function notify() {
    listeners.forEach((listener) => listener(state));
  }

  return {
    getState() {
      return state;
    },
    subscribe(listener) {
      listeners.add(listener);
      listener(state);
      return () => listeners.delete(listener);
    },
    set(key, value) {
      state = { ...state, [key]: value };
      notify();
      return value;
    },
    patch(partialState = {}) {
      state = { ...state, ...partialState };
      notify();
      return state;
    },
    getIn(path, fallback = undefined) {
      return getValueAtPath(state, path, fallback);
    },
    setIn(path, value) {
      state = setValueAtPath(state, path, value);
      notify();
      return value;
    },
    patchIn(path, partialState = {}) {
      const currentValue = getValueAtPath(state, path, {});
      const nextValue = currentValue && typeof currentValue === 'object'
        ? { ...currentValue, ...partialState }
        : { ...partialState };
      state = setValueAtPath(state, path, nextValue);
      notify();
      return nextValue;
    },
    updateIn(path, updater) {
      const currentValue = getValueAtPath(state, path);
      const nextValue = updater(currentValue);
      if (typeof nextValue === 'undefined') {
        return currentValue;
      }
      state = setValueAtPath(state, path, nextValue);
      notify();
      return nextValue;
    },
    update(updater) {
      const nextState = updater(state);
      state = nextState && typeof nextState === 'object' ? nextState : state;
      notify();
      return state;
    },
  };
}

function structuredCloneSafe(value) {
  if (typeof structuredClone === 'function') {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value));
}

function normalizePath(path) {
  if (Array.isArray(path)) return path.filter((segment) => segment !== '');
  if (typeof path === 'string') {
    return path.split('.').map((segment) => segment.trim()).filter(Boolean);
  }
  return [];
}

function getValueAtPath(source, path, fallback = undefined) {
  const segments = normalizePath(path);
  if (!segments.length) return typeof source === 'undefined' ? fallback : source;

  let cursor = source;
  for (const segment of segments) {
    if (!cursor || typeof cursor !== 'object' || !(segment in cursor)) {
      return fallback;
    }
    cursor = cursor[segment];
  }

  return typeof cursor === 'undefined' ? fallback : cursor;
}

function setValueAtPath(source, path, value) {
  const segments = normalizePath(path);
  if (!segments.length) return value;

  const [head, ...tail] = segments;
  const currentSource = source && typeof source === 'object' ? source : {};
  return {
    ...currentSource,
    [head]: tail.length
      ? setValueAtPath(currentSource[head], tail, value)
      : value,
  };
}
