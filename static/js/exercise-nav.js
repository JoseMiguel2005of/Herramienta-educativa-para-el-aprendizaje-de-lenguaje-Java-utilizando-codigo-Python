/**
 * Exercise Navigation & Validation (Dual Python/Java Mode)
 */
let standaloneQuizLang = localStorage.getItem('py2java_quiz_lang') || 'python';

function switchStandaloneExerciseLang(lang) {
    standaloneQuizLang = lang;
    localStorage.setItem('py2java_quiz_lang', lang);

    document.querySelectorAll('.quiz-lang-btn').forEach(btn => {
        if (btn.dataset.lang === lang) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    const card = document.getElementById('exercise-card-main');
    if (!card) return;

    const hasJava = card.dataset.hasJava === 'true';
    const qPy = card.querySelector('.exercise-question-python');
    const qJava = card.querySelector('.exercise-question-java');
    const viewPy = card.querySelector('.exercise-lang-python');
    const viewJava = card.querySelector('.exercise-lang-java');
    const indicator = card.querySelector('.exercise-mode-indicator');
    const feedback = document.getElementById('exercise-feedback');
    if (feedback) feedback.hidden = true;

    if (lang === 'java' && hasJava) {
        if (qPy) qPy.style.display = 'none';
        if (qJava) qJava.style.display = 'block';
        if (viewPy) viewPy.style.display = 'none';
        if (viewJava) viewJava.style.display = 'block';
        if (indicator) {
            indicator.textContent = 'Modo Java';
            indicator.className = 'exercise-mode-indicator lang-badge java-badge';
        }
    } else {
        if (qPy) qPy.style.display = 'block';
        if (qJava) qJava.style.display = 'none';
        if (viewPy) viewPy.style.display = 'block';
        if (viewJava) viewJava.style.display = 'none';
        if (indicator) {
            indicator.textContent = 'Modo Python';
            indicator.className = 'exercise-mode-indicator lang-badge python-badge';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const submitBtn = document.getElementById('btn-submit-exercise');
    const hintBtn = document.getElementById('btn-hint');
    const showBtn = document.getElementById('btn-show-answer');
    const feedback = document.getElementById('exercise-feedback');
    const hintBox = document.getElementById('hint-box');

    // Inicializar idioma guardado
    const saved = localStorage.getItem('py2java_quiz_lang') || 'python';
    switchStandaloneExerciseLang(saved);

    // Enviar / Comprobar respuesta (calificación estricta en servidor)
    if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
            const card = document.getElementById('exercise-card-main');
            if (!card) return;

            const isJavaActive = standaloneQuizLang === 'java' && card.dataset.hasJava === 'true';
            const lang = isJavaActive ? 'java' : 'python';
            const activeView = isJavaActive
                ? (card.querySelector('.exercise-lang-java') || card)
                : (card.querySelector('.exercise-lang-python') || card);

            const mcBlock = activeView.querySelector('.exercise-options-block');
            const templateArea = activeView.querySelector('.exercise-template-area');
            const freeformInput = activeView.querySelector('.exercise-freeform-editor');

            const payload = {
                lesson_id: submitBtn.dataset.lesson || '',
                exercise_id: submitBtn.dataset.exerciseId || '',
                lang: lang,
            };

            let selectedIndex = -1;
            let inputs = [];

            if (mcBlock) {
                const selected = mcBlock.querySelector('input[type="radio"]:checked');
                if (!selected) {
                    showFeedback(false, 'Por favor selecciona una opción antes de comprobar.');
                    return;
                }
                selectedIndex = parseInt(selected.value, 10);
                payload.answer = selectedIndex;
            } else if (templateArea) {
                inputs = Array.from(templateArea.querySelectorAll('.exercise-input'));
                payload.answers = inputs.map(inp => inp.value);
            } else if (freeformInput) {
                const userCode = freeformInput.value.trim();
                if (userCode.length === 0) {
                    showFeedback(false, 'Por favor escribe tu código antes de comprobar.');
                    return;
                }
                payload.answer = userCode;
            }

            submitBtn.disabled = true;
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
                    showFeedback(false, data.error || 'No se pudo validar tu respuesta.');
                    submitBtn.disabled = false;
                    return;
                }

                const isCorrect = Boolean(data.passed);
                if (mcBlock) {
                    mcBlock.querySelectorAll('.quiz-option-label').forEach((label, i) => {
                        label.classList.remove('option-correct', 'option-incorrect');
                        if (i === selectedIndex) {
                            label.classList.add(isCorrect ? 'option-correct' : 'option-incorrect');
                        }
                    });
                    showFeedback(
                        isCorrect,
                        isCorrect ? '¡Correcto! Excelente trabajo.' : 'Opción incorrecta. Intenta de nuevo o consulta una pista.'
                    );
                } else if (templateArea) {
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
                    showFeedback(
                        isCorrect,
                        isCorrect ? '¡Correcto! Completaste el código adecuadamente.' : 'Revisa los campos resaltados e intenta de nuevo.'
                    );
                } else if (freeformInput) {
                    showFeedback(
                        isCorrect,
                        isCorrect ? '¡Correcto! Tu respuesta coincide con la solución esperada.' : 'Tu respuesta no coincide aún. Usa la pista o el Tutor IA para revisar.'
                    );
                }

                if (isCorrect && typeof window.onProgressXpUpdate === 'function') {
                    window.onProgressXpUpdate(data, '¡Ejercicio completado!');
                }
                submitBtn.disabled = isCorrect;
            } catch (err) {
                console.error('Error al validar ejercicio:', err);
                showFeedback(false, 'Error de conexión al validar tu respuesta.');
                submitBtn.disabled = false;
            }
        });
    }

    // Pista
    if (hintBtn) {
        hintBtn.addEventListener('click', () => {
            if (hintBox) {
                hintBox.hidden = !hintBox.hidden;
            }
        });
    }

    // Ver solución (consulta pedagógica sin otorgar XP)
    if (showBtn) {
        showBtn.addEventListener('click', async () => {
            const card = document.getElementById('exercise-card-main');
            if (!card) return;

            const isJavaActive = standaloneQuizLang === 'java' && card.dataset.hasJava === 'true';
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
                        lesson_id: showBtn.dataset.lesson || '',
                        exercise_id: showBtn.dataset.exerciseId || '',
                        lang: lang
                    })
                });
                const data = await resp.json().catch(() => ({ ok: false }));
                if (!resp.ok || !data.ok) return;

                const mcBlock = activeView.querySelector('.exercise-options-block');
                const templateArea = activeView.querySelector('.exercise-template-area');
                const freeformInput = activeView.querySelector('.exercise-freeform-editor');

                if (mcBlock && data.type === 'multiple-choice') {
                    const correctIndex = data.correct_index;
                    mcBlock.querySelectorAll('.quiz-option-label').forEach((label, i) => {
                        label.classList.remove('option-correct', 'option-incorrect');
                        if (i === correctIndex) {
                            label.classList.add('option-correct');
                        }
                        const radio = label.querySelector('input[type="radio"]');
                        if (radio && i === correctIndex) radio.checked = true;
                    });
                    showFeedback(true, 'Respuesta mostrada.', true);
                } else if (templateArea && Array.isArray(data.answers)) {
                    const inputs = templateArea.querySelectorAll('.exercise-input');
                    inputs.forEach((input, idx) => {
                        input.value = data.answers[idx] !== undefined ? data.answers[idx] : '';
                        input.classList.remove('input-incorrect');
                        input.classList.add('input-correct');
                    });
                    showFeedback(true, 'Solución completada.', true);
                } else if (freeformInput && Array.isArray(data.answers) && data.answers.length > 0) {
                    freeformInput.value = data.answers[0];
                    showFeedback(true, 'Solución mostrada.', true);
                }
            } catch (err) {
                console.error('Error al cargar solución:', err);
            }
        });
    }

    // Navegación con teclado
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
            const nextBtn = document.querySelector('.exercise-nav-next');
            if (nextBtn) nextBtn.click();
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
            const prevBtn = document.querySelector('.exercise-nav-prev');
            if (prevBtn) prevBtn.click();
        }
    });

    function showFeedback(isCorrect, message, silent) {
        if (!silent && window.QuizSounds) window.QuizSounds.play(isCorrect);
        if (!feedback) return;
        feedback.textContent = message;
        feedback.hidden = false;
        feedback.classList.remove('feedback-correct', 'feedback-incorrect');
        feedback.classList.add(isCorrect ? 'feedback-correct' : 'feedback-incorrect');
    }
});
