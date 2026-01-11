const profileStorageKey = 'skillproof-access-profile';
const sessionUserId = document.body?.dataset?.userId || null;
const sessionUserName = document.body?.dataset?.userName || '';
const clientId = sessionUserId || (typeof crypto !== 'undefined' && crypto.randomUUID
    ? `user_${crypto.randomUUID()}`
    : `user_${Math.random().toString(36).slice(2, 11)}`);
const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
const socket = new WebSocket(`${wsScheme}://${window.location.host}/ws/${clientId}`);

const output = document.getElementById('output');
const setupContainer = document.getElementById('setup-container');
const codingContainer = document.getElementById('coding-container');
const problemTitle = document.getElementById('problem-title');
const problemSummary = document.getElementById('problem-summary');
const challengeDetail = document.getElementById('challenge-detail');
const sessionModeBadge = document.getElementById('session-mode-badge');
const decisionLog = document.getElementById('decision-log');
const feedbackPanel = document.getElementById('agent-feedback');
const explanationPanel = document.getElementById('agent-explanation');
const candidateName = document.getElementById('candidate-name');
const sessionTimer = document.getElementById('session-timer');
const sessionStatus = document.getElementById('session-status');
const sessionStatusCard = document.getElementById('session-status-card');
const integrityStatus = document.getElementById('integrity-status');
const hintCount = document.getElementById('hint-count');
const logoutButton = document.getElementById('candidate-logout');

let editor;
let editorIsCodeMirror = false;
let timerHandle = null;
let timerStart = null;
let totalHints = 0;
let socketReady = false;
const pendingMessages = [];

const getProfile = () => {
    try {
        const sessionValue = window.sessionStorage.getItem(profileStorageKey);
        if (sessionValue) {
            return JSON.parse(sessionValue);
        }
        const stored = window.localStorage.getItem(profileStorageKey);
        return stored ? JSON.parse(stored) : null;
    } catch (error) {
        console.warn('Unable to access stored profile', error);
        return null;
    }
};

const applyProfile = () => {
    const profile = getProfile();
    if (candidateName) {
        const displayName = profile?.name || sessionUserName || 'Anonymous';
        candidateName.textContent = `Candidate · ${displayName}`;
    }
};

applyProfile();

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
        window.location.href = '/access';
    });
}

const startTimer = () => {
    timerStart = Date.now();
    updateTimer();
    clearInterval(timerHandle);
    timerHandle = window.setInterval(updateTimer, 1000);
};

const stopTimer = () => {
    clearInterval(timerHandle);
    timerHandle = null;
};

const updateTimer = () => {
    if (!timerStart || !sessionTimer) {
        return;
    }
    const elapsed = Date.now() - timerStart;
    const seconds = Math.floor(elapsed / 1000) % 60;
    const minutes = Math.floor(elapsed / 60000) % 60;
    const hours = Math.floor(elapsed / 3600000);
    const formatted = [hours, minutes, seconds]
        .filter((_, index) => hours > 0 || index > 0)
        .map((value) => value.toString().padStart(2, '0'))
        .join(':') || '00:00';
    sessionTimer.textContent = `Timer · ${formatted}`;
};

const updateModeBadge = (difficulty) => {
    if (!sessionModeBadge) {
        return;
    }
    const normalized = difficulty ? `${difficulty.charAt(0).toUpperCase()}${difficulty.slice(1)} mode` : 'Configuring';
    sessionModeBadge.textContent = normalized;
    sessionModeBadge.dataset.level = difficulty || 'configuring';
};

const updateSessionStatus = (statusText, severity = 'ok') => {
    if (sessionStatus) {
        sessionStatus.textContent = statusText;
    }
    if (sessionStatusCard) {
        sessionStatusCard.dataset.status = severity;
    }
};

const updateIntegrity = (message, decision) => {
    if (!integrityStatus) {
        return;
    }
    integrityStatus.textContent = message;
    const severity = decision === 'terminate' ? 'critical' : decision === 'pause' ? 'warning' : 'ok';
    if (sessionStatusCard) {
        sessionStatusCard.dataset.status = severity;
    }
};

const incrementHintCount = () => {
    totalHints += 1;
    if (hintCount) {
        hintCount.textContent = String(totalHints);
    }
};

const revealWorkspace = () => {
    if (!setupContainer || !codingContainer) {
        return;
    }
    setupContainer.classList.add('fade-out-up');
    window.setTimeout(() => {
        setupContainer.hidden = true;
        codingContainer.hidden = false;
        codingContainer.classList.remove('fade-out-up');
        codingContainer.classList.add('fade-in-down');
        if (editor) {
            editor.focus();
        }
    }, 320);
};

const currentEditorTheme = () => {
    const theme = document.documentElement.getAttribute('data-theme');
    return theme === 'dark' ? 'material-darker' : 'neo';
};

const initializeEditor = (startCode = '') => {
    const textarea = document.getElementById('code');
    if (!textarea) {
        return;
    }

    if (typeof window.CodeMirror === 'undefined') {
        if (!editor || editorIsCodeMirror) {
            editor = {
                getValue: () => textarea.value,
                setValue: (value) => {
                    textarea.value = value;
                },
                focus: () => textarea.focus(),
                setOption: () => undefined,
            };
            editorIsCodeMirror = false;
        }
        editor.setValue(startCode);
        editor.focus();
        return;
    }

    if (!editor || !editorIsCodeMirror) {
        editor = window.CodeMirror.fromTextArea(textarea, {
            lineNumbers: true,
            mode: 'python',
            theme: currentEditorTheme(),
            indentUnit: 4,
            autofocus: true,
        });
        editorIsCodeMirror = true;
    } else {
        editor.setOption('theme', currentEditorTheme());
    }
    editor.setValue(startCode);
    editor.focus();
};

const appendOutputMessage = (text, type) => {
    if (!output) {
        return;
    }
    const messageElement = document.createElement('div');
    messageElement.textContent = text;
    messageElement.className = `output-line ${type}`;
    output.appendChild(messageElement);
    output.scrollTop = output.scrollHeight;
};

const renderEvaluationFeedback = (data) => {
    const evaluation = data.evaluation || {};
    const diagnosis = data.diagnosis || {};
    const submission = data.submission || {};

    const statusText = evaluation.status ? evaluation.status.toUpperCase() : 'UNKNOWN';
    const scoreText = typeof evaluation.score === 'number' ? `${evaluation.score}` : 'N/A';
    const passed = typeof evaluation.passed === 'number' ? evaluation.passed : 0;
    const total = typeof evaluation.total_tests === 'number' ? evaluation.total_tests : (passed + (evaluation.failed || 0));
    appendOutputMessage(`> Evaluation ${statusText} | Score ${scoreText} | Passed ${passed}/${total || 'n/a'}`, 'info');

    if (evaluation.message) {
        appendOutputMessage(`> ${evaluation.message}`, 'info');
    }

    if (diagnosis.reasoning) {
        const guess = typeof diagnosis.guess_probability === 'number' ? diagnosis.guess_probability.toFixed(2) : 'n/a';
        appendOutputMessage(`> Reasoning: ${diagnosis.reasoning} (guess probability ${guess})`, 'info');
    }

    if (submission.diff_ratio !== undefined) {
        appendOutputMessage(`> Submission metrics: diff=${submission.diff_ratio}, delta=${submission.time_delta}s`, 'info');
    }

    if (evaluation.penalties) {
        appendOutputMessage(`> Penalties applied (hint: ${evaluation.penalties.hint}, time: ${evaluation.penalties.time}, integrity: ${evaluation.penalties.integrity})`, 'info');
    }
};

const renderDecisionTrail = (entries) => {
    if (!decisionLog) {
        return;
    }
    decisionLog.innerHTML = '';
    const recent = Array.isArray(entries) ? entries.slice(-6).reverse() : [];

    if (!recent.length) {
        const empty = document.createElement('li');
        empty.className = 'panel-item';
        empty.textContent = 'No decisions recorded yet.';
        decisionLog.appendChild(empty);
        return;
    }

    recent.forEach((entry) => {
        const item = document.createElement('li');
        item.className = 'panel-item';
        const agent = entry.agent || 'agent';
        const decision = entry.decision?.decision_type || entry.decision?.type || 'action';
        const timestamp = entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : '';
        item.innerHTML = `<span class="badge muted">${agent}</span><span>${decision}</span><span class="meta">${timestamp}</span>`;
        decisionLog.appendChild(item);
    });
};

const renderAgentFeedback = (feedbackMap) => {
    if (!feedbackPanel) {
        return;
    }

    feedbackPanel.innerHTML = '';
    if (!feedbackMap) {
        const empty = document.createElement('li');
        empty.className = 'panel-item';
        empty.textContent = 'Awaiting agent feedback.';
        feedbackPanel.appendChild(empty);
        return;
    }

    const entries = Object.entries(feedbackMap)
        .map(([agent, notes]) => ({ agent, note: Array.isArray(notes) ? notes[notes.length - 1] : undefined }))
        .filter((entry) => entry.note);

    if (!entries.length) {
        const empty = document.createElement('li');
        empty.className = 'panel-item';
        empty.textContent = 'Awaiting agent feedback.';
        feedbackPanel.appendChild(empty);
        return;
    }

    entries.forEach(({ agent, note }) => {
        const item = document.createElement('li');
        item.className = 'panel-item';
        item.innerHTML = `<span class="badge muted">${agent}</span><span>${note}</span>`;
        feedbackPanel.appendChild(item);
    });
};

const renderExplanation = (explanation) => {
    if (!explanationPanel) {
        return;
    }
    if (!explanation) {
        explanationPanel.textContent = 'Awaiting agent decisions…';
        return;
    }
    if (typeof explanation === 'string') {
        explanationPanel.textContent = explanation;
        return;
    }
    const agent = explanation.agent ? `[${explanation.agent}]` : '';
    const decision = explanation.decision ? `${explanation.decision}` : '';
    const message = explanation.message || explanation.rationale || '';
    const detail = explanation.metadata ? JSON.stringify(explanation.metadata) : '';
    explanationPanel.textContent = [agent, decision, message, detail].filter(Boolean).join(' ');
};

const sendMessage = (type, payload) => {
    const message = { type, payload };
    if (socketReady && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(message));
        return;
    }

    pendingMessages.push(message);
    if (pendingMessages.length === 1) {
        appendOutputMessage('> Connection warming up. Your action will run once ready.', 'warning');
    }
};

window.startSession = () => {
    const difficulty = document.getElementById('difficulty').value;
    const language = document.getElementById('language').value;
    const topic = document.getElementById('topic').value;

    sendMessage('session_start', { difficulty, language, topic });
    revealWorkspace();
    updateSessionStatus('Active');
    updateIntegrity('Clean focus', 'resume');
    totalHints = 0;
    if (hintCount) {
        hintCount.textContent = '0';
    }
    startTimer();
    appendOutputMessage('> Session started. Waiting for problem assignment…', 'system');
};

window.submitCode = () => {
    if (!editor) {
        appendOutputMessage('> Editor not ready yet.', 'warning');
        return;
    }
    const code = editor.getValue();
    sendMessage('code_submitted', { code });
    updateSessionStatus('Evaluating', 'warning');
    appendOutputMessage('> Code submitted for evaluation.', 'info');
};

window.requestHint = () => {
    sendMessage('hint_requested', {});
    appendOutputMessage('> Hint requested.', 'info');
};

socket.addEventListener('open', () => {
    socketReady = true;
    appendOutputMessage('> Connection established. Configure your session to begin.', 'system');
    applyProfile();

    while (pendingMessages.length) {
        socket.send(JSON.stringify(pendingMessages.shift()));
    }
});

socket.addEventListener('message', (event) => {
    let data;
    try {
        data = JSON.parse(event.data);
    } catch (error) {
        console.warn('Non-JSON message received', event.data);
        return;
    }

    if (!data) {
        return;
    }

    if (data.type === 'problem_assigned') {
        initializeEditor(data.payload.code || '');
        problemTitle.textContent = `Problem: ${data.payload.title}`;
        problemSummary.textContent = data.payload.description || 'Solve the challenge using the editor.';
        challengeDetail.textContent = `${data.payload.topic || 'General'} • ${data.payload.difficulty || 'adaptive'}`;
        updateModeBadge(data.payload.difficulty || 'easy');
        updateSessionStatus('Active');
        appendOutputMessage(`> Problem "${data.payload.title}" loaded. Good luck!`, 'system');
        return;
    }

    if (data.type === 'code_feedback') {
        renderEvaluationFeedback(data);
        updateSessionStatus('Active');
        if (data.next_problem) {
            initializeEditor(data.next_problem.payload.code || '');
            problemTitle.textContent = `Problem: ${data.next_problem.payload.title}`;
            problemSummary.textContent = data.next_problem.payload.description || 'Continue iterating on the new challenge.';
            challengeDetail.textContent = `${data.next_problem.payload.topic || 'General'} • ${data.next_problem.payload.difficulty}`;
            updateModeBadge(data.next_problem.payload.difficulty);
            appendOutputMessage(`> Difficulty ${data.next_problem.decision === 'advance' ? 'increased' : 'recalibrated'}. New problem assigned: ${data.next_problem.payload.title}`, 'system');
        }
    } else if (data.type === 'hint') {
        if (data.allowed && data.payload) {
            incrementHintCount();
            appendOutputMessage(`Hint (${data.payload.level}): ${data.payload.text}`, 'hint');
        } else {
            appendOutputMessage(`> Hint unavailable: ${data.message}`, 'warning');
        }
    } else if (data.type === 'integrity') {
        updateIntegrity(data.message || 'Integrity event', data.decision);
        appendOutputMessage(`Integrity: ${data.message} (decision: ${data.decision})`, data.decision === 'terminate' ? 'error' : 'warning');
    } else if (data.type === 'session_summary') {
        updateSessionStatus(data.status || 'Completed');
        stopTimer();
        appendOutputMessage(`> Session summary generated. Status: ${data.status}`, 'system');
    } else if (data.event) {
        // Broadcast event from server; ignore if not relevant to candidate UI.
        return;
    } else {
        const message = data.result?.status || JSON.stringify(data);
        appendOutputMessage(`> ${message}`, 'info');
    }

    if (data.explanation) {
        renderExplanation(data.explanation);
    }

    if (data.decision_log) {
        renderDecisionTrail(data.decision_log);
    }

    if (data.feedback) {
        renderAgentFeedback(data.feedback);
    }
});

socket.addEventListener('close', () => {
    socketReady = false;
    appendOutputMessage('> Connection lost.', 'error');
    stopTimer();
});

window.addEventListener('blur', () => {
    if (!socketReady) {
        return;
    }
    sendMessage('focus_lost', {});
});

window.addEventListener('focus', () => {
    if (!socketReady) {
        return;
    }
    sendMessage('focus_gained', {});
});

applyProfile();

document.addEventListener('skillproof-theme-change', () => {
    if (editor) {
        editor.setOption('theme', currentEditorTheme());
    }
});
