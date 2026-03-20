function resolveElement(target) {
  if (!target) return null;
  if (typeof target === 'string') return document.getElementById(target);
  return target;
}

export function byId(id) {
  return document.getElementById(id);
}

export function toggleHidden(target, hidden) {
  const element = resolveElement(target);
  if (!element) return;
  element.classList.toggle('hidden', Boolean(hidden));
}

export function toggleClass(target, className, force) {
  const element = resolveElement(target);
  if (!element) return;
  element.classList.toggle(className, force);
}

export function setText(target, text) {
  const element = resolveElement(target);
  if (!element) return;
  element.textContent = text;
}

export function renderTabSelection(activeTab, allowedTabs = ['shopping', 'recipes', 'storage', 'notifications']) {
  allowedTabs.forEach((tabName) => {
    toggleHidden(`tab-${tabName}`, activeTab !== tabName);
    toggleClass(`tab-button-${tabName}`, 'active', activeTab === tabName);
  });
}

export function updateBusyIndicator(isBusy) {
  toggleHidden('activity-spinner', !isBusy);
}

export function lockBodyScroll(scrollY) {
  if (document.body.classList.contains('modal-open')) return;
  document.body.classList.add('modal-open');
  document.body.style.top = `-${scrollY}px`;
}

export function unlockBodyScroll(scrollY) {
  if (!document.body.classList.contains('modal-open')) return;
  document.body.classList.remove('modal-open');
  document.body.style.top = '';
  window.scrollTo(0, scrollY);
}
