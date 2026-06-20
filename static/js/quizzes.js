document.addEventListener('DOMContentLoaded', () => {
    // === MULTIPLE CHOICE ===
    document.body.addEventListener('change', (e) => {
        if (e.target.matches('.quiz-option-label input[type="radio"]')) {
            const container = e.target.closest('.quiz-options');
            container.querySelectorAll('.quiz-option-label').forEach(lbl => lbl.classList.remove('selected'));
            e.target.closest('.quiz-option-label').classList.add('selected');
        }
    });

    // === REORDER ===
    document.querySelectorAll('.reorder-list').forEach(list => {
        let draggedItem = null;
        
        list.querySelectorAll('.reorder-item').forEach(item => {
            item.addEventListener('dragstart', function() {
                draggedItem = this;
                setTimeout(() => this.classList.add('dragging'), 0);
            });
            
            item.addEventListener('dragend', function() {
                setTimeout(() => {
                    this.classList.remove('dragging');
                    draggedItem = null;
                }, 0);
            });
            
            item.addEventListener('dragover', function(e) {
                e.preventDefault();
                const afterElement = getDragAfterElement(list, e.clientY);
                if (afterElement == null) {
                    list.appendChild(draggedItem);
                } else {
                    list.insertBefore(draggedItem, afterElement);
                }
            });
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
            container.querySelectorAll('.error-line').forEach(l => l.classList.remove('selected'));
            errorLine.classList.add('selected');
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
            showAnswer(exerciseId, type);
        }
    });
});

function checkQuiz(exerciseId, type, btn) {
    const card = document.getElementById('exercise-' + exerciseId);
    if (!card) return;
    const feedback = card.querySelector('.exercise-feedback');
    let isCorrect = false;
    let message = "";

    if (type === 'fill-blank') {
        const inputs = card.querySelectorAll('.exercise-input');
        isCorrect = true;
        inputs.forEach(input => {
            const answer = input.dataset.answer;
            if (input.value.trim() === answer) {
                input.classList.remove('input-incorrect');
                input.classList.add('input-correct');
            } else {
                input.classList.remove('input-correct');
                input.classList.add('input-incorrect');
                isCorrect = false;
            }
        });
        message = isCorrect ? "¡Correcto! Excelente trabajo." : "Hay errores. Revisa las casillas rojas e intenta de nuevo.";
    } 
    else if (type === 'multiple-choice') {
        const selected = card.querySelector('input[type="radio"]:checked');
        if (!selected) {
            showFeedback(feedback, false, "Por favor selecciona una opción.");
            return;
        }
        const dataDiv = card.querySelector('.quiz-answer-data');
        const correctIndex = dataDiv.dataset.correct;
        const explanation = dataDiv.dataset.explanation || "";
        
        isCorrect = (selected.value === correctIndex);
        message = isCorrect ? "¡Correcto! " + explanation : "Incorrecto. Inténtalo de nuevo.";
    }
    else if (type === 'reorder') {
        const items = card.querySelectorAll('.reorder-item');
        const dataDiv = card.querySelector('.quiz-answer-data');
        const correctCount = parseInt(dataDiv.dataset.correctCount);
        
        isCorrect = true;
        items.forEach((item, index) => {
            const origIndex = parseInt(item.dataset.originalIndex);
            if (origIndex !== index) {
                isCorrect = false;
            }
        });
        message = isCorrect ? "¡Correcto! El código está ordenado perfectamente." : "Incorrecto. El orden no es el correcto.";
    }
    else if (type === 'find-error') {
        const selected = card.querySelector('.error-line.selected');
        if (!selected) {
            showFeedback(feedback, false, "Por favor haz click en una línea.");
            return;
        }
        const selectedLine = selected.dataset.lineIndex;
        const dataDiv = card.querySelector('.quiz-answer-data');
        const correctLine = dataDiv.dataset.errorLine;
        const explanation = dataDiv.dataset.explanation || "";
        
        isCorrect = (selectedLine === correctLine);
        message = isCorrect ? "¡Correcto! " + explanation : "Incorrecto. El error no está en esta línea.";
    }

    showFeedback(feedback, isCorrect, message);

    if (isCorrect && window.trackProgress) {
        window.trackProgress(btn.dataset.lesson, exerciseId);
    }
}

function showAnswer(exerciseId, type) {
    const card = document.getElementById('exercise-' + exerciseId);
    if (!card) return;
    
    if (type === 'fill-blank') {
        const inputs = card.querySelectorAll('.exercise-input');
        inputs.forEach(input => {
            input.value = input.dataset.answer;
            input.classList.remove('input-incorrect');
            input.classList.add('input-correct');
        });
    }
    else if (type === 'multiple-choice') {
        const dataDiv = card.querySelector('.quiz-answer-data');
        const correctIndex = dataDiv.dataset.correct;
        const correctRadio = card.querySelector(`input[type="radio"][value="${correctIndex}"]`);
        if (correctRadio) {
            correctRadio.checked = true;
            card.querySelectorAll('.quiz-option-label').forEach(lbl => lbl.classList.remove('selected'));
            correctRadio.closest('.quiz-option-label').classList.add('selected');
        }
    }
    else if (type === 'reorder') {
        const list = card.querySelector('.reorder-list');
        const items = Array.from(list.querySelectorAll('.reorder-item'));
        items.sort((a, b) => parseInt(a.dataset.originalIndex) - parseInt(b.dataset.originalIndex));
        items.forEach(item => list.appendChild(item));
    }
    else if (type === 'find-error') {
        const dataDiv = card.querySelector('.quiz-answer-data');
        const correctLine = dataDiv.dataset.errorLine;
        const errorLineEl = card.querySelector(`.error-line[data-line-index="${correctLine}"]`);
        if (errorLineEl) {
            card.querySelectorAll('.error-line').forEach(l => l.classList.remove('selected'));
            errorLineEl.classList.add('selected');
        }
    }
    
    const feedback = card.querySelector('.exercise-feedback');
    showFeedback(feedback, true, "Respuesta mostrada.");
}

function showFeedback(element, isCorrect, message) {
    element.textContent = message;
    element.hidden = false;
    if (isCorrect) {
        element.classList.remove('feedback-incorrect');
        element.classList.add('feedback-correct');
    } else {
        element.classList.remove('feedback-correct');
        element.classList.add('feedback-incorrect');
    }
}
