function defaultGetPayload(item) {
  const payloadText = decodeURIComponent(item?.dataset?.shoppingItem || item?.dataset?.swipePayload || '');
  return payloadText ? JSON.parse(payloadText) : {};
}

export function resetSwipeVisualState(item) {
  if (!item) return;
  item.classList.remove('dragging', 'swipe-commit-left', 'swipe-commit-right');
  item.style.setProperty('--swipe-offset', '0px');
  item.style.setProperty('--swipe-progress-left', '0');
  item.style.setProperty('--swipe-progress-right', '0');
  item.style.setProperty('--swipe-glow', 'transparent');
}

export function bindSwipeInteractions({
  root = document,
  selector,
  getPayload = defaultGetPayload,
  onSwipeLeft,
  onSwipeRight,
  onTap,
  interactiveElementSelector = '',
  commitDistance = 75,
  maxDistance = 132,
} = {}) {
  if (!root?.querySelectorAll || !selector) {
    return () => {};
  }

  const items = Array.from(root.querySelectorAll(selector));
  const abortController = typeof AbortController === 'function' ? new AbortController() : null;
  const signalOptions = abortController ? { signal: abortController.signal } : undefined;
  const manualCleanup = [];

  items.forEach((item) => {
    let startX = 0;
    let startY = 0;
    let deltaX = 0;
    let horizontalDragLocked = false;
    let pointerId = null;
    let isDragging = false;
    let lastTouchStartAt = 0;

    resetSwipeVisualState(item);

    const beginInteraction = ({ clientX, clientY }) => {
      startX = clientX;
      startY = clientY;
      deltaX = 0;
      horizontalDragLocked = false;
      isDragging = true;
      item.classList.remove('swipe-commit-left', 'swipe-commit-right');
      item.classList.add('dragging');
    };

    const updateInteraction = ({ clientX, clientY, cancelable = false, preventDefault = null }) => {
      if (!isDragging) {
        return;
      }

      const distanceX = clientX - startX;
      const distanceY = clientY - startY;
      if (!horizontalDragLocked) {
        if (Math.abs(distanceY) > Math.abs(distanceX) && Math.abs(distanceY) > 10) {
          isDragging = false;
          pointerId = null;
          resetSwipeVisualState(item);
          return;
        }

        if (Math.abs(distanceX) > 6) {
          horizontalDragLocked = true;
        }
      }

      if (horizontalDragLocked && cancelable && typeof preventDefault === 'function') {
        preventDefault();
      }

      const dragScale = 0.8;
      deltaX = Math.max(-maxDistance, Math.min(maxDistance, distanceX * dragScale));

      const rightProgress = Math.min(Math.max(deltaX / commitDistance, 0), 1);
      const leftProgress = Math.min(Math.max((-deltaX) / commitDistance, 0), 1);
      const glow = deltaX >= 0 ? 'rgba(22, 163, 74, 0.7)' : 'rgba(239, 68, 68, 0.7)';

      item.style.setProperty('--swipe-offset', `${deltaX}px`);
      item.style.setProperty('--swipe-progress-left', leftProgress.toFixed(3));
      item.style.setProperty('--swipe-progress-right', rightProgress.toFixed(3));
      item.style.setProperty('--swipe-glow', glow);
    };

    const handlePointerDown = (event) => {
      if (interactiveElementSelector && event.target?.closest?.(interactiveElementSelector)) {
        return;
      }
      if (event.pointerType === 'touch' && (Date.now() - lastTouchStartAt) < 800) {
        return;
      }

      pointerId = event.pointerId;
      beginInteraction({ clientX: event.clientX, clientY: event.clientY });
      if (typeof item.setPointerCapture === 'function') {
        item.setPointerCapture(pointerId);
      }
    };

    const handlePointerMove = (event) => {
      if (!isDragging || event.pointerId !== pointerId) {
        return;
      }
      updateInteraction({ clientX: event.clientX, clientY: event.clientY });
    };

    const handlePointerCancel = () => {
      isDragging = false;
      pointerId = null;
      resetSwipeVisualState(item);
    };

    const handlePointerUp = async (event) => {
      if (!isDragging || event.pointerId !== pointerId) {
        return;
      }

      isDragging = false;
      if (typeof item.hasPointerCapture === 'function' && item.hasPointerCapture(pointerId)) {
        item.releasePointerCapture(pointerId);
      }
      pointerId = null;
      item.classList.remove('dragging');

      const payload = getPayload(item);

      if (deltaX <= -commitDistance) {
        item.classList.add('swipe-commit-left');
        if (onSwipeLeft) await onSwipeLeft(item, payload);
        return;
      }

      if (deltaX >= commitDistance) {
        item.classList.add('swipe-commit-right');
        if (onSwipeRight) await onSwipeRight(item, payload);
        return;
      }

      if (Math.abs(deltaX) < 14 && onTap) {
        onTap(item, payload);
      }

      resetSwipeVisualState(item);
    };

    const getPrimaryTouch = (event) => event.touches?.[0] || event.changedTouches?.[0] || null;

    const handleTouchStart = (event) => {
      if (interactiveElementSelector && event.target?.closest?.(interactiveElementSelector)) {
        return;
      }

      const touch = getPrimaryTouch(event);
      if (!touch) return;

      lastTouchStartAt = Date.now();
      beginInteraction({ clientX: touch.clientX, clientY: touch.clientY });
    };

    const handleTouchMove = (event) => {
      if (!isDragging) return;
      const touch = getPrimaryTouch(event);
      if (!touch) return;
      updateInteraction({
        clientX: touch.clientX,
        clientY: touch.clientY,
        cancelable: event.cancelable,
        preventDefault: () => event.preventDefault(),
      });
    };

    const handleTouchCancel = () => {
      isDragging = false;
      pointerId = null;
      resetSwipeVisualState(item);
    };

    const handleTouchEnd = async (event) => {
      if (!isDragging) {
        return;
      }

      const touch = getPrimaryTouch(event);
      if (touch) {
        updateInteraction({
          clientX: touch.clientX,
          clientY: touch.clientY,
          cancelable: event.cancelable,
          preventDefault: () => event.preventDefault(),
        });
      }

      isDragging = false;
      pointerId = null;
      item.classList.remove('dragging');

      const payload = getPayload(item);

      if (deltaX <= -commitDistance) {
        item.classList.add('swipe-commit-left');
        if (onSwipeLeft) await onSwipeLeft(item, payload);
        return;
      }

      if (deltaX >= commitDistance) {
        item.classList.add('swipe-commit-right');
        if (onSwipeRight) await onSwipeRight(item, payload);
        return;
      }

      if (Math.abs(deltaX) < 14 && onTap) {
        onTap(item, payload);
      }

      resetSwipeVisualState(item);
    };

    item.addEventListener('pointerdown', handlePointerDown, signalOptions);
    item.addEventListener('pointermove', handlePointerMove, signalOptions);
    item.addEventListener('pointercancel', handlePointerCancel, signalOptions);
    item.addEventListener('pointerup', handlePointerUp, signalOptions);
    item.addEventListener('touchstart', handleTouchStart, { ...signalOptions, passive: true });
    item.addEventListener('touchmove', handleTouchMove, { ...signalOptions, passive: false });
    item.addEventListener('touchcancel', handleTouchCancel, signalOptions);
    item.addEventListener('touchend', handleTouchEnd, signalOptions);

    if (!abortController) {
      manualCleanup.push(() => {
        item.removeEventListener('pointerdown', handlePointerDown);
        item.removeEventListener('pointermove', handlePointerMove);
        item.removeEventListener('pointercancel', handlePointerCancel);
        item.removeEventListener('pointerup', handlePointerUp);
        item.removeEventListener('touchstart', handleTouchStart);
        item.removeEventListener('touchmove', handleTouchMove);
        item.removeEventListener('touchcancel', handleTouchCancel);
        item.removeEventListener('touchend', handleTouchEnd);
      });
    }
  });

  return () => {
    if (abortController) {
      abortController.abort();
    }
    manualCleanup.forEach((cleanup) => cleanup());
    items.forEach((item) => resetSwipeVisualState(item));
  };
}
