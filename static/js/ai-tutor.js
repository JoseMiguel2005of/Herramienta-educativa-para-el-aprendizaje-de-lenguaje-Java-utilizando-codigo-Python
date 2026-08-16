// ai-tutor.js — AI Tutor integration for code analysis + exercise hints
// Uses the /api/ai/tutor backend endpoint (Gemini API)

(function () {
    'use strict';

    const TUTOR_PANEL_ID = 'ai-tutor-panel';
    let tutorPanel = null;
    let isLoading = false;
    let conversationHistory = [];

    // ===== Create the AI Tutor Panel =====
    function createTutorPanel() {
        if (document.getElementById(TUTOR_PANEL_ID)) return;

        const panel = document.createElement('div');
        panel.id = TUTOR_PANEL_ID;
        panel.innerHTML = `
            <div class="ai-tutor-header">
                <div class="ai-tutor-title">
                    <span class="ai-tutor-avatar"><svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path></svg></span>
                    <span>AI TUTOR</span>
                </div>
                <button class="ai-tutor-close" id="ai-tutor-close" title="Cerrar">×</button>
            </div>
            <div class="ai-tutor-messages" id="ai-tutor-messages">
                <div class="ai-msg ai-msg-bot">
                    <span class="ai-msg-avatar"><svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path></svg></span>
                    <div class="ai-msg-content">
                        ¡Hola! Soy tu tutor de IA. Puedo ayudarte de dos formas:
                        <br><br>
                        <b>Analizar tu código</b> — escribe código en el editor y haz clic en "Analizar Código"
                        <br>
                        <b>Pistas en ejercicios</b> — si te trabas en un ejercicio, presiona "Pedir Pista"
                    </div>
                </div>
            </div>
            <div class="ai-tutor-input-area">
                <input type="text" id="ai-tutor-input" class="ai-tutor-input" 
                       placeholder="Escribe tu pregunta..." autocomplete="off">
                <button id="ai-tutor-send" class="ai-tutor-send" title="Enviar">
                    <span id="ai-tutor-send-icon">➤</span>
                </button>
            </div>
            <div class="ai-tutor-actions">
                <button id="ai-btn-analyze" class="ai-action-btn">Analizar Código</button>
            </div>
        `;

        document.body.appendChild(panel);
        tutorPanel = panel;

        // Event listeners
        document.getElementById('ai-tutor-close').addEventListener('click', closeTutor);
        document.getElementById('ai-tutor-send').addEventListener('click', sendQuestion);
        document.getElementById('ai-tutor-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendQuestion();
            }
        });
        document.getElementById('ai-btn-analyze').addEventListener('click', analyzeCode);
    }

    // ===== Create the floating toggle button =====
    function createToggleButton() {
        const btn = document.createElement('button');
        btn.id = 'ai-tutor-toggle';
        btn.className = 'ai-tutor-toggle';
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" fill="none" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path></svg>';
        btn.title = 'Abrir AI Tutor';
        btn.addEventListener('click', toggleTutor);
        document.body.appendChild(btn);
    }

    // ===== Toggle / Open / Close =====
    function toggleTutor() {
        if (!tutorPanel) createTutorPanel();
        tutorPanel.classList.toggle('open');
    }

    function closeTutor() {
        if (tutorPanel) tutorPanel.classList.remove('open');
    }

    // ===== Add a message to the chat =====
    function addMessage(text, sender) {
        const container = document.getElementById('ai-tutor-messages');
        if (!container) return;

        // Keep rolling history of last 8 messages
        conversationHistory.push({ role: sender, text: text });
        if (conversationHistory.length > 8) {
            conversationHistory = conversationHistory.slice(-8);
        }

        const msg = document.createElement('div');
        msg.className = `ai-msg ai-msg-${sender}`;

        const avatar = sender === 'bot' 
            ? '<svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" fill="none" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path></svg>'
            : '<svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" fill="none" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>';

        msg.innerHTML = `
            <span class="ai-msg-avatar">${avatar}</span>
            <div class="ai-msg-content">${formatResponse(text)}</div>
        `;
        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
    }

    function addLoadingMessage() {
        const container = document.getElementById('ai-tutor-messages');
        if (!container) return;

        const msg = document.createElement('div');
        msg.className = 'ai-msg ai-msg-bot ai-msg-loading';
        msg.id = 'ai-loading-msg';
        msg.innerHTML = `
            <span class="ai-msg-avatar">🤖</span>
            <div class="ai-msg-content">
                <span class="ai-loading-dots">
                    <span>.</span><span>.</span><span>.</span>
                </span> Pensando...
            </div>
        `;
        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
    }

    function removeLoadingMessage() {
        const el = document.getElementById('ai-loading-msg');
        if (el) el.remove();
    }

    // ===== Format response (basic markdown) =====
    function formatResponse(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
            .replace(/\*(.*?)\*/g, '<i>$1</i>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/```(\w+)?\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
            .replace(/\n/g, '<br>');
    }

    // ===== Get the current code from the editor =====
    function getCurrentCode() {
        const editor = document.getElementById('practice-editor');
        return editor ? editor.value : '';
    }

    // ===== Get the current lesson ID =====
    function getLessonId() {
        return window.currentLessonId || '';
    }

    // ===== Send a free-form question =====
    async function sendQuestion() {
        const input = document.getElementById('ai-tutor-input');
        const question = input.value.trim();
        if (!question || isLoading) return;

        input.value = '';
        addMessage(question, 'user');
        
        await callTutor({
            code: getCurrentCode(),
            lesson_id: getLessonId(),
            question: question,
            mode: 'chat',
            history: conversationHistory
        });
    }

    // ===== Analyze code from the editor =====
    async function analyzeCode() {
        const code = getCurrentCode();
        if (!code.trim() || isLoading) {
            addMessage('Escribe algo de código en el editor primero.', 'bot');
            return;
        }

        if (!tutorPanel || !tutorPanel.classList.contains('open')) {
            toggleTutor();
        }

        addMessage('Analiza mi código por favor', 'user');

        await callTutor({
            code: code,
            lesson_id: getLessonId(),
            mode: 'analyze',
            history: conversationHistory
        });
    }

    // ===== Request hint for an exercise =====
    async function requestHint(exerciseId, exerciseQuestion, userAnswer) {
        if (isLoading) return;

        if (!tutorPanel) createTutorPanel();
        if (!tutorPanel.classList.contains('open')) {
            tutorPanel.classList.add('open');
        }

        addMessage(`Necesito una pista para: "${exerciseQuestion}"`, 'user');

        await callTutor({
            code: userAnswer || '',
            lesson_id: getLessonId(),
            question: '',
            mode: 'hint',
            exercise_question: exerciseQuestion,
            history: conversationHistory
        });
    }

    // ===== Call the backend API =====
    async function callTutor(payload) {
        isLoading = true;
        const sendBtn = document.getElementById('ai-tutor-send-icon');
        if (sendBtn) sendBtn.textContent = '...';
        
        addLoadingMessage();

        try {
            const resp = await fetch('/api/ai/tutor', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            
            removeLoadingMessage();

            if (data.ok) {
                addMessage(data.response, 'bot');
            } else {
                addMessage(`${data.error || 'Error desconocido'}`, 'bot');
            }
        } catch (err) {
            removeLoadingMessage();
            addMessage('No se pudo conectar con la IA. Verifica tu conexión.', 'bot');
        } finally {
            isLoading = false;
            if (sendBtn) sendBtn.textContent = '➤';
        }
    }

    // ===== Inject hint buttons into exercises =====
    function injectHintButtons() {
        const exerciseCards = document.querySelectorAll('.exercise-card');
        exerciseCards.forEach(card => {
            const controls = card.querySelector('.exercise-controls');
            if (!controls || controls.querySelector('.btn-ai-hint')) return;

            // Only inject hint button on fill-blank exercises (those with .exercise-input)
            const isFillBlank = card.querySelector('.exercise-input') !== null;
            if (!isFillBlank) return;

            const exerciseId = card.id;
            const questionEl = card.querySelector('.exercise-question');
            const questionText = questionEl ? questionEl.textContent.trim() : '';

            const hintBtn = document.createElement('button');
            hintBtn.className = 'btn-ai-hint';
            hintBtn.innerHTML = 'Pedir Pista';
            hintBtn.addEventListener('click', () => {
                // Try to get the user's current answer
                let userAnswer = '';
                const inputs = card.querySelectorAll('input[type="text"], textarea');
                inputs.forEach(inp => { userAnswer += inp.value + ' '; });

                requestHint(exerciseId, questionText, userAnswer.trim());
            });

            controls.appendChild(hintBtn);
        });
    }

    // ===== Initialize =====
    document.addEventListener('DOMContentLoaded', () => {
        createToggleButton();
        // Delay to ensure exercises are rendered
        setTimeout(injectHintButtons, 500);
    });

    // Expose for external use
    window.AITutor = {
        open: toggleTutor,
        close: closeTutor,
        analyze: analyzeCode,
        hint: requestHint
    };
})();
