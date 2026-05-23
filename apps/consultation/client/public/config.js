(function initMcsApiBase() {
  if (window.__MCS_API_BASE__) {
    return;
  }

  if (window.location.protocol === "https:") {
    window.__MCS_API_BASE__ = `${window.location.origin}/api/v1`;
    return;
  }

  const apiOrigin = `${window.location.protocol}//${window.location.hostname}:18080`;
  window.__MCS_API_BASE__ = `${apiOrigin}/api/v1`;
})();
