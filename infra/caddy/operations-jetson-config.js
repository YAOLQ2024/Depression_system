window.__MCS_API_BASE__ = window.__MCS_API_BASE__ || (
  window.location.protocol === "https:"
    ? `${window.location.origin}/api/v1`
    : `http://${window.location.hostname}:18080/api/v1`
);
