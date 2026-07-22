document.addEventListener("DOMContentLoaded", () => {
    initCopyButtons();
    initEditorTabSupport();
    initTranslator();
    initCodeHover();
    initExercises();
});

function initCopyButtons() {
    document.querySelectorAll(".btn-copy").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const targetId = btn.dataset.target;
            const codeEl = document.getElementById(targetId);
            if (!codeEl) return;

            const text = codeEl.textContent;
            const originalLabel = btn.textContent;
            const copiedLabel = btn.dataset.copied || "Copied!";

            try {
                await navigator.clipboard.writeText(text);
                btn.textContent = copiedLabel;
                btn.classList.add("copied");
                setTimeout(() => {
                    btn.textContent = originalLabel;
                    btn.classList.remove("copied");
                }, 1500);
            } catch {
                const textarea = document.createElement("textarea");
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand("copy");
                document.body.removeChild(textarea);
                btn.textContent = copiedLabel;
                setTimeout(() => {
                    btn.textContent = originalLabel;
                }, 1500);
            }
        });
    });
}

function initEditorTabSupport() {
    const editor = document.getElementById("practice-editor");
    if (!editor) return;

    editor.addEventListener("keydown", (e) => {
        if (e.key === "Tab") {
            e.preventDefault();
            const start = editor.selectionStart;
            const end = editor.selectionEnd;
            const value = editor.value;
            editor.value = value.substring(0, start) + "    " + value.substring(end);
            editor.selectionStart = editor.selectionEnd = start + 4;
        }
    });
}

function initTranslator() {
    const editor = document.getElementById("practice-editor");
    const output = document.getElementById("translated-java");
    const btnTranslate = document.getElementById("btn-translate");
    const messagesBox = document.getElementById("translation-messages");
    const errorsBox = document.getElementById("translation-errors");
    const warningsBox = document.getElementById("translation-warnings");
    const errorList = document.getElementById("error-list");
    const warningList = document.getElementById("warning-list");

    if (!editor || !output) return;

    let debounceTimer = null;
    let requestId = 0;

    const translateCode = async () => {
        const code = editor.value;
        const currentRequest = ++requestId;

        if (btnTranslate) {
            btnTranslate.disabled = true;
            btnTranslate.textContent =
                (window.TRANSLATOR_LABELS && window.TRANSLATOR_LABELS.translating) || "Translating...";
        }

        try {
            const payload = {
                code: code,
                lesson_id: window.currentLessonId || "unknown"
            };

            const response = await fetch("/api/traducir", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            if (currentRequest !== requestId) return;

            output.textContent = data.java || "";
            renderMessages(data.errors || [], data.warnings || []);
        } catch (err) {
            if (currentRequest !== requestId) return;
            output.textContent = "";
            renderMessages([err.message], []);
        } finally {
            if (btnTranslate) {
                btnTranslate.disabled = false;
                btnTranslate.textContent =
                    btnTranslate.dataset.originalLabel || btnTranslate.textContent;
            }
        }
    };

    const renderMessages = (errors, warnings) => {
        if (!messagesBox) return;

        errorList.innerHTML = "";
        warningList.innerHTML = "";

        errors.forEach((msg) => {
            const li = document.createElement("li");
            li.textContent = msg;
            errorList.appendChild(li);
        });

        warnings.forEach((msg) => {
            const li = document.createElement("li");
            li.textContent = msg;
            warningList.appendChild(li);
        });

        errorsBox.hidden = errors.length === 0;
        warningsBox.hidden = warnings.length === 0;
        messagesBox.hidden = errors.length === 0 && warnings.length === 0;
    };

    const scheduleTranslate = () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(translateCode, 450);
    };

    if (btnTranslate) {
        btnTranslate.dataset.originalLabel = btnTranslate.textContent;
        btnTranslate.addEventListener("click", translateCode);
    }

    editor.addEventListener("input", scheduleTranslate);
    translateCode();
}

function initCodeHover() {
    const lines = document.querySelectorAll('.interactive-line');
    const hoverExplanation = document.getElementById('hover-explanation');
    const defaultExplanation = document.getElementById('default-explanation');

    if (lines.length === 0 || !hoverExplanation || !defaultExplanation) return;

    lines.forEach(line => {
        line.addEventListener('mouseenter', () => {
            const mappingId = line.getAttribute('data-mapping-id');
            const explanationText = line.getAttribute('data-explanation');
            
            // Highlight matching lines
            document.querySelectorAll(`.interactive-line[data-mapping-id="${mappingId}"]`).forEach(el => {
                el.classList.add('active');
            });
            
            // Show explanation
            if (explanationText) {
                defaultExplanation.style.display = 'none';
                hoverExplanation.textContent = explanationText;
                hoverExplanation.style.display = 'block';
            }
        });

        line.addEventListener('mouseleave', () => {
            const mappingId = line.getAttribute('data-mapping-id');
            
            // Remove highlight
            document.querySelectorAll(`.interactive-line[data-mapping-id="${mappingId}"]`).forEach(el => {
                el.classList.remove('active');
            });
            
            // Restore default explanation
            hoverExplanation.style.display = 'none';
            defaultExplanation.style.display = 'block';
        });
    });
}

function initExercises() {
    // Comprobar respuesta
    document.querySelectorAll('.btn-check-quiz').forEach(btn => {
        btn.addEventListener('click', () => {
            const exerciseId = btn.getAttribute('data-exercise-id');
            const lessonId = btn.getAttribute('data-lesson');
            const exType = btn.getAttribute('data-type');
            const card = document.getElementById('exercise-' + exerciseId);
            const feedbackEl = document.getElementById('feedback-' + exerciseId);
            if (!card || !feedbackEl) return;

            let allCorrect = false;
            let explanation = '';

            if (exType === 'multiple-choice') {
                // --- Multiple choice: check radio selection ---
                const answerData = card.querySelector('.quiz-answer-data');
                const correctIndex = answerData ? parseInt(answerData.getAttribute('data-correct')) : -1;
                explanation = answerData ? answerData.getAttribute('data-explanation') || '' : '';

                const selected = card.querySelector('input[type="radio"]:checked');
                if (!selected) {
                    feedbackEl.hidden = false;
                    feedbackEl.className = 'exercise-feedback feedback-incorrect';
                    feedbackEl.textContent = 'Por favor selecciona una opción antes de enviar.';
                    return;
                }

                const selectedIndex = parseInt(selected.value);
                allCorrect = (selectedIndex === correctIndex);

                // Highlight options
                card.querySelectorAll('.quiz-option-label').forEach((label, i) => {
                    label.classList.remove('option-correct', 'option-incorrect');
                    if (i === correctIndex) {
                        label.classList.add('option-correct');
                    } else if (i === selectedIndex && !allCorrect) {
                        label.classList.add('option-incorrect');
                    }
                    // Disable all radios
                    const radio = label.querySelector('input[type="radio"]');
                    if (radio) radio.disabled = true;
                });

            } else if (exType === 'fill-blank' || !exType) {
                // --- Fill in the blank: check text inputs ---
                const inputs = card.querySelectorAll('.exercise-input');
                allCorrect = true;
                inputs.forEach(input => {
                    const userAnswer = input.value.trim().toLowerCase().replace(/\s+/g, ' ');
                    const correctAnswer = input.getAttribute('data-answer').trim().toLowerCase().replace(/\s+/g, ' ');
                    if (userAnswer === correctAnswer) {
                        input.classList.remove('input-incorrect');
                        input.classList.add('input-correct');
                    } else {
                        input.classList.remove('input-correct');
                        input.classList.add('input-incorrect');
                        allCorrect = false;
                    }
                });

            } else if (exType === 'find-error') {
                // --- Find the error line ---
                const answerData = card.querySelector('.quiz-answer-data');
                const correctLine = answerData ? parseInt(answerData.getAttribute('data-error-line')) : -1;
                explanation = answerData ? answerData.getAttribute('data-explanation') || '' : '';

                const selectedLine = card.querySelector('.error-line.selected-line');
                if (!selectedLine) {
                    feedbackEl.hidden = false;
                    feedbackEl.className = 'exercise-feedback feedback-incorrect';
                    feedbackEl.textContent = 'Haz click en la línea que crees que tiene el error.';
                    return;
                }
                const selectedIndex = parseInt(selectedLine.getAttribute('data-line-index'));
                allCorrect = (selectedIndex === correctLine);

                card.querySelectorAll('.error-line').forEach(line => {
                    const idx = parseInt(line.getAttribute('data-line-index'));
                    if (idx === correctLine) line.classList.add('line-correct');
                    else if (idx === selectedIndex && !allCorrect) line.classList.add('line-incorrect');
                });

            } else if (exType === 'reorder') {
                // --- Reorder: check order of items ---
                const answerData = card.querySelector('.quiz-answer-data');
                const correctCount = answerData ? parseInt(answerData.getAttribute('data-correct-count')) : 0;
                const items = card.querySelectorAll('.reorder-item');
                let correctPositions = 0;
                items.forEach((item, i) => {
                    if (parseInt(item.getAttribute('data-original-index')) === i) correctPositions++;
                });
                allCorrect = (correctPositions === correctCount && correctCount > 0);
            }

            // Mostrar feedback visual
            feedbackEl.hidden = false;
            card.classList.remove('correct', 'incorrect');

            if (allCorrect) {
                card.classList.add('correct');
                feedbackEl.className = 'exercise-feedback feedback-correct';
                feedbackEl.textContent = '✅ Correcto. Excelente trabajo.' + (explanation ? ' ' + explanation : '');
                btn.disabled = true;
            } else {
                card.classList.add('incorrect');
                feedbackEl.className = 'exercise-feedback feedback-incorrect';
                if (exType === 'multiple-choice' || exType === 'find-error') {
                    feedbackEl.textContent = '❌ Respuesta incorrecta.' + (explanation ? ' ' + explanation : ' Inténtalo de nuevo.');
                } else {
                    feedbackEl.textContent = '❌ Respuesta incorrecta. Revisa los campos marcados en rojo e inténtalo de nuevo.';
                }
            }

            // Registrar intento en analíticas (silenciosamente)
            fetch('/api/progreso/ejercicio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lesson_id: lessonId,
                    passed: allCorrect
                })
            }).catch(() => {});  // no bloqueamos si falla
        });
    });

    // Click en líneas de find-error para seleccionarlas
    document.querySelectorAll('.error-line').forEach(line => {
        line.addEventListener('click', () => {
            const card = line.closest('.exercise-card');
            if (!card) return;
            card.querySelectorAll('.error-line').forEach(l => l.classList.remove('selected-line'));
            line.classList.add('selected-line');
        });
    });

    // Mostrar respuesta
    document.querySelectorAll('.btn-show-answer-quiz').forEach(btn => {
        btn.addEventListener('click', () => {
            const exerciseId = btn.getAttribute('data-exercise-id');
            const exType = btn.getAttribute('data-type');
            const card = document.getElementById('exercise-' + exerciseId);
            const feedbackEl = document.getElementById('feedback-' + exerciseId);
            if (!card) return;

            if (exType === 'multiple-choice') {
                const answerData = card.querySelector('.quiz-answer-data');
                const correctIndex = answerData ? parseInt(answerData.getAttribute('data-correct')) : -1;
                const explanation = answerData ? answerData.getAttribute('data-explanation') || '' : '';

                card.querySelectorAll('.quiz-option-label').forEach((label, i) => {
                    label.classList.remove('option-correct', 'option-incorrect');
                    if (i === correctIndex) label.classList.add('option-correct');
                    const radio = label.querySelector('input[type="radio"]');
                    if (radio) {
                        radio.disabled = true;
                        if (i === correctIndex) radio.checked = true;
                    }
                });

                if (feedbackEl) {
                    feedbackEl.hidden = false;
                    feedbackEl.className = 'exercise-feedback feedback-correct';
                    feedbackEl.textContent = '✅ Respuesta mostrada.' + (explanation ? ' ' + explanation : '');
                }

            } else {
                // Fill-blank: show answers in inputs
                const inputs = card.querySelectorAll('.exercise-input');
                inputs.forEach(input => {
                    const correctAnswer = input.getAttribute('data-answer');
                    input.value = correctAnswer;
                    input.classList.remove('input-incorrect');
                    input.classList.add('input-correct');
                });

                const checkBtn = card.querySelector('.btn-check-quiz');
                if (checkBtn) checkBtn.click();
            }
        });
    });
}
