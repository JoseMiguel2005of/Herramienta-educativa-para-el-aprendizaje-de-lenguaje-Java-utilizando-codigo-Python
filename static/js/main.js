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

    const translateCode = async (isManual = false) => {
        const code = editor.value;
        const currentRequest = ++requestId;

        if (btnTranslate && isManual) {
            btnTranslate.disabled = true;
            btnTranslate.innerHTML = '<span>⚡ Transpilando...</span>';
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

            output.textContent = data.java || "// No se generó salida Java";
            renderMessages(data.errors || [], data.warnings || []);

            const panel = output.closest('.translator-panel');
            if (panel && isManual) {
                panel.classList.remove('transpile-glow');
                void panel.offsetWidth; // Trigger reflow
                panel.classList.add('transpile-glow');

                // Si está en pantalla pequeña, hacer scroll al resultado
                if (window.innerWidth < 800) {
                    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }

            if (btnTranslate && isManual) {
                btnTranslate.innerHTML = '<span>✅ ¡Traducido!</span>';
                setTimeout(() => {
                    btnTranslate.disabled = false;
                    btnTranslate.innerHTML = btnTranslate.dataset.originalLabel || '⚡ Transpilar a Java';
                }, 1400);
            }
        } catch (err) {
            if (currentRequest !== requestId) return;
            output.textContent = "// Error al procesar la traducción";
            renderMessages([err.message], []);
            if (btnTranslate && isManual) {
                btnTranslate.disabled = false;
                btnTranslate.innerHTML = btnTranslate.dataset.originalLabel || '⚡ Transpilar a Java';
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
        debounceTimer = setTimeout(() => translateCode(false), 400);
    };

    if (btnTranslate) {
        btnTranslate.dataset.originalLabel = btnTranslate.innerHTML.trim();
        btnTranslate.addEventListener("click", () => translateCode(true));
    }

    editor.addEventListener("input", scheduleTranslate);
    translateCode(false);
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
    // Handled by quizzes.js for full support of fill-blank, multiple-choice, reorder and find-error
}
