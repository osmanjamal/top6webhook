$(document).ready(function() {
    function getLogData() {
        $.ajax({
            url: '/logs',
            type: 'GET',
            success: function(data) {
                data.reverse();
                updateLogs(data.slice(0, 20));
            },
            error: function(error) {
                console.error('Error fetching logs:', error);
            }
        });
    }

    function updateLogs(logs) {
        const logContainer = $('#logContainer');
        logContainer.empty();

        logs.forEach(log => {
            const logEntry = $('<div>')
                .addClass('log-entry mb-2 p-2 border-bottom');

            const header = $('<div>')
                .addClass('d-flex justify-content-between mb-1');

            const source = $('<span>')
                .addClass('fw-bold text-primary')
                .text(log.parent);

            const timestamp = $('<span>')
                .addClass('text-muted small')
                .text(new Date(log.event_time).toLocaleString());

            header.append(source, timestamp);

            const message = $('<div>')
                .addClass('small')
                .text(log.event_data);

            logEntry.append(header, message);
            logContainer.append(logEntry);
        });
    }

    // Initial load
    getLogData();

    // Refresh every 5 seconds
    setInterval(getLogData, 5000);
});