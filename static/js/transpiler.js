/**
 * Visual Transpiler (AST Mapper)
 * Generates mapped tokens from basic Python to Java for visual hover tracking.
 * Sprint 1: Added snippets (3.6), export (3.7), and complexity metrics (3.8)
 */

document.addEventListener('DOMContentLoaded', () => {
    const inputArea = document.getElementById('python-input');
    const pyOutput = document.getElementById('python-ast-output');
    const javaOutput = document.getElementById('java-ast-output');

    let tokenCounter = 0;
    let lastJavaCode = '';  // For export (3.7)
    let lastPyLineCount = 0;  // For metrics (3.8)
    let lastJavaLineCount = 0;

    function generateTokenId() {
        return `tk-${tokenCounter++}`;
    }

    function createTokenHtml(text, type, id) {
        return `<span class="token-span token-${type}" data-tkid="${id}">${escapeHtml(text)}</span>`;
    }

    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    function transpile() {
        const code = inputArea.value;
        const lines = code.split('\n');

        let pyHtml = '';
        let javaHtml = '';
        let javaPlain = '';  // Plain text for export (3.7)
        tokenCounter = 0;

        let indentLevel = 0;

        // Java boilerplate start
        const classId = generateTokenId();
        const mainId = generateTokenId();

        javaHtml += `${createTokenHtml("public class", "keyword", classId)} ${createTokenHtml("Programa", "variable", classId)} {\n`;
        javaHtml += `    ${createTokenHtml("public static void", "keyword", mainId)} ${createTokenHtml("main(String[] args)", "variable", mainId)} {\n`;
        javaPlain += `public class Programa {\n`;
        javaPlain += `    public static void main(String[] args) {\n`;

        let pyLineCount = 0;
        let javaLineCount = 2;  // class + main
        let importsNeeded = new Set();

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i];
            let trimmed = line.trim();

            // Detect indentation to close Java blocks (very naive logic for demo)
            let currentIndent = line.search(/\S/);
            if (currentIndent === -1) currentIndent = 0;

            if (currentIndent < indentLevel && trimmed !== '') {
                // Close Java blocks
                javaHtml += `        }\n`;
                javaPlain += `        }\n`;
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
                pyHtml += `${createTokenHtml(line, "comment", id)}\n`;
                javaHtml += `        ${createTokenHtml("//" + trimmed.substring(1), "comment", id)}\n`;
                javaPlain += `        //${trimmed.substring(1)}\n`;
                javaLineCount++;
                continue;
            }

            // 1. print("...")
            let match = trimmed.match(/^print\((.*)\)$/);
            if (match) {
                const id = generateTokenId();
                const inner = match[1];

                // Indentation
                pyHtml += `${line.substring(0, currentIndent)}`;
                pyHtml += `${createTokenHtml("print", "keyword", id)}(${createTokenHtml(inner, "string", id)})\n`;

                javaHtml += `        ${createTokenHtml("System.out.println", "keyword", id)}(${createTokenHtml(inner, "string", id)});\n`;
                javaPlain += `        System.out.println(${inner});\n`;
                javaLineCount++;
                continue;
            }

            // 2. Variable assignment: var = "value"
            match = trimmed.match(/^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.*)$/);
            if (match) {
                const id = generateTokenId();
                const vName = match[1];
                const vVal = match[2];

                pyHtml += `${line.substring(0, currentIndent)}`;
                pyHtml += `${createTokenHtml(vName, "variable", id)} = ${createTokenHtml(vVal, vVal.includes('"') ? "string" : "number", id)}\n`;

                // Naive type inference
                let type = "var"; // Java 10+ var
                if (vVal.includes('"') || vVal.includes("'")) type = "String";
                else if (vVal === "True" || vVal === "False") type = "boolean";
                else if (!isNaN(vVal)) type = "int";

                let jVal = vVal;
                if (jVal === "True") jVal = "true";
                if (jVal === "False") jVal = "false";

                javaHtml += `        ${createTokenHtml(type, "keyword", id)} ${createTokenHtml(vName, "variable", id)} = ${createTokenHtml(jVal, jVal.includes('"') ? "string" : "number", id)};\n`;
                javaPlain += `        ${type} ${vName} = ${jVal};\n`;
                javaLineCount++;
                continue;
            }

            // 3. if condition:
            match = trimmed.match(/^if\s+(.*):$/);
            if (match) {
                const id = generateTokenId();
                const cond = match[1];

                pyHtml += `${line.substring(0, currentIndent)}`;
                pyHtml += `${createTokenHtml("if", "keyword", id)} ${createTokenHtml(cond, "variable", id)}:\n`;

                let jCond = cond;
                if (jCond === "True") jCond = "true";
                if (jCond === "False") jCond = "false";

                javaHtml += `        ${createTokenHtml("if", "keyword", id)} (${createTokenHtml(jCond, "variable", id)}) {\n`;
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

                pyHtml += `${line.substring(0, currentIndent)}`;
                pyHtml += `${createTokenHtml("for " + v + " in range", "keyword", id)}(${createTokenHtml(range, "number", id)}):\n`;

                javaHtml += `        ${createTokenHtml("for", "keyword", id)} (int ${createTokenHtml(v, "variable", id)} = 0; ${v} < ${createTokenHtml(range, "number", id)}; ${v}++) {\n`;
                javaPlain += `        for (int ${v} = 0; ${v} < ${range}; ${v}++) {\n`;
                javaLineCount++;
                indentLevel = currentIndent + 4;
                continue;
            }

            // Unhandled lines
            const id = generateTokenId();
            pyHtml += `${createTokenHtml(line, "punctuation", id)}\n`;
            javaHtml += `        // ${createTokenHtml("Sin traducción directa", "comment", id)}\n`;
            javaPlain += `        // Sin traducción directa\n`;
            javaLineCount++;
        }

        // Close pending blocks
        while(indentLevel > 0) {
            javaHtml += `        }\n`;
            javaPlain += `        }\n`;
            javaLineCount++;
            indentLevel -= 4;
        }

        // Java boilerplate end
        javaHtml += `    }\n`;
        javaHtml += `}\n`;
        javaPlain += `    }\n`;
        javaPlain += `}\n`;
        javaLineCount += 2;

        pyOutput.innerHTML = pyHtml;
        javaOutput.innerHTML = javaHtml;

        // Store for export (3.7)
        lastJavaCode = javaPlain;
        lastPyLineCount = pyLineCount;
        lastJavaLineCount = javaLineCount;

        // Update metrics (3.8)
        updateMetrics(pyLineCount, javaLineCount, importsNeeded.size);

        attachHoverEvents();
    }

    function attachHoverEvents() {
        const spans = document.querySelectorAll('.token-span');
        spans.forEach(span => {
            span.addEventListener('mouseenter', (e) => {
                const tkid = e.target.getAttribute('data-tkid');
                if(!tkid) return;
                document.querySelectorAll(`.token-span[data-tkid="${tkid}"]`).forEach(el => {
                    el.classList.add('hovered');
                });
            });
            span.addEventListener('mouseleave', (e) => {
                const tkid = e.target.getAttribute('data-tkid');
                if(!tkid) return;
                document.querySelectorAll(`.token-span[data-tkid="${tkid}"]`).forEach(el => {
                    el.classList.remove('hovered');
                });
            });
        });
    }

    // ===== COMPLEXITY METRICS (3.8) =====
    function updateMetrics(pyLines, javaLines, imports) {
        let metricsEl = document.getElementById('transpiler-metrics');
        if (!metricsEl) return;

        const ratio = pyLines > 0 ? (javaLines / pyLines).toFixed(1) : '—';
        const ratioColor = javaLines > pyLines ? '#ff5555' : '#51cf66';

        metricsEl.innerHTML = `
            <div class="metric-item">
                <span class="metric-label">PYTHON</span>
                <span class="metric-num" style="color: var(--python-color);">${pyLines}</span>
                <span class="metric-unit">líneas</span>
            </div>
            <div class="metric-arrow">→</div>
            <div class="metric-item">
                <span class="metric-label">JAVA</span>
                <span class="metric-num" style="color: var(--java-color);">${javaLines}</span>
                <span class="metric-unit">líneas</span>
            </div>
            <div class="metric-item metric-ratio">
                <span class="metric-label">RATIO</span>
                <span class="metric-num" style="color: ${ratioColor};">${ratio}x</span>
            </div>
        `;
    }

    // ===== EXPORT FUNCTIONS (3.7) =====
    window.downloadJavaFile = function() {
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

        // Feedback
        showExportFeedback('Archivo descargado');
    };

    window.copyJavaCode = function() {
        if (!lastJavaCode) return;
        navigator.clipboard.writeText(lastJavaCode).then(() => {
            showExportFeedback('Copiado al portapapeles');
        }).catch(() => {
            // Fallback for older browsers
            const ta = document.createElement('textarea');
            ta.value = lastJavaCode;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            showExportFeedback('Copiado al portapapeles');
        });
    };

    function showExportFeedback(message) {
        let feedback = document.getElementById('export-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.id = 'export-feedback';
            feedback.style.cssText = 'position:fixed; bottom:2rem; left:50%; transform:translateX(-50%); background:#161B22; border:1px solid var(--green); color:var(--green); padding:0.6rem 1.5rem; border-radius:6px; font-family:"JetBrains Mono",monospace; font-size:0.85rem; z-index:10000; opacity:0; transition:opacity 0.3s ease; box-shadow: 0 4px 15px rgba(0,229,255,0.2);';
            document.body.appendChild(feedback);
        }
        feedback.textContent = message;
        feedback.style.opacity = '1';
        setTimeout(() => { feedback.style.opacity = '0'; }, 2000);
    }

    // ===== SNIPPET LOADING (3.6) =====
    window.loadSnippet = function(snippetKey) {
        const snippet = SNIPPETS[snippetKey];
        if (snippet && inputArea) {
            inputArea.value = snippet;
            transpile();
        }
    };

    // Run on load and on typing
    inputArea.addEventListener('input', transpile);
    transpile();
});

// ===== PREDEFINED SNIPPETS (3.6) =====
const SNIPPETS = {
    "hello_world": `# Hola Mundo
print("¡Hola, mundo!")`,

    "variables": `# Variables y tipos
nombre = "Carlos"
edad = 25
es_estudiante = True
print("Nombre: " + nombre)`,

    "conditionals": `# Condicionales
edad = 18
if edad >= 18:
    print("Eres mayor de edad")`,

    "for_loop": `# Bucle For
for i in range(5):
    print(i)`,

    "fibonacci": `# Serie Fibonacci
a = 0
b = 1
for i in range(10):
    print(a)
    temp = a
    a = b
    b = temp + b`,

    "calculator": `# Calculadora simple
num1 = 10
num2 = 5
suma = num1 + num2
resta = num1 - num2
print(suma)
print(resta)`,

    "bubble_sort": `# Ordenamiento Burbuja
for i in range(5):
    for j in range(4):
        print(j)`,

    "class_animal": `# Clase Animal
nombre = "Firulais"
tipo = "Perro"
edad = 3
print(nombre)
print(tipo)`
};
