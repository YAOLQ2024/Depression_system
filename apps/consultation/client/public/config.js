(function initMcsApiBase() {
  if (window.__MCS_API_BASE__) {
    return;
  }

  const apiOrigin = `${window.location.protocol}//${window.location.hostname}:18080`;
  window.__MCS_API_BASE__ = `${apiOrigin}/api/v1`;
})();
