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
    document.querySelectorAll('.btn-check').forEach(btn => {
        btn.addEventListener('click', () => {
            const exerciseId = btn.getAttribute('data-exercise-id');
            const lessonId = btn.getAttribute('data-lesson');
            const card = document.getElementById('exercise-' + exerciseId);
            const feedbackEl = document.getElementById('feedback-' + exerciseId);
            if (!card || !feedbackEl) return;

            const inputs = card.querySelectorAll('.exercise-input');
            let allCorrect = true;

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

            // Mostrar feedback visual
            feedbackEl.hidden = false;
            card.classList.remove('correct', 'incorrect');

            if (allCorrect) {
                card.classList.add('correct');
                feedbackEl.className = 'exercise-feedback feedback-correct';
                feedbackEl.textContent = 'Correcto. Excelente trabajo.';
                btn.disabled = true;
            } else {
                card.classList.add('incorrect');
                feedbackEl.className = 'exercise-feedback feedback-incorrect';
                feedbackEl.textContent = 'Respuesta incorrecta. Revisa los campos marcados en rojo e intentalo de nuevo.';
            }

            // Registrar intento en analíticas (silenciosamente)
            fetch('/api/ejercicio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lesson_id: lessonId,
                    passed: allCorrect
                })
            }).catch(() => {});  // no bloqueamos si falla
        });
    });

    // Mostrar respuesta
    document.querySelectorAll('.btn-show-answer').forEach(btn => {
        btn.addEventListener('click', () => {
            const exerciseId = btn.getAttribute('data-exercise-id');
            const card = document.getElementById('exercise-' + exerciseId);
            if (!card) return;

            const inputs = card.querySelectorAll('.exercise-input');
            inputs.forEach(input => {
                const correctAnswer = input.getAttribute('data-answer');
                input.value = correctAnswer;
                input.classList.remove('input-incorrect');
                input.classList.add('input-correct');
            });
            
            // Trigger check manually to show success message
            const checkBtn = card.querySelector('.btn-check');
            if (checkBtn) {
                checkBtn.click();
            }
        });
    });
}
