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
    const cardExplanation = card.dataset.explanation || "";
    const cardHint = card.dataset.hint || "";

    if (type === 'fill-blank') {
        const inputs = card.querySelectorAll('.exercise-input');
        isCorrect = true;
        inputs.forEach(input => {
            const answer = input.dataset.answer ? input.dataset.answer.trim().toLowerCase().replace(/\s+/g, ' ') : '';
            const userVal = input.value ? input.value.trim().toLowerCase().replace(/\s+/g, ' ') : '';
            if (userVal === answer) {
                input.classList.remove('input-incorrect');
                input.classList.add('input-correct');
            } else {
                input.classList.remove('input-correct');
                input.classList.add('input-incorrect');
                isCorrect = false;
            }
        });
        if (isCorrect) {
            message = "¡Correcto! Excelente trabajo." + (cardExplanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${cardExplanation}</div>` : "");
            if (btn) btn.disabled = true;
        } else {
            const expText = cardExplanation || cardHint || "Revisa la sintaxis requerida y los campos resaltados en rojo.";
            message = `❌ <b>Hay errores en tu respuesta.</b><div class="exercise-explanation-box"><b>Orientación:</b> ${expText}</div>`;
        }
    } 
    else if (type === 'multiple-choice') {
        const selected = card.querySelector('input[type="radio"]:checked');
        if (!selected) {
            showFeedback(feedback, false, "Por favor selecciona una opción antes de comprobar.", card, exerciseId);
            return;
        }
        const dataDiv = card.querySelector('.quiz-answer-data');
        const correctIndex = dataDiv ? dataDiv.dataset.correct : "-1";
        const explanation = (dataDiv && dataDiv.dataset.explanation) ? dataDiv.dataset.explanation : cardExplanation;
        
        isCorrect = (selected.value === correctIndex);
        
        // Highlight options visually
        card.querySelectorAll('.quiz-option-label').forEach((label, i) => {
            label.classList.remove('option-correct', 'option-incorrect');
            if (i.toString() === correctIndex) {
                label.classList.add('option-correct');
            } else if (label.querySelector('input:checked') && !isCorrect) {
                label.classList.add('option-incorrect');
            }
        });

        if (isCorrect) {
            message = "¡Correcto! " + (explanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${explanation}</div>` : "");
            if (btn) btn.disabled = true;
        } else {
            message = "❌ <b>Opción incorrecta.</b> " + (explanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${explanation}</div>` : "Esa opción no es la adecuada según los conceptos vistos en la lección.");
        }
    }
    else if (type === 'reorder') {
        const items = card.querySelectorAll('.reorder-item');
        isCorrect = true;
        items.forEach((item, index) => {
            const origIndex = parseInt(item.dataset.originalIndex);
            if (origIndex !== index) {
                isCorrect = false;
            }
        });
        if (isCorrect) {
            message = "¡Correcto! El código está ordenado perfectamente." + (cardExplanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${cardExplanation}</div>` : "");
            if (btn) btn.disabled = true;
        } else {
            message = "❌ <b>El orden no es el correcto.</b> Recuerda el flujo lógico de ejecución de las instrucciones.";
        }
    }
    else if (type === 'find-error') {
        const selected = card.querySelector('.error-line.selected, .error-line.selected-line');
        if (!selected) {
            showFeedback(feedback, false, "Por favor haz click sobre la línea donde crees que está el error.", card, exerciseId);
            return;
        }
        const selectedLine = selected.dataset.lineIndex;
        const dataDiv = card.querySelector('.quiz-answer-data');
        const correctLine = dataDiv ? dataDiv.dataset.errorLine : "-1";
        const explanation = (dataDiv && dataDiv.dataset.explanation) ? dataDiv.dataset.explanation : cardExplanation;
        
        isCorrect = (selectedLine === correctLine);
        if (isCorrect) {
            message = "¡Correcto! " + (explanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${explanation}</div>` : "Has identificado la línea con el error.");
            if (btn) btn.disabled = true;
        } else {
            message = "❌ <b>Línea incorrecta.</b> El error sintáctico o lógico no se encuentra en esa línea.";
        }
    }

    showFeedback(feedback, isCorrect, message, card, exerciseId);

    if (isCorrect && window.trackProgress && btn && btn.dataset.lesson) {
        window.trackProgress(btn.dataset.lesson, exerciseId);
    }
    
    // Register attempt
    if (btn && btn.dataset.lesson) {
        fetch('/api/progreso/ejercicio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lesson_id: btn.dataset.lesson,
                exercise_id: exerciseId,
                passed: isCorrect
            })
        }).catch(() => {});
    }
}

function showAnswer(exerciseId, type) {
    const card = document.getElementById('exercise-' + exerciseId);
    if (!card) return;
    const cardExplanation = card.dataset.explanation || "";
    
    if (type === 'fill-blank') {
        const inputs = card.querySelectorAll('.exercise-input');
        inputs.forEach(input => {
            input.value = input.dataset.answer || '';
            input.classList.remove('input-incorrect');
            input.classList.add('input-correct');
        });
    }
    else if (type === 'multiple-choice') {
        const dataDiv = card.querySelector('.quiz-answer-data');
        const correctIndex = dataDiv ? dataDiv.dataset.correct : "-1";
        const correctRadio = card.querySelector(`input[type="radio"][value="${correctIndex}"]`);
        if (correctRadio) {
            correctRadio.checked = true;
            card.querySelectorAll('.quiz-option-label').forEach((lbl, i) => {
                lbl.classList.remove('selected', 'option-incorrect');
                if (i.toString() === correctIndex) {
                    lbl.classList.add('option-correct');
                }
            });
        }
    }
    else if (type === 'reorder') {
        const list = card.querySelector('.reorder-list');
        if (list) {
            const items = Array.from(list.querySelectorAll('.reorder-item'));
            items.sort((a, b) => parseInt(a.dataset.originalIndex) - parseInt(b.dataset.originalIndex));
            items.forEach(item => list.appendChild(item));
        }
    }
    else if (type === 'find-error') {
        const dataDiv = card.querySelector('.quiz-answer-data');
        const correctLine = dataDiv ? dataDiv.dataset.errorLine : "-1";
        const errorLineEl = card.querySelector(`.error-line[data-line-index="${correctLine}"]`);
        if (errorLineEl) {
            card.querySelectorAll('.error-line').forEach(l => l.classList.remove('selected', 'selected-line'));
            errorLineEl.classList.add('selected-line');
        }
    }
    
    const feedback = card.querySelector('.exercise-feedback');
    const msg = "<b>Respuesta mostrada.</b>" + (cardExplanation ? `<div class="exercise-explanation-box"><b>Explicación:</b> ${cardExplanation}</div>` : "");
    showFeedback(feedback, true, msg, card, exerciseId);
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

        // Add AI Tutor explanation button if available
        if (card && exerciseId && window.AITutor) {
            const questionEl = card.querySelector('.exercise-question');
            const questionText = questionEl ? questionEl.textContent.trim() : '';
            
            const helpWrap = document.createElement('div');
            helpWrap.style.marginTop = '0.5rem';
            
            const helpBtn = document.createElement('button');
            helpBtn.type = 'button';
            helpBtn.className = 'btn-ask-ai-error';
            helpBtn.innerHTML = '<span style="font-size:1rem;">🤖</span> <b>¿Por qué me equivoqué?</b> (Explicación con Tutor IA)';
            
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
                    ? `Mi respuesta fue: "${userAnswer.trim()}". ¿Por qué es incorrecta y qué concepto debo repasar?` 
                    : 'No entendí cómo resolver este ejercicio, ¿me das una pista conceptual?';
                window.AITutor.hint(exerciseId, questionText, promptDetail);
            });
            
            helpWrap.appendChild(helpBtn);
            element.appendChild(helpWrap);
        }
    }
}
