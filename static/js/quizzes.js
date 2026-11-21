// quizzes.js - Soporte completo para evaluación en Python y Java (sensible a mayúsculas/minúsculas)

function _quizLangStorageKey() {
    if (typeof window.getScopedStorageKey === 'function') {
        return window.getScopedStorageKey('py2java_quiz_lang');
    }
    const uid = window.PY2JAVA_USER_ID;
    const scope = (uid !== undefined && uid !== null && String(uid).trim() !== '') ? String(uid) : 'anon';
    return `py2java_quiz_lang_${scope}`;
}

let currentQuizLanguage = 'python';

document.addEventListener('DOMContentLoaded', () => {
    currentQuizLanguage = localStorage.getItem(_quizLangStorageKey()) || 'python';
    // Inicializar idioma guardado (segmentado por user_id)
    initQuizLanguageSelector();

    // === MULTIPLE CHOICE ===
    document.body.addEventListener('change', (e) => {
        if (e.target.matches('.quiz-option-label input[type="radio"]')) {
            const container = e.target.closest('.quiz-options');
            container.querySelectorAll('.quiz-option-label').forEach(lbl => lbl.classList.remove('selected'));
            e.target.closest('.quiz-option-label').classList.add('selected');
        }
    });

    // === REORDER (Drag & Drop + Botones accesibles Subir/Bajar) ===
    function announceA11y(msg) {
        if (window.Py2JavaA11y && typeof window.Py2JavaA11y.announce === 'function') {
            window.Py2JavaA11y.announce(msg);
            return;
        }
        const region = document.getElementById('a11y-announcer');
        if (region) {
            region.textContent = '';
            requestAnimationFrame(() => { region.textContent = msg; });
        }
    }

    function updateReorderButtons(list) {
        if (!list) return;
        const items = Array.from(list.querySelectorAll('.reorder-item'));
        const total = items.length;
        items.forEach((item, idx) => {
            const upBtn = item.querySelector('.btn-reorder-up');
            const downBtn = item.querySelector('.btn-reorder-down');
            if (upBtn) {
                upBtn.disabled = (idx === 0);
                upBtn.setAttribute('aria-label', `Subir línea ${idx + 1} de ${total}`);
            }
            if (downBtn) {
                downBtn.disabled = (idx === total - 1);
                downBtn.setAttribute('aria-label', `Bajar línea ${idx + 1} de ${total}`);
            }
        });
    }

    window._updateReorderButtons = updateReorderButtons;

    document.querySelectorAll('.reorder-list').forEach(list => {
        let draggedItem = null;
        updateReorderButtons(list);

        list.querySelectorAll('.reorder-item').forEach(item => {
            item.addEventListener('dragstart', function() {
                draggedItem = this;
                setTimeout(() => this.classList.add('dragging'), 0);
            });

            item.addEventListener('dragend', function() {
                setTimeout(() => {
                    this.classList.remove('dragging');
                    draggedItem = null;
                    updateReorderButtons(list);
                }, 0);
            });

            item.addEventListener('dragover', function(e) {
                e.preventDefault();
                if (!draggedItem) return;
                const afterElement = getDragAfterElement(list, e.clientY);
                if (afterElement == null) {
                    list.appendChild(draggedItem);
                } else {
                    list.insertBefore(draggedItem, afterElement);
                }
            });
        });

        // Controles táctiles y de teclado (Subir / Bajar)
        list.addEventListener('click', (e) => {
            const upBtn = e.target.closest('.btn-reorder-up');
            const downBtn = e.target.closest('.btn-reorder-down');
            if (!upBtn && !downBtn) return;

            const item = e.target.closest('.reorder-item');
            if (!item || item.parentElement !== list) return;

            if (upBtn && item.previousElementSibling) {
                list.insertBefore(item, item.previousElementSibling);
                updateReorderButtons(list);
                const newPos = Array.from(list.children).indexOf(item) + 1;
                announceA11y(`Línea movida a la posición ${newPos} de ${list.children.length}`);
                if (!upBtn.disabled) {
                    upBtn.focus();
                } else {
                    const fallbackBtn = item.querySelector('.btn-reorder-down');
                    if (fallbackBtn) fallbackBtn.focus();
                }
            } else if (downBtn && item.nextElementSibling) {
                list.insertBefore(item.nextElementSibling, item);
                updateReorderButtons(list);
                const newPos = Array.from(list.children).indexOf(item) + 1;
                announceA11y(`Línea movida a la posición ${newPos} de ${list.children.length}`);
                if (!downBtn.disabled) {
                    downBtn.focus();
                } else {
                    const fallbackBtn = item.querySelector('.btn-reorder-up');
                    if (fallbackBtn) fallbackBtn.focus();
                }
            }
        });

        function getDragAfterElement(container, y) {
            const draggableElements = [...container.querySelectorAll('.reorder-item:not(.dragging)')];
            return draggableElements.reduce((closest, child) => {
                const box = child.getBoundingClientRect();
                const offset = y - box.top - box.height / 2;
                if (offset < 0 && offset > closest.offset) {
                    return { offset: offset, element: child };
                } else {
                    return closest;
                }
            }, { offset: Number.NEGATIVE_INFINITY }).element;
        }
    });

    // === FIND ERROR ===
    document.body.addEventListener('click', (e) => {
        const errorLine = e.target.closest('.error-line');
        if (errorLine) {
            const container = errorLine.closest('.find-error-code');
            if (container) {
                container.querySelectorAll('.error-line').forEach(l => {
                    l.classList.remove('selected', 'selected-line');
                    l.setAttribute('aria-pressed', 'false');
                });
            }
            errorLine.classList.add('selected');
            errorLine.setAttribute('aria-pressed', 'true');
        }
    });

    // === CHECK ANSWER ===
    document.body.addEventListener('click', (e) => {
        if (e.target.matches('.btn-check-quiz')) {
            const btn = e.target;
            const exerciseId = btn.dataset.exerciseId;
            const type = btn.dataset.type || 'fill-blank';
            checkQuiz(exerciseId, type, btn);
        } else if (e.target.matches('.btn-show-answer-quiz')) {
            const btn = e.target;
            const exerciseId = btn.dataset.exerciseId;
            const type = btn.dataset.type || 'fill-blank';
            const lessonId = btn.dataset.lesson || window.currentLessonId || '';
            showAnswer(exerciseId, type, lessonId);
        } else if (e.target.matches('.quiz-lang-btn')) {
            const lang = e.target.dataset.lang;
            if (lang) switchQuizLanguage(lang);
        }
    });
});

// Selector de Idioma para los Quizzes
function initQuizLanguageSelector() {
    const saved = localStorage.getItem(_quizLangStorageKey()) || 'python';
    switchQuizLanguage(saved);
}

function switchQuizLanguage(lang) {
    currentQuizLanguage = lang;
    try {
        localStorage.setItem(_quizLangStorageKey(), lang);
    } catch (e) {}

    // Actualizar botones de la barra
    document.querySelectorAll('.quiz-lang-btn').forEach(btn => {
        if (btn.dataset.lang === lang) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Actualizar tarjetas de ejercicios
    document.querySelectorAll('.exercise-card').forEach(card => {
        const hasJava = card.dataset.hasJava === 'true';
        const qPy = card.querySelector('.exercise-question-python');
        const qJava = card.querySelector('.exercise-question-java');
        const viewPy = card.querySelector('.exercise-lang-python');
        const viewJava = card.querySelector('.exercise-lang-java');
        const modeBadge = card.querySelector('.exercise-mode-indicator');
        const feedback = card.querySelector('.exercise-feedback');
        if (feedback) feedback.hidden = true;

        if (lang === 'java' && hasJava) {
            if (qPy) qPy.style.display = 'none';
            if (qJava) qJava.style.display = 'block';
            if (viewPy) viewPy.style.display = 'none';
            if (viewJava) viewJava.style.display = 'block';
            if (modeBadge) {
                modeBadge.textContent = 'Modo Java';
                modeBadge.className = 'exercise-mode-indicator lang-badge java-badge';
            }
        } else {
            if (qPy) qPy.style.display = 'block';
            if (qJava) qJava.style.display = 'none';
            if (viewPy) viewPy.style.display = 'block';
            if (viewJava) viewJava.style.display = 'none';
            if (modeBadge) {
                modeBadge.textContent = 'Modo Python';
                modeBadge.className = 'exercise-mode-indicator lang-badge python-badge';
            }
        }
    });
}

async function checkQuiz(exerciseId, type, btn) {
    const card = document.getElementById('exercise-' + exerciseId);
    if (!card) return;
    const feedback = card.querySelector('.exercise-feedback');
    const lessonId = (btn && btn.dataset.lesson) || window.currentLessonId || '';

    const isJavaActive = currentQuizLanguage === 'java' && card.dataset.hasJava === 'true';
    const lang = isJavaActive ? 'java' : 'python';
    const activeView = isJavaActive
        ? (card.querySelector('.exercise-lang-java') || card)
        : (card.querySelector('.exercise-lang-python') || card);

    const payload = {
        lesson_id: lessonId,
        exercise_id: exerciseId,
        lang: lang,
    };

    let selectedRadio = null;
    let inputs = [];

    if (type === 'fill-blank' || !type) {
        inputs = Array.from(activeView.querySelectorAll('.exercise-input'));
        payload.answers = inputs.map(inp => inp.value);
    } else if (type === 'multiple-choice') {
        selectedRadio = activeView.querySelector('input[type="radio"]:checked');
        if (!selectedRadio) {
            showFeedback(feedback, false, "Por favor selecciona una opción antes de comprobar.", card, exerciseId);
            return;
        }
        payload.answer = parseInt(selectedRadio.value, 10);
    } else if (type === 'reorder') {
        const items = Array.from(card.querySelectorAll('.reorder-item'));
        payload.answers = items.map(item => parseInt(item.dataset.originalIndex, 10));
    } else if (type === 'find-error') {
        const selected = card.querySelector('.error-line.selected, .error-line.selected-line');
        if (!selected) {
            showFeedback(feedback, false, "Por favor haz click sobre la línea donde crees que está el error.", card, exerciseId);
            return;
        }
        payload.answer = parseInt(selected.dataset.lineIndex, 10);
    }

    if (btn) btn.disabled = true;
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    try {
        const resp = await fetch('/api/progreso/ejercicio', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        });
        const data = await resp.json().catch(() => ({ ok: false }));
        if (!resp.ok || !data.ok) {
            showFeedback(feedback, false, data.error || "No se pudo validar tu respuesta. Intenta de nuevo.", card, exerciseId);
            if (btn) btn.disabled = false;
            return;
        }

        const isCorrect = Boolean(data.passed);
        const xpBlocked = Boolean(data.xp_blocked_by_solution || card.dataset.solutionViewed === 'true');
        const explanation = data.explanation || '';
        const hint = data.hint || card.dataset.hint || '';
        const blockedNote = xpBlocked
            ? ' <span style="opacity:0.85;">(Sin +25 XP porque consultaste la solución)</span>'
            : '';
        let message = '';

        if (type === 'fill-blank' || !type) {
            const results = Array.isArray(data.input_results) ? data.input_results : [];
            inputs.forEach((input, idx) => {
                if (results[idx]) {
                    input.classList.remove('input-incorrect');
                    input.classList.add('input-correct');
                } else {
                    input.classList.remove('input-correct');
                    input.classList.add('input-incorrect');
                }
            });
            if (isCorrect) {
                const langLabel = isJavaActive ? "Java" : "Python";
                message = `¡Correcto en ${langLabel}!${blockedNote}` + (explanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${escapeFeedbackHtml(explanation)}</div>` : "");
            } else {
                const expText = explanation || hint || "Revisa la sintaxis requerida (respeta mayúsculas y minúsculas) y los campos resaltados.";
                message = `<b>Hay errores en tu respuesta.</b><div class="exercise-explanation-box"><b>Orientación:</b> ${escapeFeedbackHtml(expText)}</div>`;
            }
        } else if (type === 'multiple-choice') {
            const selectedIdx = parseInt(selectedRadio.value, 10);
            activeView.querySelectorAll('.quiz-option-label').forEach((label, i) => {
                label.classList.remove('option-correct', 'option-incorrect');
                if (isCorrect && i === selectedIdx) {
                    label.classList.add('option-correct');
                } else if (!isCorrect && i === selectedIdx) {
                    label.classList.add('option-incorrect');
                }
            });
            if (isCorrect) {
                message = `¡Correcto!${blockedNote} ` + (explanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${escapeFeedbackHtml(explanation)}</div>` : "");
            } else {
                message = "<b>Opción incorrecta.</b> " + (explanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${escapeFeedbackHtml(explanation)}</div>` : "Esa opción no es la adecuada.");
            }
        } else if (type === 'reorder') {
            if (isCorrect) {
                message = `¡Correcto! El código está ordenado perfectamente.${blockedNote}` + (explanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${escapeFeedbackHtml(explanation)}</div>` : "");
            } else {
                message = "<b>El orden no es el correcto.</b> Recuerda el flujo lógico de ejecución.";
            }
        } else if (type === 'find-error') {
            if (isCorrect) {
                message = `¡Correcto!${blockedNote} ` + (explanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${escapeFeedbackHtml(explanation)}</div>` : "Has identificado la línea con el error.");
            } else {
                message = "<b>Línea incorrecta.</b> El error sintáctico o lógico no se encuentra en esa línea.";
            }
        }

        if (btn) btn.disabled = isCorrect;
        showFeedback(feedback, isCorrect, message, card, exerciseId);
        if (window.QuizSounds) window.QuizSounds.play(isCorrect);
        if (isCorrect && !xpBlocked && typeof window.onProgressXpUpdate === 'function') {
            window.onProgressXpUpdate(data, '¡Ejercicio completado!');
        }
    } catch (err) {
        console.error('Error al validar ejercicio:', err);
        showFeedback(feedback, false, "Error de conexión al validar tu respuesta.", card, exerciseId);
        if (btn) btn.disabled = false;
    }
}

function escapeFeedbackHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

async function showAnswer(exerciseId, type, lessonId) {
    const card = document.getElementById('exercise-' + exerciseId);
    if (!card) return;

    const isJavaActive = currentQuizLanguage === 'java' && card.dataset.hasJava === 'true';
    const lang = isJavaActive ? 'java' : 'python';
    const activeView = isJavaActive
        ? (card.querySelector('.exercise-lang-java') || card)
        : (card.querySelector('.exercise-lang-python') || card);
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    try {
        const resp = await fetch('/api/ejercicio/solucion', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                lesson_id: lessonId || window.currentLessonId || '',
                exercise_id: exerciseId,
                lang: lang
            })
        });
        const data = await resp.json().catch(() => ({ ok: false }));
        if (!resp.ok || !data.ok) return;

        if (data.xp_blocked) {
            card.dataset.solutionViewed = 'true';
        }

        if (data.type === 'fill-blank') {
            const inputs = activeView.querySelectorAll('.exercise-input');
            const solAnswers = Array.isArray(data.answers) ? data.answers : [];
            inputs.forEach((input, idx) => {
                input.value = solAnswers[idx] !== undefined ? solAnswers[idx] : '';
                input.classList.remove('input-incorrect');
                input.classList.add('input-correct');
            });
        } else if (data.type === 'multiple-choice') {
            const correctIndex = String(data.correct_index);
            const correctRadio = activeView.querySelector(`input[type="radio"][value="${correctIndex}"]`);
            if (correctRadio) {
                correctRadio.checked = true;
                activeView.querySelectorAll('.quiz-option-label').forEach((lbl, i) => {
                    lbl.classList.remove('selected', 'option-incorrect');
                    if (String(i) === correctIndex) {
                        lbl.classList.add('option-correct');
                    }
                });
            }
        } else if (data.type === 'reorder') {
            const list = card.querySelector('.reorder-list');
            if (list) {
                const items = Array.from(list.querySelectorAll('.reorder-item'));
                items.sort((a, b) => parseInt(a.dataset.originalIndex, 10) - parseInt(b.dataset.originalIndex, 10));
                items.forEach(item => list.appendChild(item));
                if (typeof window._updateReorderButtons === 'function') {
                    window._updateReorderButtons(list);
                }
            }
        } else if (data.type === 'find-error') {
            const errorLineEl = card.querySelector(`.error-line[data-line-index="${data.error_line}"]`);
            if (errorLineEl) {
                card.querySelectorAll('.error-line').forEach(l => {
                    l.classList.remove('selected', 'selected-line');
                    l.setAttribute('aria-pressed', 'false');
                });
                errorLineEl.classList.add('selected-line');
                errorLineEl.setAttribute('aria-pressed', 'true');
            }
        }

        const feedback = card.querySelector('.exercise-feedback');
        const explanation = data.explanation || '';
        const xpNote = data.xp_blocked
            ? ' Al consultar la solución, este ejercicio no otorgará +25 XP.'
            : '';
        const msg = `<b>Respuesta mostrada.</b>${xpNote}` + (explanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${escapeFeedbackHtml(explanation)}</div>` : "");
        showFeedback(feedback, true, msg, card, exerciseId);
    } catch (err) {
        console.error('Error al cargar solución:', err);
    }
}

function showFeedback(element, isCorrect, messageHtml, card, exerciseId) {
    if (!element) return;
    element.innerHTML = messageHtml;
    element.hidden = false;

    if (isCorrect) {
        element.classList.remove('feedback-incorrect');
        element.classList.add('feedback-correct');
    } else {
        element.classList.remove('feedback-correct');
        element.classList.add('feedback-incorrect');

        // Botón de ayuda con el Tutor IA
        if (card && exerciseId && window.AITutor) {
            const qPy = card.querySelector('.exercise-question-python');
            const qJava = card.querySelector('.exercise-question-java');
            const isJava = currentQuizLanguage === 'java' && card.dataset.hasJava === 'true';
            const questionText = (isJava && qJava) ? qJava.textContent.trim() : (qPy ? qPy.textContent.trim() : '');

            const helpWrap = document.createElement('div');
            helpWrap.style.marginTop = '0.5rem';

            const helpBtn = document.createElement('button');
            helpBtn.type = 'button';
            helpBtn.className = 'btn-ask-ai-error';
            helpBtn.innerHTML = '<b>¿Por qué me equivoqué?</b> (Explicación con Tutor IA)';

            helpBtn.addEventListener('click', () => {
                let userAnswer = '';
                const checkedRadio = card.querySelector('input[type="radio"]:checked');
                if (checkedRadio) {
                    const label = checkedRadio.closest('label');
                    userAnswer = label ? label.textContent.trim() : checkedRadio.value;
                } else {
                    const inputs = card.querySelectorAll('.exercise-input');
                    inputs.forEach(inp => { if (inp.value) userAnswer += inp.value + ' '; });
                }
                const promptDetail = userAnswer.trim()
                    ? `Mi respuesta en ${isJava ? 'Java' : 'Python'} fue: "${userAnswer.trim()}". ¿Por qué es incorrecta y qué concepto debo repasar?`
                    : 'No entendí cómo resolver este ejercicio, ¿me das una pista conceptual?';
                window.AITutor.hint(exerciseId, questionText, promptDetail);
            });

            helpWrap.appendChild(helpBtn);
            element.appendChild(helpWrap);
        }
    }
}
