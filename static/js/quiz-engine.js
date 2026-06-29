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
    let score = 0;
    let answers = [];
    let answered = false;

    // Start quiz
    btnStart.addEventListener('click', () => {
        startScreen.hidden = true;
        activeScreen.hidden = false;
        currentQuestion = 0;
        score = 0;
        answers = [];
        showQuestion(0);
    });

    // Next question
    btnNext.addEventListener('click', () => {
        if (!answered) {
            // Check if user selected an option
            const slide = getSlide(currentQuestion);
            const selected = slide.querySelector('input[type="radio"]:checked');
            if (!selected) return; // No selection

            // Check answer
            const correctIndex = parseInt(slide.dataset.correct);
            const selectedIndex = parseInt(selected.value);
            answered = true;

            const options = slide.querySelectorAll('.quiz-option');
            options.forEach((opt, i) => {
                const radio = opt.querySelector('input[type="radio"]');
                radio.disabled = true;
                if (i === correctIndex) {
                    opt.classList.add('correct');
                } else if (i === selectedIndex && selectedIndex !== correctIndex) {
                    opt.classList.add('incorrect');
                }
            });

            if (selectedIndex === correctIndex) {
                score++;
            }
            answers.push({ question: currentQuestion, selected: selectedIndex, correct: correctIndex });

            // Change button text
            if (currentQuestion < totalQuestions - 1) {
                btnNext.textContent = 'Siguiente Pregunta ❯';
            } else {
                btnNext.textContent = 'Ver Resultados ❯';
            }
            return;
        }

        // Move to next question
        answered = false;
        currentQuestion++;

        if (currentQuestion >= totalQuestions) {
            showResults();
        } else {
            showQuestion(currentQuestion);
            btnNext.textContent = 'Enviar Respuesta';
        }
    });

    // Retry
    btnRetry.addEventListener('click', () => {
        resultsScreen.hidden = true;
        // Reset all questions
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
            if (answered) return;
            const radio = option.querySelector('input[type="radio"]');
            radio.checked = true;
        });
    });

    function getSlide(index) {
        return document.querySelector(`.quiz-question-slide[data-question="${index}"]`);
    }

    function showQuestion(index) {
        // Hide all slides
        document.querySelectorAll('.quiz-question-slide').forEach(s => s.hidden = true);
        // Show current
        const slide = getSlide(index);
        if (slide) slide.hidden = false;

        // Update counter
        counterEl.textContent = `Pregunta ${index + 1} de ${totalQuestions}`;
        // Update progress
        const pct = ((index + 1) / totalQuestions * 100);
        progressFill.style.width = pct + '%';
        // Reset button
        btnNext.textContent = 'Enviar Respuesta';
    }

    function showResults() {
        activeScreen.hidden = true;
        resultsScreen.hidden = false;

        const pct = Math.round((score / totalQuestions) * 100);
        document.getElementById('score-text').textContent = pct + '%';
        document.getElementById('quiz-results-detail').textContent =
            `¡Obtuviste ${score} de ${totalQuestions} correctas!`;

        // Animate circle
        const circle = document.getElementById('score-circle-fill');
        const circumference = 2 * Math.PI * 54; // r=54
        const offset = circumference - (pct / 100) * circumference;
        setTimeout(() => {
            circle.style.strokeDashoffset = offset;
        }, 100);

        // Change color based on score
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

        // Save result
        fetch('/api/quiz/resultado', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                quiz_id: quizId,
                score: score,
                total: totalQuestions
            })
        }).catch(() => {});
    }
});
