/**
 * College Connect - Client-side Script
 * Handles health monitoring modal and UI enhancements
 */

/**
 * Queries /health using fetch() and updates the health status modal UI
 */
async function fetchHealthStatus() {
    const statusContainer = document.getElementById('healthStatusContent');
    if (!statusContainer) return;

    // Loading State
    statusContainer.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-success mb-3" role="status" style="width: 2.5rem; height: 2.5rem;">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-secondary fw-medium mb-0">Querying backend health endpoint (/health)...</p>
        </div>
    `;

    const startTime = performance.now();

    try {
        const response = await fetch('/health', {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            cache: 'no-store'
        });

        const latency = Math.round(performance.now() - startTime);

        if (!response.ok) {
            throw new Error(`Server returned HTTP ${response.status}`);
        }

        const data = await response.json();

        // Check health status from JSON payload
        if (data.status && data.status.toLowerCase() === 'healthy') {
            statusContainer.innerHTML = `
                <div class="p-3 mb-3 bg-white rounded-3 border border-success-subtle shadow-sm">
                    <div class="d-flex align-items-center justify-content-between mb-2">
                        <div class="d-flex align-items-center gap-2">
                            <span class="status-indicator-dot healthy"></span>
                            <span class="fw-bold fs-5 text-success">Backend Status: Healthy</span>
                        </div>
                        <span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-1 rounded-pill fw-semibold">
                            HTTP 200 OK
                        </span>
                    </div>
                    <p class="text-secondary small mb-0">
                        The Flask backend server is running smoothly and actively responding to requests.
                    </p>
                </div>

                <div class="bg-white rounded-3 p-3 border shadow-sm">
                    <h6 class="fw-bold text-dark border-bottom pb-2 mb-3">
                        <i class="bi bi-info-circle text-success me-1"></i> Diagnostic Information
                    </h6>
                    <div class="row g-2 small">
                        <div class="col-6 text-muted">Service Name:</div>
                        <div class="col-6 fw-bold text-dark text-end">${data.service || 'College Connect'}</div>

                        <div class="col-6 text-muted">Application Version:</div>
                        <div class="col-6 fw-bold text-dark text-end">v${data.version || '1.0.0'}</div>

                        <div class="col-6 text-muted">Response Latency:</div>
                        <div class="col-6 fw-bold text-success text-end">${latency} ms</div>

                        <div class="col-6 text-muted">Server Timestamp:</div>
                        <div class="col-6 fw-semibold text-secondary text-end">${data.timestamp ? new Date(data.timestamp).toLocaleString() : 'N/A'}</div>
                    </div>
                </div>
            `;
        } else {
            throw new Error(data.message || 'Server reported degraded or unhealthy status');
        }
    } catch (error) {
        statusContainer.innerHTML = `
            <div class="p-3 mb-3 bg-white rounded-3 border border-danger-subtle shadow-sm">
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <div class="d-flex align-items-center gap-2">
                        <span class="status-indicator-dot unavailable"></span>
                        <span class="fw-bold fs-5 text-danger">Backend Status: Unavailable</span>
                    </div>
                    <span class="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-1 rounded-pill fw-semibold">
                        Offline / Error
                    </span>
                </div>
                <p class="text-secondary small mb-0">
                    Could not receive a healthy response from the backend /health endpoint.
                </p>
            </div>

            <div class="bg-white rounded-3 p-3 border shadow-sm">
                <h6 class="fw-bold text-dark border-bottom pb-2 mb-3">
                    <i class="bi bi-exclamation-triangle text-danger me-1"></i> Failure Details
                </h6>
                <div class="row g-2 small">
                    <div class="col-6 text-muted">Service Name:</div>
                    <div class="col-6 fw-bold text-dark text-end">College Connect</div>

                    <div class="col-6 text-muted">Application Version:</div>
                    <div class="col-6 fw-bold text-dark text-end">v1.0.0</div>

                    <div class="col-6 text-muted">Error Message:</div>
                    <div class="col-6 text-danger fw-semibold text-end">${error.message}</div>
                </div>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Health Modal Event Listeners
    const healthModal = document.getElementById('healthModal');
    if (healthModal) {
        healthModal.addEventListener('show.bs.modal', () => {
            fetchHealthStatus();
        });
    }

    const recheckBtn = document.getElementById('recheckHealthBtn');
    if (recheckBtn) {
        recheckBtn.addEventListener('click', () => {
            fetchHealthStatus();
        });
    }
});

