const tableBody = document.getElementById('session-table-body');
const connectionStatus = document.getElementById('connection-status');
const liveStatus = document.getElementById('live-status');
const activeUsersCard = document.getElementById('active-users-card');
const integrityFlagsCard = document.getElementById('integrity-flags-card');
const solvedCountCard = document.getElementById('solved-count-card');
const activityFeed = document.getElementById('activity-feed');
const logoutButton = document.getElementById('admin-logout');

const clientId = typeof crypto !== 'undefined' && crypto.randomUUID
    ? `admin_${crypto.randomUUID()}`
    : `admin_${Math.random().toString(36).slice(2, 11)}`;
const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
const socket = new WebSocket(`${wsScheme}://${window.location.host}/ws/${clientId}`);

const userSessions = {};
const activityLog = [];
const MAX_ACTIVITY = 30;

if (logoutButton) {
    logoutButton.addEventListener('click', async () => {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include',
            });
        } catch (error) {
            console.warn('Failed to call logout endpoint', error);
        }
        window.location.href = '/admin/login';
    });
}

const setConnectionState = (state) => {
    const text = state === 'connected' ? 'Connected' : state === 'reconnecting' ? 'Reconnecting…' : 'Disconnected';
    connectionStatus.textContent = text;
    if (liveStatus) {
        liveStatus.dataset.state = state;
    }
};

const ensureSession = (userId) => {
    if (!userSessions[userId]) {
        userSessions[userId] = {
            status: 'Configuring',
            lastEvent: 'Session started',
            integrityFlags: 0,
            lastDecision: '—',
            lastFeedback: '—',
            lastUpdate: new Date(),
            solved: 0,
        };
    }
    return userSessions[userId];
};

const pushActivity = (entry) => {
    activityLog.unshift(entry);
    if (activityLog.length > MAX_ACTIVITY) {
        activityLog.pop();
    }
    renderActivityFeed();
};

const renderActivityFeed = () => {
    if (!activityFeed) {
        return;
    }

    activityFeed.innerHTML = '';
    if (!activityLog.length) {
        const empty = document.createElement('p');
        empty.className = 'subdued';
        empty.textContent = 'Waiting for session activity…';
        activityFeed.appendChild(empty);
        return;
    }

    activityLog.forEach((log) => {
        const item = document.createElement('div');
        item.className = 'activity-item';
        item.innerHTML = `<strong>${log.title}</strong><span>${log.detail}</span>`;
        activityFeed.appendChild(item);
    });
};

const renderDashboard = () => {
    tableBody.innerHTML = '';
    let totalFlags = 0;
    let totalSolved = 0;

    const sortedUsers = Object.keys(userSessions).sort(
        (a, b) => userSessions[b].lastUpdate - userSessions[a].lastUpdate,
    );

    sortedUsers.forEach((userId) => {
        const session = userSessions[userId];
        totalFlags += session.integrityFlags;
        totalSolved += session.solved;

        const row = document.createElement('tr');
        const statusClass = {
            Active: 'status-active',
            Suspicious: 'status-suspicious',
            Evaluating: 'status-evaluating',
            Configuring: 'status-configuring',
            Terminated: 'status-suspicious',
            Solved: 'status-active',
        }[session.status] || 'status-configuring';

        const flagClass = session.integrityFlags > 2 ? 'flag-high' : session.integrityFlags > 0 ? 'flag-medium' : '';

        row.innerHTML = `
            <td>${userId}</td>
            <td><span class="status-indicator ${statusClass}">${session.status}</span></td>
            <td>${session.lastEvent || '—'}</td>
            <td>${session.lastDecision || '—'}</td>
            <td>${session.lastFeedback || '—'}</td>
            <td><span class="flag-badge ${flagClass}">${session.integrityFlags}</span></td>
            <td>${session.lastUpdate.toLocaleTimeString()}</td>
        `;
        tableBody.appendChild(row);
    });

    activeUsersCard.textContent = sortedUsers.length;
    integrityFlagsCard.textContent = totalFlags;
    solvedCountCard.textContent = totalSolved;
};

socket.addEventListener('open', () => {
    setConnectionState('connected');
});

socket.addEventListener('close', () => {
    setConnectionState('disconnected');
});

socket.addEventListener('message', (event) => {
    let data;
    try {
        data = JSON.parse(event.data);
    } catch (error) {
        console.warn('Non-JSON message received', event.data);
        return;
    }

    const userId = data.user_id;
    if (!userId) {
        return;
    }

    const session = ensureSession(userId);
    session.lastUpdate = new Date();

    if (data.event) {
        session.lastEvent = data.event;
        pushActivity({
            title: `${userId} • ${data.event}`,
            detail: session.lastUpdate.toLocaleTimeString(),
        });
    }

    if (data.decision_log && Array.isArray(data.decision_log) && data.decision_log.length) {
        const lastDecisionEntry = data.decision_log[data.decision_log.length - 1];
        const agent = lastDecisionEntry.agent || 'agent';
        const decisionType = lastDecisionEntry.decision?.decision_type || 'decision';
        session.lastDecision = `${agent}: ${decisionType}`;
    }

    if (data.feedback) {
        const entries = Object.entries(data.feedback)
            .map(([agent, notes]) => ({ agent, note: Array.isArray(notes) ? notes[notes.length - 1] : undefined }))
            .filter((entry) => entry.note);
        if (entries.length) {
            const recent = entries[entries.length - 1];
            session.lastFeedback = `${recent.agent}: ${recent.note}`;
        }
    }

    if (data.event === 'session_start') {
        session.status = 'Configuring';
    }
    if (data.event === 'focus_gained' || data.event === 'problem_assigned') {
        session.status = 'Active';
    }
    if (data.event === 'focus_lost') {
        session.integrityFlags += 1;
        session.status = 'Suspicious';
    }
    if (data.event === 'code_submitted') {
        session.status = 'Evaluating';
        if (data.evaluation && data.evaluation.status === 'passed') {
            session.solved += 1;
            session.status = 'Solved';
        }
    }

    if (data.integrity_decision === 'pause') {
        session.status = 'Suspicious';
    }
    if (data.status === 'terminated') {
        session.status = 'Terminated';
    }

    renderDashboard();
});

renderActivityFeed();
