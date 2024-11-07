$(document).ready(function() {
    const LOG_REFRESH_INTERVAL = 5000; // 5 seconds
    let lastLogTimestamp = null;

    function formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString();
    }

    function formatLogLevel(level) {
        const levelColors = {
            'INFO': 'text-info',
            'WARNING': 'text-warning',
            'ERROR': 'text-danger',
            'SUCCESS': 'text-success'
        };
        return `<span class="${levelColors[level] || 'text-secondary'}">${level}</span>`;
    }

    function createLogEntry(log) {
        return `
            <div class="log-entry">
                <div class="d-flex justify-content-between">
                    <span class="fw-bold">${log.parent}</span>
                    <small class="text-muted">${formatTimestamp(log.event_time)}</small>
                </div>
                <div class="mt-1">
                    ${formatLogLevel(log.event_type)} ${log.event_data}
                </div>
            </div>
        `;
    }

    function updateLogs() {
        $.ajax({
            url: '/logs',
            method: 'GET',
            data: lastLogTimestamp ? { since: lastLogTimestamp } : {},
            success: function(logs) {
                if (logs.length > 0) {
                    // Update last timestamp
                    lastLogTimestamp = logs[logs.length - 1].event_time;
                    
                    // Add new logs
                    const logContainer = $('#logContainer');
                    logs.forEach(log => {
                        logContainer.prepend(createLogEntry(log));
                    });
                    
                    // Limit number of visible logs
                    const maxLogs = 100;
                    $('.log-entry:gt(' + (maxLogs - 1) + ')').remove();
                }
            },
            error: function(xhr, status, error) {
                console.error('Error fetching logs:', error);
            }
        });
    }

    // Initial load
    updateLogs();

    // Set up auto-refresh
    setInterval(updateLogs, LOG_REFRESH_INTERVAL);

    // Clear logs function
    window.clearLogs = function() {
        $.ajax({
            url: '/logs/clear',
            method: 'POST',
            success: function() {
                $('#logContainer').empty();
                lastLogTimestamp = null;
                showAlert('success', 'Logs cleared successfully');
            },
            error: function(xhr, status, error) {
                showAlert('danger', 'Error clearing logs: ' + error);
            }
        });
    };
});