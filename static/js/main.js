const clientId = "user_" + Math.random().toString(36).substr(2, 9);
const socket = new WebSocket(`ws://localhost:8000/ws/${clientId}`);
const output = document.getElementById('output');

// UI Elements
const setupContainer = document.getElementById('setup-container');
const codingContainer = document.getElementById('coding-container');
const problemTitle = document.getElementById('problem-title');
const sessionModeBadge = document.getElementById('session-mode-badge');

let editor; // Will be initialized after session start

socket.onopen = function() {
    appendOutputMessage("> Connection established. Please configure your session.", "system");
};

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'problem_assigned') {
        // Initialize the editor now that we have a problem
        initializeEditor(data.payload.code);
        problemTitle.textContent = `Problem: ${data.payload.title}`;
        const difficulty = data.payload.difficulty || 'easy';
        const normalizedDifficulty = difficulty.charAt(0).toUpperCase() + difficulty.slice(1);
        sessionModeBadge.textContent = `${normalizedDifficulty} Mode`;
        sessionModeBadge.className = `badge rounded-pill fs-6 bg-${difficulty === 'easy' ? 'success' : difficulty === 'medium' ? 'warning' : 'danger'}`;
        if (data.payload.description) {
            appendOutputMessage(`> ${data.payload.description}`, "system");
        }
        appendOutputMessage(`> Problem "${data.payload.title}" loaded. Good luck!`, "system");
    } else if (data.type === 'code_feedback') {
        renderEvaluationFeedback(data);
        if (data.next_problem) {
            initializeEditor(data.next_problem.payload.code);
            problemTitle.textContent = `Problem: ${data.next_problem.payload.title}`;
            const diff = data.next_problem.payload.difficulty;
            const nextDifficulty = diff.charAt(0).toUpperCase() + diff.slice(1);
            sessionModeBadge.textContent = `${nextDifficulty} Mode`;
            sessionModeBadge.className = `badge rounded-pill fs-6 bg-${diff === 'easy' ? 'success' : diff === 'medium' ? 'warning' : 'danger'}`;
            appendOutputMessage(`> Difficulty ${data.next_problem.decision === 'advance' ? 'increased' : 'recalibrated'}. New problem assigned: ${data.next_problem.payload.title}`, "system");
        }
    } else if (data.type === 'hint') {
        if (data.allowed && data.payload) {
            appendOutputMessage(`Hint (${data.payload.level}): ${data.payload.text}`, "hint");
        } else {
            appendOutputMessage(`> Hint unavailable: ${data.message}`, "warning");
        }
    } else if (data.type === 'integrity') {
        appendOutputMessage(`Integrity: ${data.message} (decision: ${data.decision})`, data.decision === 'terminate' ? 'error' : 'warning');
    } else if (data.type === 'session_summary') {
        appendOutputMessage(`> Session summary generated. Status: ${data.status}`, "system");
    } else if (data.event) {
        return;
    } else {
        // Generic message handler
        const message = data.result?.status || JSON.stringify(data);
        appendOutputMessage(`> ${message}`, "info");
    }
};

socket.onclose = function() {
    appendOutputMessage("> Connection lost.", "error");
};

function initializeEditor(startCode) {
    if (!editor) {
        editor = CodeMirror.fromTextArea(document.getElementById('code'), {
            lineNumbers: true,
            mode: "python",
            theme: "material-darker",
            indentUnit: 4,
            autofocus: true
        });
    }
    editor.setValue(startCode);
}

function appendOutputMessage(text, type) {
    const messageElement = document.createElement('div');
    messageElement.textContent = text;
    messageElement.className = `output-line ${type}`;
    output.appendChild(messageElement);
    output.scrollTop = output.scrollHeight;
}

function renderEvaluationFeedback(data) {
    const evaluation = data.evaluation || {};
    const diagnosis = data.diagnosis || {};
    const submission = data.submission || {};

    const statusText = evaluation.status ? evaluation.status.toUpperCase() : 'UNKNOWN';
    const scoreText = typeof evaluation.score === 'number' ? `${evaluation.score}` : 'N/A';
    appendOutputMessage(`> Evaluation ${statusText} | Score ${scoreText} | Passed ${evaluation.passed}/${evaluation.total_tests}`, "info");

    if (evaluation.message) {
        appendOutputMessage(`> ${evaluation.message}`, "info");
    }

    if (diagnosis.reasoning) {
        const guess = typeof diagnosis.guess_probability === 'number' ? diagnosis.guess_probability.toFixed(2) : 'n/a';
        appendOutputMessage(`> Reasoning: ${diagnosis.reasoning} (guess probability ${guess})`, "info");
    }

    if (submission.diff_ratio !== undefined) {
        appendOutputMessage(`> Submission metrics: diff=${submission.diff_ratio}, delta=${submission.time_delta}s`, "info");
    }

    if (evaluation.penalties) {
        appendOutputMessage(`> Penalties applied (hint: ${evaluation.penalties.hint}, time: ${evaluation.penalties.time}, integrity: ${evaluation.penalties.integrity})`, "info");
    }
}

function sendMessage(type, payload) {
    if (socket.readyState === WebSocket.OPEN) {
        const message = {
            type: type,
            payload: payload
        };
        socket.send(JSON.stringify(message));
    } else {
        appendOutputMessage("> Cannot send message. Connection is not open.", "error");
    }
}

function startSession() {
    const difficulty = document.getElementById('difficulty').value;
    const language = document.getElementById('language').value;
    const topic = document.getElementById('topic').value;

    sendMessage('session_start', {
        difficulty: difficulty,
        language: language,
        topic: topic
    });

    // Animate UI transition
    setupContainer.classList.add('fade-out-up');
    
    setTimeout(() => {
        codingContainer.classList.remove('fade-out-up');
        codingContainer.classList.add('fade-in-down');
        setupContainer.style.display = 'none';
        if(editor) editor.focus();
    }, 400); // Match CSS transition duration

    appendOutputMessage("> Session started. Waiting for problem assignment...", "system");
}

function submitCode() {
    if (!editor) return;
    const code = editor.getValue();
    sendMessage('code_submitted', { code: code });
    appendOutputMessage("> Code submitted for evaluation.", "info");
}

function requestHint() {
    sendMessage('hint_requested', {});
    appendOutputMessage("> Hint requested.", "info");
}

// Mock integrity monitoring
window.onblur = function() {
    sendMessage('focus_lost', {});
};

window.onfocus = function() {
    sendMessage('focus_gained', {});
};
