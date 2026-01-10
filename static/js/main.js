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
        sessionModeBadge.textContent = `${data.payload.difficulty} Mode`;
        appendOutputMessage(`> Problem "${data.payload.title}" loaded. Good luck!`, "system");
    } else if (data.hint) {
        appendOutputMessage(`Hint: ${data.hint}`, "hint");
    } else if (data.integrity_action) {
        appendOutputMessage(`Warning: ${data.integrity_action}`, "warning");
    } else {
        appendOutputMessage(JSON.stringify(data), "info");
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
            indentUnit: 4
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

    // Switch UI
    setupContainer.classList.add('d-none');
    codingContainer.classList.remove('d-none');
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
