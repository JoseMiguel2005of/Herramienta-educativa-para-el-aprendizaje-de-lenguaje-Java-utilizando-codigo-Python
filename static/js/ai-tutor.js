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
        panel.setAttribute('role', 'dialog');
        panel.setAttribute('aria-label', 'Tutor IA Educativo');
        panel.innerHTML = `
            <div class="ai-tutor-header">
                <div class="ai-tutor-title">
                    <span class="ai-tutor-avatar" aria-hidden="true">
                        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2">
                            <rect x="3" y="11" width="18" height="10" rx="2"></rect>
                            <circle cx="12" cy="5" r="2"></circle>
                            <path d="M12 7v4"></path>
                        </svg>
                    </span>
                    <span>Tutor IA Educativo</span>
                </div>
                <div class="ai-tutor-header-controls">
                    <button type="button" class="ai-tutor-ctrl-btn" id="ai-tutor-expand" title="Expandir o reducir panel" aria-label="Expandir o reducir panel">⛶</button>
                    <button type="button" class="ai-tutor-ctrl-btn" id="ai-tutor-close" title="Cerrar Tutor IA" aria-label="Cerrar Tutor IA">✕</button>
                </div>
            </div>
            <div class="ai-tutor-messages" id="ai-tutor-messages">
                <div class="ai-msg ai-msg-bot">
                    <span class="ai-msg-avatar" aria-hidden="true">
                        <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2">
                            <rect x="3" y="11" width="18" height="10" rx="2"></rect>
                            <circle cx="12" cy="5" r="2"></circle>
                            <path d="M12 7v4"></path>
                        </svg>
                    </span>
                    <div class="ai-msg-content">
                        <p class="ai-msg-p">¡Hola! Soy tu <strong>Tutor de IA</strong> para Python y Java. ¿En qué te puedo ayudar hoy?</p>
                        <ul class="ai-msg-list">
                            <li><strong>Resolver dudas de código:</strong> Escribe tu pregunta en el chat y te responderé con ejemplos.</li>
                            <li><strong>Analizar tu código:</strong> Presiona <em>"Analizar Código"</em> para revisar lo que escribiste en el editor.</li>
                            <li><strong>Pistas en ejercicios:</strong> Si te trabas en una lección, usa <em>"Pedir Pista"</em>.</li>
                        </ul>
                    </div>
                </div>
            </div>
            <div class="ai-tutor-input-area">
                <label for="ai-tutor-input" class="sr-only">Escribe tu pregunta al Tutor IA</label>
                <input type="text" id="ai-tutor-input" class="ai-tutor-input" 
                       placeholder="Escribe tu duda sobre Python o Java..." autocomplete="off">
                <button type="button" id="ai-tutor-send" class="ai-tutor-send" title="Enviar pregunta" aria-label="Enviar pregunta">
                    <span id="ai-tutor-send-icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" fill="none" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg></span>
                </button>
            </div>
            <div class="ai-tutor-actions">
                <button type="button" id="ai-btn-analyze" class="ai-action-btn">Analizar código del editor</button>
            </div>
        `;

        document.body.appendChild(panel);
        tutorPanel = panel;

        // Event listeners
        document.getElementById('ai-tutor-close').addEventListener('click', closeTutor);
        document.getElementById('ai-tutor-expand').addEventListener('click', toggleExpandTutor);
        document.getElementById('ai-tutor-send').addEventListener('click', sendQuestion);
        document.getElementById('ai-tutor-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendQuestion();
            }
        });
        document.getElementById('ai-btn-analyze').addEventListener('click', analyzeCode);
        const messagesEl = document.getElementById('ai-tutor-messages');
        if (messagesEl) {
            messagesEl.addEventListener('click', (e) => {
                const copyBtn = e.target.closest('.ai-code-copy');
                if (copyBtn) window.copyAiCode(copyBtn);
            });
        }
    }

    function syncNavTriggerState(isOpen) {
        const navBtn = document.getElementById('btn-ai-tutor-nav');
        if (navBtn) {
            navBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            navBtn.classList.toggle('nav-active-item', isOpen);
        }
    }

    // ===== Wire sidebar Tutor IA trigger (sin FAB flotante que tape botones) =====
    function wireNavToggleButton() {
        const navBtn = document.getElementById('btn-ai-tutor-nav');
        if (navBtn) {
            navBtn.addEventListener('click', () => {
                const sb = document.getElementById('main-sidebar');
                const ov = document.getElementById('mobile-overlay');
                const mt = document.getElementById('mobile-menu-toggle');
                if (window.innerWidth <= 900 && sb && sb.classList.contains('active')) {
                    sb.classList.remove('active');
                    if (ov) ov.style.display = 'none';
                    if (mt) mt.setAttribute('aria-expanded', 'false');
                }
                toggleTutor();
            });
        }
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && tutorPanel && tutorPanel.classList.contains('open')) {
                e.preventDefault();
                closeTutor();
            }
        });
    }

    // ===== Toggle / Open / Close =====
    function toggleTutor() {
        if (!tutorPanel) createTutorPanel();
        const opening = !tutorPanel.classList.contains('open');
        tutorPanel.classList.toggle('open', opening);
        syncNavTriggerState(opening);
        if (opening) {
            setTimeout(() => {
                const input = document.getElementById('ai-tutor-input');
                if (input) input.focus();
            }, 120);
        }
    }

    function closeTutor() {
        if (tutorPanel) {
            tutorPanel.classList.remove('open');
            syncNavTriggerState(false);
        }
    }

    function toggleExpandTutor() {
        if (tutorPanel) {
            tutorPanel.classList.toggle('expanded');
            const expandBtn = document.getElementById('ai-tutor-expand');
            if (expandBtn) {
                expandBtn.textContent = tutorPanel.classList.contains('expanded') ? '⤢' : '⛶';
            }
        }
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
            ? '<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path></svg>'
            : '<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>';

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
            <span class="ai-msg-avatar">
                <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2">
                    <rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path>
                </svg>
            </span>
            <div class="ai-msg-content">
                <span class="ai-loading-dots">
                    <span>.</span><span>.</span><span>.</span>
                </span> Consultando al Tutor IA...
            </div>
        `;
        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
    }

    function removeLoadingMessage() {
        const el = document.getElementById('ai-loading-msg');
        if (el) el.remove();
    }

    // ===== Format response (XSS-safe Markdown Parser) =====
    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatResponse(text) {
        if (!text) return '';

        const tokenPrefix = `AITEMP${Math.random().toString(36).slice(2, 10)}`;

        // 1. Extraer y proteger bloques de código ```...``` (con contenido escapado)
        const codeBlocks = [];
        let working = String(text).replace(/```(\w+)?\n?([\s\S]*?)```/g, (match, lang, code) => {
            const placeholder = `${tokenPrefix}CODEBLOCK${codeBlocks.length}END`;
            const langLabel = lang ? `<span class="ai-code-lang">${escapeHtml(lang)}</span>` : '';
            codeBlocks.push(`
                <div class="ai-code-block">
                    <div class="ai-code-header">
                        ${langLabel}
                        <button type="button" class="ai-code-copy">Copiar</button>
                    </div>
                    <pre><code>${escapeHtml(code.trim())}</code></pre>
                </div>
            `);
            return `\n\n${placeholder}\n\n`;
        });

        // 2. Extraer y proteger código inline `...` (con contenido escapado)
        const inlineCodes = [];
        working = working.replace(/`([^`]+)`/g, (match, inline) => {
            const placeholder = `${tokenPrefix}INLINECODE${inlineCodes.length}END`;
            inlineCodes.push(`<code class="ai-inline-code">${escapeHtml(inline)}</code>`);
            return placeholder;
        });

        // 3. Escapar TODO el texto restante antes de transformar Markdown
        //    (previene XSS y preserva genéricos Java como List<String>)
        let cleanText = escapeHtml(working);

        // 4. Encabezados
        cleanText = cleanText.replace(/^### (.*$)/gim, '<h4 class="ai-msg-h4">$1</h4>');
        cleanText = cleanText.replace(/^## (.*$)/gim, '<h3 class="ai-msg-h3">$1</h3>');
        cleanText = cleanText.replace(/^# (.*$)/gim, '<h2 class="ai-msg-h2">$1</h2>');

        // 5. Separadores
        cleanText = cleanText.replace(/^---$/gim, '<hr class="ai-msg-hr">');

        // 6. Negrita y Cursiva
        cleanText = cleanText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        cleanText = cleanText.replace(/\*(.*?)\*/g, '<em>$1</em>');

        // 7. Formateo línea a línea para listas y párrafos limpios
        const lines = cleanText.split('\n');
        let inList = false;
        let listType = 'ul';
        let formattedLines = [];

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();
            if (!line) {
                if (inList) {
                    formattedLines.push(`</${listType}>`);
                    inList = false;
                }
                continue;
            }

            const isUnordered = /^[-*•]\s+(.*)$/.test(line);
            const isOrdered = /^\d+\.\s+(.*)$/.test(line);

            if (isUnordered) {
                const itemContent = line.replace(/^[-*•]\s+/, '');
                if (!inList || listType !== 'ul') {
                    if (inList) formattedLines.push(`</${listType}>`);
                    formattedLines.push('<ul class="ai-msg-list">');
                    inList = true;
                    listType = 'ul';
                }
                formattedLines.push(`<li>${itemContent}</li>`);
            } else if (isOrdered) {
                const itemContent = line.replace(/^\d+\.\s+/, '');
                if (!inList || listType !== 'ol') {
                    if (inList) formattedLines.push(`</${listType}>`);
                    formattedLines.push('<ol class="ai-msg-list">');
                    inList = true;
                    listType = 'ol';
                }
                formattedLines.push(`<li>${itemContent}</li>`);
            } else {
                if (inList) {
                    formattedLines.push(`</${listType}>`);
                    inList = false;
                }
                if (
                    line.startsWith('<h') ||
                    line.startsWith('<hr') ||
                    line.startsWith(`${tokenPrefix}CODEBLOCK`)
                ) {
                    formattedLines.push(line);
                } else {
                    formattedLines.push(`<p class="ai-msg-p">${line}</p>`);
                }
            }
        }
        if (inList) {
            formattedLines.push(`</${listType}>`);
        }

        let resultHtml = formattedLines.join('');

        // 8. Restaurar código inline y bloques de código usando funciones (evita interpretación de $&/$1)
        inlineCodes.forEach((snippet, index) => {
            resultHtml = resultHtml.replace(`${tokenPrefix}INLINECODE${index}END`, () => snippet);
        });
        codeBlocks.forEach((block, index) => {
            resultHtml = resultHtml.replace(`${tokenPrefix}CODEBLOCK${index}END`, () => block);
        });

        return resultHtml;
    }

    // Helper global para copiar código de bloques IA
    window.copyAiCode = function (button) {
        const codeElement = button.closest('.ai-code-block').querySelector('code');
        if (codeElement) {
            navigator.clipboard.writeText(codeElement.innerText).then(() => {
                button.textContent = '¡Copiado!';
                button.style.color = '#00E5FF';
                setTimeout(() => {
                    button.textContent = 'Copiar';
                    button.style.color = '';
                }, 2000);
            });
        }
    };

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
            addMessage('Por favor escribe algo de código en el editor antes de analizar.', 'bot');
            return;
        }

        if (!tutorPanel || !tutorPanel.classList.contains('open')) {
            toggleTutor();
        }

        addMessage('Analiza mi código por favor.', 'user');

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

        addMessage(`Necesito una pista para el ejercicio: "${exerciseQuestion}"`, 'user');

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
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
            const resp = await fetch('/api/ai/tutor', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            
            removeLoadingMessage();

            if (data.ok) {
                addMessage(data.response, 'bot');
            } else {
                addMessage(data.error || 'Ocurrió un error inesperado al consultar el Tutor.', 'bot');
            }
        } catch (err) {
            removeLoadingMessage();
            addMessage('No se pudo conectar con el servicio de tutoría. Verifica tu conexión a internet.', 'bot');
        } finally {
            isLoading = false;
            if (sendBtn) sendBtn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
        }
    }

    // ===== Inject hint buttons into exercises =====
    function injectHintButtons() {
        const exerciseCards = document.querySelectorAll('.exercise-card');
        exerciseCards.forEach(card => {
            const controls = card.querySelector('.exercise-controls');
            if (!controls || controls.querySelector('.btn-ai-hint')) return;

            const isFillBlank = card.querySelector('.exercise-input') !== null;
            if (!isFillBlank) return;

            const exerciseId = card.id;
            const questionEl = card.querySelector('.exercise-question');
            const questionText = questionEl ? questionEl.textContent.trim() : '';

            const hintBtn = document.createElement('button');
            hintBtn.className = 'btn-ai-hint';
            hintBtn.innerHTML = 'Pedir Pista';
            hintBtn.addEventListener('click', () => {
                let userAnswer = '';
                const inputs = card.querySelectorAll('input[type="text"], textarea');
                inputs.forEach(inp => { userAnswer += inp.value + ' '; });

                requestHint(exerciseId, questionText, userAnswer.trim());
            });

            controls.appendChild(hintBtn);
        });
    }

    // ===== Expose public API =====
    window.AITutor = {
        hint: requestHint,
        open: toggleTutor,
        analyze: analyzeCode
    };

    // ===== Init on DOM load =====
    document.addEventListener('DOMContentLoaded', () => {
        wireNavToggleButton();
        injectHintButtons();
    });

})();
