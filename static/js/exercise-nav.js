/**
 * Exercise Navigation & Validation
 * Handles individual exercise page interactions
 */
document.addEventListener('DOMContentLoaded', () => {
    const submitBtn = document.getElementById('btn-submit-exercise');
    const hintBtn = document.getElementById('btn-hint');
    const showBtn = document.getElementById('btn-show-answer');
    const feedback = document.getElementById('exercise-feedback');
    const hintBox = document.getElementById('hint-box');
    const freeformInput = document.getElementById('exercise-freeform-input');

    // Submit answer
    if (submitBtn) {
        submitBtn.addEventListener('click', () => {
            const templateArea = document.getElementById('exercise-template');

            if (templateArea) {
                // Fill-in-the-blank mode
                const inputs = templateArea.querySelectorAll('.exercise-input');
                let allCorrect = true;

                inputs.forEach(input => {
                    const answer = input.dataset.answer;
                    if (input.value.trim() === answer) {
                        input.classList.remove('input-incorrect');
                        input.classList.add('input-correct');
                    } else {
                        input.classList.remove('input-correct');
                        input.classList.add('input-incorrect');
                        allCorrect = false;
                    }
                });

                showFeedback(allCorrect,
                    allCorrect ? '✅ Correct! Well done.' : '❌ Not quite. Check the highlighted fields and try again.');

                if (allCorrect) {
                    trackExerciseProgress(submitBtn.dataset.lesson, submitBtn.dataset.exerciseId);
                }
            } else if (freeformInput) {
                // Freeform text comparison mode
                const userCode = freeformInput.value.trim();
                if (userCode.length === 0) {
                    showFeedback(false, 'Please write your answer first.');
                    return;
                }
                // In freeform mode, we just mark as attempted and let AI tutor help
                showFeedback(true, '✅ Answer submitted! Use the hint button if you need guidance.');
                trackExerciseProgress(submitBtn.dataset.lesson, submitBtn.dataset.exerciseId);
            }
        });
    }

    // Show hint
    if (hintBtn) {
        hintBtn.addEventListener('click', () => {
            if (hintBox) {
                hintBox.hidden = !hintBox.hidden;
            }
        });
    }

    // Show answer
    if (showBtn) {
        showBtn.addEventListener('click', () => {
            const templateArea = document.getElementById('exercise-template');
            if (templateArea) {
                const inputs = templateArea.querySelectorAll('.exercise-input');
                inputs.forEach(input => {
                    input.value = input.dataset.answer;
                    input.classList.remove('input-incorrect');
                    input.classList.add('input-correct');
                });
            }
            showFeedback(true, 'Answer shown.');
        });
    }

    // Keyboard navigation
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
