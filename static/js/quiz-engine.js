/**
 * Quiz Engine
 * Handles quiz flow: start, countdown timer, questions, navigation, scoring, results
 */
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('quiz-container');
    if (!container) return;

    const quizId = container.dataset.quizId;
    const totalQuestions = parseInt(container.dataset.total, 10);
    const timeLimit = parseInt(container.dataset.timeLimit || '0', 10);

    const startScreen = document.getElementById('quiz-start');
    const activeScreen = document.getElementById('quiz-active');
    const resultsScreen = document.getElementById('quiz-results');

    const btnStart = document.getElementById('btn-start-quiz');
    const btnNext = document.getElementById('btn-quiz-next');
    const btnRetry = document.getElementById('btn-quiz-retry');

    const counterEl = document.getElementById('quiz-counter');
    const progressFill = document.getElementById('quiz-progress-fill');
    const timerEl = document.getElementById('quiz-timer');

    let currentQuestion = 0;
    let userAnswers = {};
    let timerInterval = null;
    let secondsRemaining = Number.isFinite(timeLimit) && timeLimit > 0 ? timeLimit : 0;
    let startTime = null;
    let isSubmitting = false;

    if (!Number.isFinite(totalQuestions) || totalQuestions <= 0) {
        if (btnStart) btnStart.disabled = true;
        return;
    }

    function formatTime(secs) {
        const safe = Math.max(0, secs);
        const mins = Math.floor(safe / 60);
        const rem = safe % 60;
        return `${mins}:${rem.toString().padStart(2, '0')}`;
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    function startTimer() {
        stopTimer();
        if (!timerEl || !Number.isFinite(timeLimit) || timeLimit <= 0) return;
        secondsRemaining = timeLimit;
        timerEl.classList.remove('warning', 'danger');
        timerEl.textContent = formatTime(secondsRemaining);

        timerInterval = setInterval(() => {
            secondsRemaining--;
            timerEl.textContent = formatTime(secondsRemaining);

            if (secondsRemaining <= 60) {
                timerEl.classList.add('danger');
                timerEl.classList.remove('warning');
            } else if (secondsRemaining <= 120) {
                timerEl.classList.add('warning');
            }

            if (secondsRemaining <= 0) {
                stopTimer();
                captureCurrentSelection();
                submitQuiz(true);
            }
        }, 1000);
    }

    function captureCurrentSelection() {
        const slide = getSlide(currentQuestion);
        if (!slide) return false;
        const selected = slide.querySelector('input[type="radio"]:checked');
        if (!selected) return false;
        const qid = slide.dataset.qid || String(currentQuestion);
        userAnswers[qid] = parseInt(selected.value, 10);
        return true;
    }

    // Start quiz
    btnStart.addEventListener('click', () => {
        startScreen.hidden = true;
        activeScreen.hidden = false;
        currentQuestion = 0;
        userAnswers = {};
        isSubmitting = false;
        startTime = Date.now();
        startTimer();
        showQuestion(0);
    });

    // Next / Finish question (envía respuestas al servidor al finalizar para calificación anti-trampa)
    btnNext.addEventListener('click', async () => {
        if (!captureCurrentSelection()) return;

        currentQuestion++;
        if (currentQuestion >= totalQuestions) {
            await submitQuiz(false);
        } else {
            showQuestion(currentQuestion);
        }
    });

    // Retry
    btnRetry.addEventListener('click', () => {
        stopTimer();
        resultsScreen.hidden = true;
        userAnswers = {};
        isSubmitting = false;
        if (timerEl && timeLimit > 0) {
            timerEl.classList.remove('warning', 'danger');
            timerEl.textContent = formatTime(timeLimit);
        }
        document.querySelectorAll('.quiz-question-slide').forEach(slide => {
            slide.querySelectorAll('input[type="radio"]').forEach(r => {
                r.checked = false;
                r.disabled = false;
            });
            slide.querySelectorAll('.quiz-option').forEach(o => {
                o.classList.remove('correct', 'incorrect');
            });
        });
        startScreen.hidden = false;
    });

    // Option click handler - select the radio when clicking the label
    document.querySelectorAll('.quiz-option').forEach(option => {
        option.addEventListener('click', () => {
            const radio = option.querySelector('input[type="radio"]');
            if (radio && !radio.disabled) radio.checked = true;
        });
    });

    function getSlide(index) {
        return document.querySelector(`.quiz-question-slide[data-question="${index}"]`);
    }

    function showQuestion(index) {
        document.querySelectorAll('.quiz-question-slide').forEach(s => s.hidden = true);
        const slide = getSlide(index);
        if (slide) slide.hidden = false;

        counterEl.textContent = `Pregunta ${index + 1} de ${totalQuestions}`;
        const pct = ((index + 1) / totalQuestions * 100);
        progressFill.style.width = pct + '%';
        btnNext.disabled = false;
        btnNext.textContent = index < totalQuestions - 1 ? 'Siguiente Pregunta ❯' : 'Ver Resultados ❯';
    }

    async function submitQuiz(timedOut) {
        if (isSubmitting) return;
        isSubmitting = true;
        stopTimer();

        btnNext.disabled = true;
        btnNext.textContent = timedOut ? 'Tiempo agotado, calificando...' : 'Calificando...';
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
        const elapsedSeconds = startTime ? Math.max(0, Math.round((Date.now() - startTime) / 1000)) : 0;

        try {
            const resp = await fetch('/api/quiz/resultado', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    quiz_id: quizId,
                    answers: userAnswers,
                    time_taken: elapsedSeconds
                })
            });
            const data = await resp.json().catch(() => ({ ok: false }));
            if (!resp.ok || !data.ok) {
                alert(data.error || 'No se pudo calificar el quiz. Intenta de nuevo.');
                isSubmitting = false;
                currentQuestion = Math.min(currentQuestion, totalQuestions - 1);
                showQuestion(currentQuestion);
                return;
            }
            showResults(data, timedOut);
        } catch (err) {
            console.error('Error al calificar quiz:', err);
            alert('Error de conexión al enviar el quiz.');
            isSubmitting = false;
            currentQuestion = Math.min(currentQuestion, totalQuestions - 1);
            showQuestion(currentQuestion);
        }
    }

    function showResults(data, timedOut) {
        activeScreen.hidden = true;
        resultsScreen.hidden = false;

        const score = data.score || 0;
        const total = data.total || totalQuestions;
        const pct = Number.isFinite(data.percentage) ? data.percentage : Math.round((score / total) * 100);

        if (window.QuizSounds) window.QuizSounds.play(pct >= 70);

        document.getElementById('score-text').textContent = pct + '%';
        document.getElementById('quiz-results-detail').textContent = timedOut
            ? `Tiempo agotado. Obtuviste ${score} de ${total} respuestas correctas.`
            : `¡Obtuviste ${score} de ${total} correctas!`;

        const circle = document.getElementById('score-circle-fill');
        const circumference = 2 * Math.PI * 54; // r=54
        const offset = circumference - (pct / 100) * circumference;
        setTimeout(() => {
            circle.style.strokeDashoffset = offset;
        }, 100);

        if (pct >= 80) {
            circle.style.stroke = '#66bb6a';
            document.getElementById('score-text').style.color = '#66bb6a';
        } else if (pct >= 50) {
            circle.style.stroke = '#ffc107';
            document.getElementById('score-text').style.color = '#ffc107';
        } else {
            circle.style.stroke = '#ef5350';
            document.getElementById('score-text').style.color = '#ef5350';
        }
    }
});
