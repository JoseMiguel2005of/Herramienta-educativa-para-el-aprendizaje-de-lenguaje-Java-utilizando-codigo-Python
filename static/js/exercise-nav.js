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

    // Enviar / Comprobar respuesta
    if (submitBtn) {
        submitBtn.addEventListener('click', () => {
            const card = document.getElementById('exercise-card-main');
            if (!card) return;

            const isJavaActive = standaloneQuizLang === 'java' && card.dataset.hasJava === 'true';
            const activeView = isJavaActive 
                ? (card.querySelector('.exercise-lang-java') || card)
                : (card.querySelector('.exercise-lang-python') || card);

            const mcBlock = activeView.querySelector('.exercise-options-block');
            const templateArea = activeView.querySelector('.exercise-template-area');
            const freeformInput = activeView.querySelector('.exercise-freeform-editor');

            if (mcBlock) {
                // Opción Múltiple
                const answerData = mcBlock.querySelector('.quiz-answer-data');
                const correctIndex = answerData ? parseInt(answerData.getAttribute('data-correct')) : -1;

                const selected = mcBlock.querySelector('input[type="radio"]:checked');
                if (!selected) {
                    showFeedback(false, 'Por favor selecciona una opción antes de comprobar.');
                    return;
                }

                const selectedIndex = parseInt(selected.value);
                const isCorrect = (selectedIndex === correctIndex);

                mcBlock.querySelectorAll('.quiz-option-label').forEach((label, i) => {
                    label.classList.remove('option-correct', 'option-incorrect');
                    if (i === correctIndex) {
                        label.classList.add('option-correct');
                    } else if (i === selectedIndex && !isCorrect) {
                        label.classList.add('option-incorrect');
                    }
                });

                showFeedback(isCorrect,
                    isCorrect ? '¡Correcto! Excelente trabajo.' : 'Opción incorrecta. La respuesta correcta está resaltada en verde.');

                if (isCorrect) {
                    trackExerciseProgress(submitBtn.dataset.lesson, submitBtn.dataset.exerciseId);
                }

            } else if (templateArea) {
                // Espacios en blanco (Fill-in-the-blank)
                const inputs = templateArea.querySelectorAll('.exercise-input');
                let allCorrect = true;

                inputs.forEach(input => {
                    const answer = (input.dataset.answer || '').trim().toLowerCase();
                    const userVal = input.value.trim().toLowerCase();
                    if (userVal === answer) {
                        input.classList.remove('input-incorrect');
                        input.classList.add('input-correct');
                    } else {
                        input.classList.remove('input-correct');
                        input.classList.add('input-incorrect');
                        allCorrect = false;
                    }
                });

                showFeedback(allCorrect,
                    allCorrect ? '¡Correcto! Completaste el código adecuadamente.' : 'Revisa los campos resaltados en rojo e intenta de nuevo.');

                if (allCorrect) {
                    trackExerciseProgress(submitBtn.dataset.lesson, submitBtn.dataset.exerciseId);
                }
            } else if (freeformInput) {
                const userCode = freeformInput.value.trim();
                if (userCode.length === 0) {
                    showFeedback(false, 'Por favor escribe tu código antes de comprobar.');
                    return;
                }
                showFeedback(true, '¡Respuesta enviada! Puedes usar el botón de Pista o consultar al Tutor IA si necesitas retroalimentación.');
                trackExerciseProgress(submitBtn.dataset.lesson, submitBtn.dataset.exerciseId);
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

    // Ver solución
    if (showBtn) {
        showBtn.addEventListener('click', () => {
            const card = document.getElementById('exercise-card-main');
            if (!card) return;

            const isJavaActive = standaloneQuizLang === 'java' && card.dataset.hasJava === 'true';
            const activeView = isJavaActive 
                ? (card.querySelector('.exercise-lang-java') || card)
                : (card.querySelector('.exercise-lang-python') || card);

            const mcBlock = activeView.querySelector('.exercise-options-block');
            const templateArea = activeView.querySelector('.exercise-template-area');

            if (mcBlock) {
                const answerData = mcBlock.querySelector('.quiz-answer-data');
                const correctIndex = answerData ? parseInt(answerData.getAttribute('data-correct')) : -1;

                mcBlock.querySelectorAll('.quiz-option-label').forEach((label, i) => {
                    label.classList.remove('option-correct', 'option-incorrect');
                    if (i === correctIndex) {
                        label.classList.add('option-correct');
                    }
                    const radio = label.querySelector('input[type="radio"]');
                    if (radio && i === correctIndex) radio.checked = true;
                });
                showFeedback(true, 'Respuesta mostrada.');
            } else if (templateArea) {
                const inputs = templateArea.querySelectorAll('.exercise-input');
                inputs.forEach(input => {
                    input.value = input.dataset.answer || '';
                    input.classList.remove('input-incorrect');
                    input.classList.add('input-correct');
                });
                showFeedback(true, 'Solución completada.');
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

    function showFeedback(isCorrect, message) {
        if (!feedback) return;
        feedback.textContent = message;
        feedback.hidden = false;
        feedback.classList.remove('feedback-correct', 'feedback-incorrect');
        feedback.classList.add(isCorrect ? 'feedback-correct' : 'feedback-incorrect');
    }

    function trackExerciseProgress(lessonId, exerciseId) {
        fetch('/api/progreso/ejercicio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lesson_id: lessonId,
                exercise_id: exerciseId,
                passed: true
            })
        }).catch(() => {});
    }
});
