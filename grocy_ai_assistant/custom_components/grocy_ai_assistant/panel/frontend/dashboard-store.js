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
