/**
 * Practice Runner
 * Handles code execution, test validation, hints, and solution display
 */
document.addEventListener('DOMContentLoaded', () => {
    if (!window.PRACTICE_DATA) return;

    const { problemId, starterCode, testCases, hints, solution } = window.PRACTICE_DATA;
    const editor = document.getElementById('practice-editor');
    const outputWrapper = document.getElementById('practice-output-wrapper');
    const outputEl = document.getElementById('practice-output');
    const testsWrapper = document.getElementById('practice-tests-wrapper');
    const testsList = document.getElementById('tests-list');
    const testsScore = document.getElementById('tests-score');
    const solutionSection = document.getElementById('solution-section');
    const solutionCode = document.getElementById('solution-code');
    const hintContent = document.getElementById('hint-content');

    let pyodideInstance = null;
    let hintsRevealed = 0;

    // Show solution section after first attempt
    let hasAttempted = false;

    async function getPyodide() {
        if (pyodideInstance) return pyodideInstance;
        try {
            pyodideInstance = await loadPyodide();
            return pyodideInstance;
        } catch (e) {
            console.error('Failed to load Pyodide:', e);
            return null;
        }
    }

    async function runCode(code) {
        const pyodide = await getPyodide();
        if (!pyodide) return { output: 'Error: No se pudo cargar el entorno de Python', error: true };

        try {
            pyodide.runPython(`
import sys, io
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()
`);
            pyodide.runPython(code);
            const stdout = pyodide.runPython('sys.stdout.getvalue()');
            const stderr = pyodide.runPython('sys.stderr.getvalue()');
            return { output: stdout + (stderr ? '\n' + stderr : ''), error: !!stderr };
        } catch (e) {
            return { output: 'Error: ' + e.message, error: true };
        }
    }

    // Run button
    document.getElementById('btn-run-code')?.addEventListener('click', async () => {
        outputWrapper.hidden = false;
        outputEl.textContent = '⏳ Ejecutando...';
        const result = await runCode(editor.value);
        outputEl.textContent = result.output || '(Sin salida)';
        outputEl.style.color = result.error ? '#ef5350' : '#e0e0e0';
    });

    // Submit button - run tests
    document.getElementById('btn-submit-code')?.addEventListener('click', async () => {
        outputWrapper.hidden = false;
        outputEl.textContent = '⏳ Ejecutando pruebas...';
        testsWrapper.hidden = false;
        testsList.innerHTML = '';

        const userCode = editor.value;
        let passed = 0;
        const total = testCases.length;

        for (const tc of testCases) {
            const fullCode = userCode + '\n\n__result__ = ' + tc.input;
            try {
                const pyodide = await getPyodide();
                pyodide.runPython(`
import sys, io
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()
`);
                pyodide.runPython(fullCode);
                const result = pyodide.runPython('repr(__result__)');
                const expected = tc.expected;
                const isPass = result === expected;

                if (isPass) passed++;

                const item = document.createElement('div');
                item.className = 'test-case-item ' + (isPass ? 'passed' : 'failed');
                item.innerHTML = `
                    <span class="test-icon">${isPass ? '✓' : '✗'}</span>
                    <span>${tc.input} → ${isPass ? expected : result + ' (esperado ' + expected + ')'}</span>
                `;
                testsList.appendChild(item);
            } catch (e) {
                const item = document.createElement('div');
                item.className = 'test-case-item failed';
                item.innerHTML = `
                    <span class="test-icon">✗</span>
                    <span>${tc.input} → Error: ${e.message}</span>
                `;
                testsList.appendChild(item);
            }
        }

        testsScore.textContent = `${passed}/${total} aprobadas`;
        testsScore.style.color = passed === total ? '#66bb6a' : '#ef5350';
        outputEl.textContent = passed === total
            ? 'Todas las pruebas aprobadas. Excelente trabajo.'
            : `${passed} de ${total} pruebas aprobadas. ¡Sigue intentando!`;
        outputEl.style.color = passed === total ? '#66bb6a' : '#ffc107';

        // Show solution section after first attempt
        if (!hasAttempted) {
            hasAttempted = true;
            solutionSection.hidden = false;
        }

        // Track progress if all passed
        if (passed === total) {
            fetch('/api/progreso/ejercicio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lesson_id: 'practice',
                    exercise_id: problemId,
                    passed: true
                })
            }).catch(() => {});
        }
    });

    // Reset button
    document.getElementById('btn-reset-code')?.addEventListener('click', () => {
        editor.value = starterCode;
        outputWrapper.hidden = true;
        testsWrapper.hidden = true;
    });

    // Hint buttons
    document.querySelectorAll('.btn-practice-hint').forEach(btn => {
        btn.addEventListener('click', () => {
            const idx = parseInt(btn.dataset.hintIndex);
            if (idx < hints.length) {
                hintContent.textContent = hints[idx];
                hintContent.hidden = false;
            }
        });
    });

    // Solution button
    document.getElementById('btn-show-solution')?.addEventListener('click', () => {
        solutionCode.hidden = !solutionCode.hidden;
    });
});
