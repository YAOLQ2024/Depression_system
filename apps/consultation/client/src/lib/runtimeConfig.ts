/**
 * Read the deployment-time browser settings written by config.js.
 *
 * The Jetson display uses this mode because the Snap Chromium package falls
 * back to software compositing. Keeping the choice in config.js makes it
 * reversible without rebuilding the front end.
 */
export function isPerformanceMode() {
  return window.__MCS_PERFORMANCE_MODE__ === true;
}
