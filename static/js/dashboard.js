const tableBody = document.getElementById('session-table-body');
const connectionStatus = document.getElementById('connection-status');
const clientId = "admin_" + Math.random().toString(36).substr(2, 9);
const socket = new WebSocket(`ws://localhost:8000/ws/${clientId}`);

// In-memory store for user session data
const userSessions = {};

socket.onopen = function() {
    connectionStatus.textContent = "Connected";
    connectionStatus.previousElementSibling.classList.remove('bg-danger');
    connectionStatus.previousElementSibling.classList.add('bg-success');
};

socket.onmessage = function(event) {
    try {
        // The backend now sends stringified JSON, so we need to parse it twice.
        // This is a temporary workaround for the eval call.
        const rawData = event.data.replace(/'/g, '"'); // Replace single quotes with double
        const data = JSON.parse(rawData);
        const userId = data.user_id;

        if (!userId) return;

        // Initialize user session if it's the first time we see them
        if (!userSessions[userId]) {
            userSessions[userId] = {
                status: 'Active',
                lastEvent: 'Session Started',
                integrityFlags: 0,
                lastUpdate: new Date()
            };
        }

        // Update session data based on the event
        const session = userSessions[userId];
        session.lastEvent = data.type;
        session.lastUpdate = new Date();

        if (data.type === 'focus_lost') {
            session.integrityFlags++;
            session.status = 'Suspicious';
        }
        if (data.type === 'focus_gained') {
            session.status = 'Active';
        }
        if (data.type === 'code_submitted') {
            session.status = 'Evaluating';
        }
        if (data.type === 'session_start') {
            session.status = 'Configuring';
        }

        // Re-render the table
        renderTable();

    } catch (e) {
        console.error("Received non-JSON message or malformed data: ", event.data, e);
    }
};

socket.onclose = function() {
    connectionStatus.textContent = "Disconnected";
    connectionStatus.previousElementSibling.classList.remove('bg-success');
    connectionStatus.previousElementSibling.classList.add('bg-danger');
};

function renderTable() {
    // Clear existing table body
    tableBody.innerHTML = '';

    for (const userId in userSessions) {
        const session = userSessions[userId];
        const row = document.createElement('tr');

        const flagClass = session.integrityFlags > 0 ? 'bg-warning text-dark' : 'bg-light';

        row.innerHTML = `
            <td>${userId}</td>
            <td>${session.status}</td>
            <td>${session.lastEvent}</td>
            <td><span class="badge ${flagClass}">${session.integrityFlags}</span></td>
            <td>${session.lastUpdate.toLocaleTimeString()}</td>
        `;
        tableBody.appendChild(row);
    }
}
