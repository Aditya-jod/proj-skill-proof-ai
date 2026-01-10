const tableBody = document.getElementById('session-table-body');
const connectionStatus = document.getElementById('connection-status');
const activeUsersCard = document.getElementById('active-users-card');
const integrityFlagsCard = document.getElementById('integrity-flags-card');
const solvedCountCard = document.getElementById('solved-count-card');

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
        const data = JSON.parse(event.data);
        const userId = data.user_id;

        if (!userId) return;

        if (!userSessions[userId]) {
            userSessions[userId] = {
                status: 'Configuring',
                lastEvent: 'Session Started',
                integrityFlags: 0,
                lastUpdate: new Date(),
                solved: 0
            };
        }

        const session = userSessions[userId];
        session.lastEvent = data.event;
        session.lastUpdate = new Date();

        switch (data.event) {
            case 'session_start':
                session.status = 'Configuring';
                break;
            case 'focus_lost':
                session.integrityFlags++;
                session.status = 'Suspicious';
                break;
            case 'focus_gained':
                session.status = 'Active';
                break;
            case 'code_submitted':
                session.status = 'Evaluating';
                if (data.evaluation && data.evaluation.status === 'passed') {
                    session.solved++;
                    session.status = 'Solved';
                }
                break;
            case 'problem_assigned':
                session.status = 'Active';
                break;
        }

        if (data.integrity_decision === 'pause') {
            session.status = 'Suspicious';
        }
        if (data.status === 'terminated') {
            session.status = 'Terminated';
        }

        renderDashboard();

    } catch (e) {
        console.error("Error parsing message: ", event.data, e);
    }
};

socket.onclose = function() {
    connectionStatus.textContent = "Disconnected";
    connectionStatus.previousElementSibling.classList.remove('bg-success');
    connectionStatus.previousElementSibling.classList.add('bg-danger');
};

function renderDashboard() {
    tableBody.innerHTML = '';
    let totalFlags = 0;
    let totalSolved = 0;

    const sortedUsers = Object.keys(userSessions).sort((a, b) => 
        userSessions[b].lastUpdate - userSessions[a].lastUpdate
    );

    for (const userId of sortedUsers) {
        const session = userSessions[userId];
        totalFlags += session.integrityFlags;
        totalSolved += session.solved;

        const row = document.createElement('tr');
        const flagClass = session.integrityFlags > 2 ? 'flag-high' : session.integrityFlags > 0 ? 'flag-medium' : '';
        
        let statusIcon = 'bi-person';
        let statusClass = 'status-active';
        if (session.status === 'Suspicious') { statusIcon = 'bi-eye-slash'; statusClass = 'status-suspicious'; }
        if (session.status === 'Evaluating') { statusIcon = 'bi-hourglass-split'; statusClass = 'status-evaluating'; }
        if (session.status === 'Configuring') { statusIcon = 'bi-gear'; statusClass = 'status-configuring'; }
        if (session.status === 'Solved') { statusIcon = 'bi-check2-circle'; statusClass = 'status-active'; }


        row.innerHTML = `
            <td>${userId}</td>
            <td><i class="bi ${statusIcon} ${statusClass} status-icon me-2"></i>${session.status}</td>
            <td>${session.lastEvent}</td>
            <td><span class="badge rounded-pill ${flagClass}">${session.integrityFlags}</span></td>
            <td>${session.lastUpdate.toLocaleTimeString()}</td>
        `;
        tableBody.appendChild(row);
    }

    // Update summary cards
    activeUsersCard.textContent = Object.keys(userSessions).length;
    integrityFlagsCard.textContent = totalFlags;
    solvedCountCard.textContent = totalSolved;
}
