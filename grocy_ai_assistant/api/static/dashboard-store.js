export function createDashboardStore(initialState = {}) {
  const state = initialState;

  return {
    state,
    get(key) {
      return state[key];
    },
    set(key, value) {
      state[key] = value;
      return value;
    },
    patch(partialState = {}) {
      Object.assign(state, partialState);
      return state;
    },
  };
}
