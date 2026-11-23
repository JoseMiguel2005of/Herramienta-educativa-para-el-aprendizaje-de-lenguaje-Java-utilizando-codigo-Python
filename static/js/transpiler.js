/**
 * Visual Transpiler (AST Mapper)
 * Generates mapped tokens from basic Python to Java for visual hover tracking.
 */

document.addEventListener('DOMContentLoaded', () => {
    const inputArea = document.getElementById('python-input');
    const pyOutput = document.getElementById('python-ast-output');
    const javaOutput = document.getElementById('java-ast-output');
    const hoverReadout = document.getElementById('translator-hover-readout');
    const snippetSelect = document.getElementById('snippet-selector');
    const btnModeEdit = document.getElementById('btn-mode-edit');
    const btnModeInspect = document.getElementById('btn-mode-inspect');

    if (!inputArea || !pyOutput || !javaOutput) return;

    let tokenCounter = 0;
    let lastJavaCode = '';
    let tokenPyMap = new Map();

    function generateTokenId() {
        return `tk-${tokenCounter++}`;
    }

    function createTokenHtml(text, type, id) {
        return `<span class="token-span token-${type}" data-tkid="${id}">${escapeHtml(text)}</span>`;
    }

    function escapeHtml(unsafe) {
        return String(unsafe)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function setLeftMode(mode) {
        const inspect = mode === 'inspect';
        inputArea.hidden = inspect;
        pyOutput.hidden = !inspect;
        if (btnModeEdit) btnModeEdit.setAttribute('aria-pressed', inspect ? 'false' : 'true');
        if (btnModeInspect) btnModeInspect.setAttribute('aria-pressed', inspect ? 'true' : 'false');
    }

    if (btnModeEdit) btnModeEdit.addEventListener('click', () => setLeftMode('edit'));
    if (btnModeInspect) btnModeInspect.addEventListener('click', () => setLeftMode('inspect'));

    function transpile() {
        const code = inputArea.value;
        const lines = code.split('\n');

        let pyHtml = '';
        let javaHtml = '';
        let javaPlain = '';
        tokenCounter = 0;
        tokenPyMap = new Map();

        let indentLevel = 0;

        // Java boilerplate start
        const classId = generateTokenId();
        const mainId = generateTokenId();
        tokenPyMap.set(classId, 'Estructura base de clase (requerida en Java)');
        tokenPyMap.set(mainId, 'Punto de entrada principal (implícito en Python)');

        javaHtml += `${createTokenHtml('public class', 'keyword', classId)} ${createTokenHtml('Programa', 'variable', classId)} {\n`;
        javaHtml += `    ${createTokenHtml('public static void', 'keyword', mainId)} ${createTokenHtml('main(String[] args)', 'variable', mainId)} {\n`;
        javaPlain += 'public class Programa {\n';
        javaPlain += '    public static void main(String[] args) {\n';

        let pyLineCount = 0;
        let javaLineCount = 2;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const trimmed = line.trim();

            let currentIndent = line.search(/\S/);
            if (currentIndent === -1) currentIndent = 0;

            if (currentIndent < indentLevel && trimmed !== '') {
                javaHtml += '        }\n';
                javaPlain += '        }\n';
                javaLineCount++;
                indentLevel = currentIndent;
            }

            if (trimmed === '') {
                pyHtml += '\n';
                javaHtml += '\n';
                javaPlain += '\n';
                continue;
            }

            pyLineCount++;

            if (trimmed.startsWith('#')) {
                const id = generateTokenId();
                tokenPyMap.set(id, trimmed);
                pyHtml += `${createTokenHtml(line, 'comment', id)}\n`;
                javaHtml += `        ${createTokenHtml('//' + trimmed.substring(1), 'comment', id)}\n`;
                javaPlain += `        //${trimmed.substring(1)}\n`;
                javaLineCount++;
                continue;
            }

            // 1. print("...")
            let match = trimmed.match(/^print\((.*)\)$/);
            if (match) {
                const id = generateTokenId();
                const inner = match[1];
                tokenPyMap.set(id, trimmed);

                pyHtml += `${line.substring(0, currentIndent)}`;
                pyHtml += `${createTokenHtml('print', 'keyword', id)}(${createTokenHtml(inner, 'string', id)})\n`;

                javaHtml += `        ${createTokenHtml('System.out.println', 'keyword', id)}(${createTokenHtml(inner, 'string', id)});\n`;
                javaPlain += `        System.out.println(${inner});\n`;
                javaLineCount++;
                continue;
            }

            // 2. Variable assignment: var = value
            match = trimmed.match(/^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.*)$/);
            if (match) {
                const id = generateTokenId();
                const vName = match[1];
                const vVal = match[2];
                tokenPyMap.set(id, trimmed);

                pyHtml += `${line.substring(0, currentIndent)}`;
                pyHtml += `${createTokenHtml(vName, 'variable', id)} = ${createTokenHtml(vVal, vVal.includes('"') || vVal.includes("'") ? 'string' : 'number', id)}\n`;

                let type = 'var';
                if (vVal.includes('"') || vVal.includes("'")) type = 'String';
                else if (vVal === 'True' || vVal === 'False') type = 'boolean';
                else if (!isNaN(vVal)) type = 'int';

                let jVal = vVal;
                if (jVal === 'True') jVal = 'true';
                if (jVal === 'False') jVal = 'false';

                javaHtml += `        ${createTokenHtml(type, 'keyword', id)} ${createTokenHtml(vName, 'variable', id)} = ${createTokenHtml(jVal, jVal.includes('"') || jVal.includes("'") ? 'string' : 'number', id)};\n`;
                javaPlain += `        ${type} ${vName} = ${jVal};\n`;
                javaLineCount++;
                continue;
            }

            // 3. if condition:
            match = trimmed.match(/^if\s+(.*):$/);
            if (match) {
                const id = generateTokenId();
                const cond = match[1];
                tokenPyMap.set(id, trimmed);

                pyHtml += `${line.substring(0, currentIndent)}`;
                pyHtml += `${createTokenHtml('if', 'keyword', id)} ${createTokenHtml(cond, 'variable', id)}:\n`;

                let jCond = cond;
                if (jCond === 'True') jCond = 'true';
                if (jCond === 'False') jCond = 'false';

                javaHtml += `        ${createTokenHtml('if', 'keyword', id)} (${createTokenHtml(jCond, 'variable', id)}) {\n`;
                javaPlain += `        if (${jCond}) {\n`;
                javaLineCount++;
                indentLevel = currentIndent + 4;
                continue;
            }

            // 4. for i in range(x):
            match = trimmed.match(/^for\s+([a-zA-Z_]+)\s+in\s+range\((.*)\):$/);
            if (match) {
                const id = generateTokenId();
                const v = match[1];
                const range = match[2];
                tokenPyMap.set(id, trimmed);

                pyHtml += `${line.substring(0, currentIndent)}`;
                pyHtml += `${createTokenHtml('for ' + v + ' in range', 'keyword', id)}(${createTokenHtml(range, 'number', id)}):\n`;

                javaHtml += `        ${createTokenHtml('for', 'keyword', id)} (int ${createTokenHtml(v, 'variable', id)} = 0; ${v} < ${createTokenHtml(range, 'number', id)}; ${v}++) {\n`;
                javaPlain += `        for (int ${v} = 0; ${v} < ${range}; ${v}++) {\n`;
                javaLineCount++;
                indentLevel = currentIndent + 4;
                continue;
            }

            // Unhandled lines
            const id = generateTokenId();
            tokenPyMap.set(id, trimmed);
            pyHtml += `${createTokenHtml(line, 'punctuation', id)}\n`;
            javaHtml += `        // ${createTokenHtml('Sin traducción directa', 'comment', id)}\n`;
            javaPlain += '        // Sin traducción directa\n';
            javaLineCount++;
        }

        // Close pending blocks
        while (indentLevel > 0) {
            javaHtml += '        }\n';
            javaPlain += '        }\n';
            javaLineCount++;
            indentLevel -= 4;
        }

        // Java boilerplate end
        javaHtml += '    }\n';
        javaHtml += '}\n';
        javaPlain += '    }\n';
        javaPlain += '}\n';
        javaLineCount += 2;

        pyOutput.innerHTML = pyHtml;
        javaOutput.innerHTML = javaHtml;

        lastJavaCode = javaPlain;
        updateMetrics(pyLineCount, javaLineCount);
        attachHoverEvents();
    }

    function attachHoverEvents() {
        const spans = document.querySelectorAll('.token-span');
        spans.forEach(span => {
            span.addEventListener('mouseenter', (e) => {
                const tkid = e.target.getAttribute('data-tkid');
                if (!tkid) return;
                document.querySelectorAll(`.token-span[data-tkid="${tkid}"]`).forEach(el => {
                    el.classList.add('hovered');
                });
                if (hoverReadout && tokenPyMap.has(tkid)) {
                    hoverReadout.innerHTML = `<strong>Equivalente en Python:</strong> ${escapeHtml(tokenPyMap.get(tkid))}`;
                }
            });
            span.addEventListener('mouseleave', (e) => {
                const tkid = e.target.getAttribute('data-tkid');
                if (!tkid) return;
                document.querySelectorAll(`.token-span[data-tkid="${tkid}"]`).forEach(el => {
                    el.classList.remove('hovered');
                });
                if (hoverReadout) {
                    hoverReadout.textContent = 'Pasa el cursor sobre una línea de Java para ver su equivalente en Python.';
                }
            });
        });
    }

    function updateMetrics(pyLines, javaLines) {
        const metricsEl = document.getElementById('transpiler-metrics');
        if (!metricsEl) return;

        const ratio = pyLines > 0 ? (javaLines / pyLines).toFixed(1) : '—';

        metricsEl.innerHTML = `
            <div class="metric-item">
                <span class="metric-label">Python</span>
                <span class="metric-num metric-num--python">${pyLines}</span>
                <span class="metric-unit">líneas</span>
            </div>
            <span class="metric-arrow" aria-hidden="true">→</span>
            <div class="metric-item">
                <span class="metric-label">Java</span>
                <span class="metric-num metric-num--java">${javaLines}</span>
                <span class="metric-unit">líneas</span>
            </div>
            <div class="metric-item metric-ratio" title="Proporción informativa de líneas entre Java y Python">
                <span class="metric-label">Relación</span>
                <span class="metric-num metric-num--ratio">${ratio}×</span>
            </div>
        `;
    }

    window.downloadJavaFile = function () {
        if (!lastJavaCode) return;
        const blob = new Blob([lastJavaCode], { type: 'text/x-java' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Programa.java';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showExportFeedback('✓ Archivo Programa.java descargado');
    };

    window.copyJavaCode = function () {
        if (!lastJavaCode) return;
        navigator.clipboard.writeText(lastJavaCode).then(() => {
            showExportFeedback('✓ Código Java copiado al portapapeles');
        }).catch(() => {
            const ta = document.createElement('textarea');
            ta.value = lastJavaCode;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            showExportFeedback('✓ Código Java copiado al portapapeles');
        });
    };

    function showExportFeedback(message) {
        let feedback = document.getElementById('export-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.id = 'export-feedback';
            feedback.className = 'translator-toast';
            feedback.setAttribute('role', 'status');
            feedback.setAttribute('aria-live', 'polite');
            document.body.appendChild(feedback);
        }
        feedback.textContent = message;
        feedback.classList.add('is-visible');
        clearTimeout(feedback._hideTimer);
        feedback._hideTimer = setTimeout(() => {
            feedback.classList.remove('is-visible');
        }, 2200);
    }

    window.loadSnippet = function (snippetKey) {
        const snippet = SNIPPETS[snippetKey];
        if (!snippet || !inputArea) return;
        inputArea.value = snippet;
        if (snippetSelect) snippetSelect.value = snippetKey;
        document.querySelectorAll('.snippet-btn').forEach(btn => {
            btn.setAttribute('aria-pressed', btn.dataset.snippet === snippetKey ? 'true' : 'false');
        });
        transpile();
    };

    if (snippetSelect) {
        snippetSelect.addEventListener('change', () => {
            if (snippetSelect.value) {
                window.loadSnippet(snippetSelect.value);
            }
        });
    }

    inputArea.addEventListener('input', transpile);
    transpile();
});

const SNIPPETS = {
    'hello_world': `# Hola Mundo
print("¡Hola, mundo!")`,

    'variables': `# Variables y tipos
nombre = "Carlos"
edad = 25
es_estudiante = True
print("Nombre: " + nombre)`,

    'conditionals': `# Condicionales
edad = 18
if edad >= 18:
    print("Eres mayor de edad")`,

    'for_loop': `# Bucle For
for i in range(5):
    print(i)`,

    'fibonacci': `# Serie Fibonacci
a = 0
b = 1
for i in range(10):
    print(a)
    temp = a
    a = b
    b = temp + b`,

    'calculator': `# Calculadora simple
num1 = 10
num2 = 5
suma = num1 + num2
resta = num1 - num2
print(suma)
print(resta)`,

    'bubble_sort': `# Bucle anidado
for i in range(5):
    for j in range(4):
        print(j)`,

    'class_animal': `# Datos de mascota
nombre = "Firulais"
tipo = "Perro"
edad = 3
print(nombre)
print(tipo)`
};
