/**
 * Quiz Engine
 * Handles quiz flow: start, questions, navigation, scoring, results
 */
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('quiz-container');
    if (!container) return;

    const quizId = container.dataset.quizId;
    const totalQuestions = parseInt(container.dataset.total);

    const startScreen = document.getElementById('quiz-start');
    const activeScreen = document.getElementById('quiz-active');
    const resultsScreen = document.getElementById('quiz-results');

    const btnStart = document.getElementById('btn-start-quiz');
    const btnNext = document.getElementById('btn-quiz-next');
    const btnRetry = document.getElementById('btn-quiz-retry');

    const counterEl = document.getElementById('quiz-counter');
    const progressFill = document.getElementById('quiz-progress-fill');

    let currentQuestion = 0;
    let userAnswers = {};

    // Start quiz
    btnStart.addEventListener('click', () => {
        startScreen.hidden = true;
        activeScreen.hidden = false;
        currentQuestion = 0;
        userAnswers = {};
        showQuestion(0);
    });

    // Next / Finish question (envía respuestas al servidor al finalizar para calificación anti-trampa)
    btnNext.addEventListener('click', async () => {
        const slide = getSlide(currentQuestion);
        const selected = slide.querySelector('input[type="radio"]:checked');
        if (!selected) return; // No selection

        const qid = slide.dataset.qid || String(currentQuestion);
        userAnswers[qid] = parseInt(selected.value, 10);

        currentQuestion++;
        if (currentQuestion >= totalQuestions) {
            await submitQuiz();
        } else {
            showQuestion(currentQuestion);
        }
    });

    // Retry
    btnRetry.addEventListener('click', () => {
        resultsScreen.hidden = true;
        userAnswers = {};
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

    async function submitQuiz() {
        btnNext.disabled = true;
        btnNext.textContent = 'Calificando...';
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        try {
            const resp = await fetch('/api/quiz/resultado', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    quiz_id: quizId,
                    answers: userAnswers
                })
            });
            const data = await resp.json().catch(() => ({ ok: false }));
            if (!resp.ok || !data.ok) {
                alert(data.error || 'No se pudo calificar el quiz. Intenta de nuevo.');
                currentQuestion = totalQuestions - 1;
                showQuestion(currentQuestion);
                return;
            }
            showResults(data);
        } catch (err) {
            console.error('Error al calificar quiz:', err);
            alert('Error de conexión al enviar el quiz.');
            currentQuestion = totalQuestions - 1;
            showQuestion(currentQuestion);
        }
    }

    function showResults(data) {
        activeScreen.hidden = true;
        resultsScreen.hidden = false;

        const score = data.score || 0;
        const total = data.total || totalQuestions;
        const pct = Number.isFinite(data.percentage) ? data.percentage : Math.round((score / total) * 100);

        if (window.QuizSounds) window.QuizSounds.play(pct >= 70);

        document.getElementById('score-text').textContent = pct + '%';
        document.getElementById('quiz-results-detail').textContent =
            `¡Obtuviste ${score} de ${total} correctas!`;

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
