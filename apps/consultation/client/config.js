(function initMcsApiBase() {
  if (typeof window.__MCS_PERFORMANCE_MODE__ !== "boolean") {
    window.__MCS_PERFORMANCE_MODE__ = true;
  }

  if (window.__MCS_API_BASE__) {
    return;
  }

  const apiOrigin = `${window.location.protocol}//${window.location.hostname}:18080`;
  window.__MCS_API_BASE__ = `${apiOrigin}/api/v1`;
})();
