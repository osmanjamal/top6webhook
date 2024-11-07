// تهيئة متغيرات عامة
let currentModal = null;

// وظائف إنشاء المكونات
function createAction() {
    showModal('Create New Action', `
        <form id="createActionForm">
            <div class="mb-3">
                <label class="form-label">Action Name</label>
                <input type="text" class="form-control" id="actionName" required>
                <small class="text-muted">Use PascalCase, e.g., "MyAction"</small>
            </div>
            <button type="submit" class="btn btn-primary w-100">Create Action</button>
        </form>
    `);

    $('#createActionForm').on('submit', async function(e) {
        e.preventDefault();
        const actionName = $('#actionName').val();
        try {
            const response = await fetch('/api/action/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: actionName })
            });
            if (response.ok) {
                showAlert('success', `Action ${actionName} created successfully!`);
                refreshComponents();
                closeModal();
            } else {
                throw new Error(await response.text());
            }
        } catch (error) {
            showAlert('danger', `Error creating action: ${error.message}`);
        }
    });
}

function createEvent() {
    showModal('Create New Event', `
        <form id="createEventForm">
            <div class="mb-3">
                <label class="form-label">Event Name</label>
                <input type="text" class="form-control" id="eventName" required>
                <small class="text-muted">Use PascalCase, e.g., "MyEvent"</small>
            </div>
            <button type="submit" class="btn btn-primary w-100">Create Event</button>
        </form>
    `);

    $('#createEventForm').on('submit', async function(e) {
        e.preventDefault();
        const eventName = $('#eventName').val();
        try {
            const response = await fetch('/api/event/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: eventName })
            });
            if (response.ok) {
                showAlert('success', `Event ${eventName} created successfully!`);
                refreshComponents();
                closeModal();
            } else {
                throw new Error(await response.text());
            }
        } catch (error) {
            showAlert('danger', `Error creating event: ${error.message}`);
        }
    });
}

function linkActionEvent() {
    showModal('Link Action to Event', `
        <form id="linkForm">
            <div class="mb-3">
                <label class="form-label">Select Action</label>
                <select class="form-select" id="actionSelect" required>
                    <option value="">Choose action...</option>
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Select Event</label>
                <select class="form-select" id="eventSelect" required>
                    <option value="">Choose event...</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary w-100">Link Components</button>
        </form>
    `);

    // تحميل القوائم المنسدلة
    loadComponents();

    $('#linkForm').on('submit', async function(e) {
        e.preventDefault();
        const actionName = $('#actionSelect').val();
        const eventName = $('#eventSelect').val();
        try {
            const response = await fetch('/api/link', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    action: actionName,
                    event: eventName 
                })
            });
            if (response.ok) {
                showAlert('success', 'Components linked successfully!');
                refreshComponents();
                closeModal();
            } else {
                throw new Error(await response.text());
            }
        } catch (error) {
            showAlert('danger', `Error linking components: ${error.message}`);
        }
    });
}

// وظائف مساعدة
function showModal(title, content) {
    $('#modalTitle').text(title);
    $('.modal-body').html(content);
    currentModal = new bootstrap.Modal('#componentModal');
    currentModal.show();
}

function closeModal() {
    if (currentModal) {
        currentModal.hide();
    }
}

function showAlert(type, message) {
    const alert = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    $('#alerts').append(alert);
}

async function loadComponents() {
    try {
        const [actions, events] = await Promise.all([
            fetch('/api/actions').then(r => r.json()),
            fetch('/api/events').then(r => r.json())
        ]);

        const actionSelect = $('#actionSelect');
        const eventSelect = $('#eventSelect');

        actionSelect.empty().append('<option value="">Choose action...</option>');
        eventSelect.empty().append('<option value="">Choose event...</option>');

        actions.forEach(action => {
            actionSelect.append(`<option value="${action.name}">${action.name}</option>`);
        });

        events.forEach(event => {
            eventSelect.append(`<option value="${event.name}">${event.name}</option>`);
        });
    } catch (error) {
        showAlert('danger', 'Error loading components');
    }
}

async function refreshComponents() {
    try {
        const [actions, events] = await Promise.all([
            fetch('/api/actions').then(r => r.json()),
            fetch('/api/events').then(r => r.json())
        ]);

        updateActionsTable(actions);
        updateEventsTable(events);
    } catch (error) {
        showAlert('danger', 'Error refreshing components');
    }
}

function updateActionsTable(actions) {
    const tbody = $('#actionsTable');
    tbody.empty();

    actions.forEach(action => {
        tbody.append(`
            <tr>
                <td>${action.name}</td>
                <td>${action.linkedEvents.join(', ') || 'None'}</td>
                <td><span class="badge bg-success">Active</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteAction('${action.name}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `);
    });
}

function updateEventsTable(events) {
    const tbody = $('#eventsTable');
    tbody.empty();

    events.forEach(event => {
        tbody.append(`
            <tr>
                <td>${event.name}</td>
                <td><code>${event.key}</code></td>
                <td><span class="badge bg-success">Active</span></td>
                <td>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteEvent('${event.name}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `);
    });
}

// تهيئة الصفحة
$(document).ready(function() {
    refreshComponents();
    
    // تنفيذ التحديث كل 30 ثانية
    setInterval(refreshComponents, 30000);

    // تهيئة النماذج
    $('#apiForm').on('submit', async function(e) {
        e.preventDefault();
        try {
            const response = await fetch('/api/settings/binance', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    apiKey: $('#apiKey').val(),
                    apiSecret: $('#apiSecret').val(),
                    testnet: $('#testnetMode').is(':checked')
                })
            });
            if (response.ok) {
                showAlert('success', 'Binance settings updated successfully!');
            } else {
                throw new Error(await response.text());
            }
        } catch (error) {
            showAlert('danger', `Error updating Binance settings: ${error.message}`);
        }
    });

    $('#riskForm').on('submit', async function(e) {
        e.preventDefault();
        try {
            const response = await fetch('/api/settings/risk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    maxPosition: $('#maxPosition').val(),
                    riskPerTrade: $('#riskPerTrade').val()
                })
            });
            if (response.ok) {
                showAlert('success', 'Risk settings updated successfully!');
            } else {
                throw new Error(await response.text());
            }
        } catch (error) {
            showAlert('danger', `Error updating risk settings: ${error.message}`);
        }
    });
});

// تحديث معلومات الحساب
function updateAccountInfo() {
    $.ajax({
        url: '/api/account/info',
        method: 'GET',
        success: function(data) {
            $('#balance').text(`Balance: $${data.balance.toFixed(2)}`);
            $('#accountInfo').html(`
                <div>Margin Level: ${data.marginLevel}%</div>
                <div>Available Balance: $${data.availableBalance.toFixed(2)}</div>
            `);
        },
        error: function(xhr, status, error) {
            console.error('Error updating account info:', error);
        }
    });
}

// تحديث قائمة الأحداث النشطة
function updateActiveEvents() {
    $.ajax({
        url: '/api/events/active',
        method: 'GET',
        success: function(events) {
            const tbody = $('#eventsTable');
            tbody.empty();
            
            events.forEach(event => {
                tbody.append(`
                    <tr>
                        <td>${event.name}</td>
                        <td><code>${event.key}</code></td>
                        <td>
                            <span class="badge ${event.active ? 'bg-success' : 'bg-warning'}">
                                ${event.active ? 'Active' : 'Inactive'}
                            </span>
                        </td>
                        <td>
                            <button class="btn btn-sm btn-icon btn-outline-primary" 
                                    onclick="toggleEvent('${event.name}', ${!event.active})">
                                <i class="bi ${event.active ? 'bi-pause-fill' : 'bi-play-fill'}"></i>
                            </button>
                            <button class="btn btn-sm btn-icon btn-outline-danger" 
                                    onclick="deleteEvent('${event.name}')">
                                <i class="bi bi-trash"></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        }
    });
}

// تحديث كل البيانات
function updateDashboard() {
    updateAccountInfo();
    updateActiveEvents();
    // يمكن إضافة المزيد من التحديثات هنا
}

// بدء التحديثات التلقائية
$(document).ready(function() {
    // التحديث الأولي
    updateDashboard();
    
    // تحديث كل 30 ثانية
    setInterval(updateDashboard, 30000);
    
    // إعداد الأزرار
    $('.btn-refresh').click(function() {
        updateDashboard();
    });
});
