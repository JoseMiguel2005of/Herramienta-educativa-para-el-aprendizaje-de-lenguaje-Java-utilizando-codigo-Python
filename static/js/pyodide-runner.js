// pyodide-runner.js - Carga Lazy de Pyodide, paquetes científicos y ejecución con captura de stdout/stderr

let pyodideInstance = null;
let pyodideLoading = false;
let pyodideLoadPromise = null;

const EXTERNAL_SERVER_IMPORTS = [
    { re: /(?:^|\n)\s*(?:import|from)\s+mysql\b/i, service: "MySQL" },
    { re: /(?:^|\n)\s*(?:import|from)\s+pymysql\b/i, service: "MySQL (PyMySQL)" },
    { re: /(?:^|\n)\s*(?:import|from)\s+MySQLdb\b/, service: "MySQL" },
    { re: /(?:^|\n)\s*(?:import|from)\s+pymongo\b/i, service: "MongoDB (PyMongo)" },
    { re: /(?:^|\n)\s*(?:import|from)\s+motor\b/i, service: "MongoDB (Motor)" },
    { re: /(?:^|\n)\s*(?:import|from)\s+psycopg2\b/i, service: "PostgreSQL" },
];

function detectExternalServerDependency(code) {
    if (typeof code !== "string" || !code.trim()) return null;
    for (const rule of EXTERNAL_SERVER_IMPORTS) {
        if (rule.re.test(code)) {
            return rule.service;
        }
    }
    return null;
}

async function loadPyodideIfNeeded(customStatusEl) {
    const statusEl = customStatusEl || document.getElementById("pyodide-status");

    if (pyodideInstance) return pyodideInstance;

    if (pyodideLoading && pyodideLoadPromise) {
        return pyodideLoadPromise;
    }

    pyodideLoading = true;
    if (statusEl) statusEl.textContent = "(Descargando motor Python, ~15MB...)";

    pyodideLoadPromise = (async () => {
        try {
            if (typeof loadPyodide !== "function") {
                throw new Error("El cargador de Pyodide no está disponible en esta página.");
            }
            const instance = await loadPyodide({
                indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/",
            });
            pyodideInstance = instance;

            if (statusEl) statusEl.textContent = "(Python listo)";
            setTimeout(() => {
                if (statusEl && statusEl.textContent === "(Python listo)") {
                    statusEl.textContent = "";
                }
            }, 2000);

            return instance;
        } catch (err) {
            pyodideInstance = null;
            pyodideLoadPromise = null;
            if (statusEl) statusEl.textContent = "(Error cargando Python — puedes reintentar)";
            console.error("Pyodide init error:", err);
            throw err;
        } finally {
            pyodideLoading = false;
        }
    })();

    return pyodideLoadPromise;
}

async function runPythonInBrowser(code, options = {}) {
    const statusEl = options.statusEl || document.getElementById("pyodide-status");
    const externalService = detectExternalServerDependency(code);
    if (externalService) {
        return {
            ok: false,
            blockedExternal: true,
            service: externalService,
            stdout: "",
            stderr: "",
            message: `Ejemplo de consola / solo lectura: este código utiliza ${externalService}, que requiere un servidor de base de datos externo y no puede ejecutarse dentro del navegador.`,
        };
    }

    const pyodide = await loadPyodideIfNeeded(statusEl);

    if (typeof pyodide.loadPackagesFromImports === "function") {
        if (statusEl) statusEl.textContent = "(Cargando paquetes requeridos...)";
        try {
            await pyodide.loadPackagesFromImports(code);
        } finally {
            if (statusEl && statusEl.textContent === "(Cargando paquetes requeridos...)") {
                statusEl.textContent = "";
            }
        }
    }

    let stdout = "";
    let stderr = "";

    pyodide.setStdout({
        batched: (line) => {
            stdout += line + "\n";
            if (typeof options.onStdout === "function") {
                options.onStdout(line);
            }
        },
    });

    pyodide.setStderr({
        batched: (line) => {
            stderr += line + "\n";
            if (typeof options.onStderr === "function") {
                options.onStderr(line);
            }
        },
    });

    try {
        await pyodide.runPythonAsync(code);
        return {
            ok: true,
            blockedExternal: false,
            stdout: stdout,
            stderr: stderr,
            error: null,
        };
    } catch (err) {
        return {
            ok: false,
            blockedExternal: false,
            stdout: stdout,
            stderr: stderr,
            error: err.message || String(err),
        };
    }
}

function renderConsoleResult(targetEl, result) {
    if (!targetEl) return;
    targetEl.textContent = "";

    if (result.blockedExternal) {
        const noteSpan = document.createElement("span");
        noteSpan.style.color = "#f59e0b";
        noteSpan.textContent = "ℹ " + result.message;
        targetEl.appendChild(noteSpan);
        return;
    }

    if (result.stdout) {
        const outNode = document.createTextNode(result.stdout);
        targetEl.appendChild(outNode);
    }

    if (result.stderr) {
        const stderrSpan = document.createElement("span");
        stderrSpan.style.color = "#ff9800";
        stderrSpan.textContent = result.stderr;
        targetEl.appendChild(stderrSpan);
    }

    if (!result.ok && result.error) {
        const errSpan = document.createElement("span");
        errSpan.style.color = "#ef5350";
        errSpan.textContent = (result.stdout || result.stderr ? "\n" : "") + result.error;
        targetEl.appendChild(errSpan);
        return;
    }

    if (!result.stdout.trim() && !result.stderr.trim()) {
        const doneSpan = document.createElement("span");
        doneSpan.style.color = "#a6e22e";
        doneSpan.textContent = "[Ejecución completada sin salida en consola]";
        targetEl.appendChild(doneSpan);
    }
}

window.loadPyodideIfNeeded = loadPyodideIfNeeded;
window.runPythonInBrowser = runPythonInBrowser;
window.renderConsoleResult = renderConsoleResult;
window.detectExternalServerDependency = detectExternalServerDependency;

document.addEventListener("DOMContentLoaded", () => {
    const btnRun = document.getElementById("btn-run-python");
    const editor = document.getElementById("practice-editor");
    const output = document.getElementById("python-console-output");
    const statusEl = document.getElementById("pyodide-status");

    if (btnRun && editor && output && !btnRun.disabled) {
        btnRun.addEventListener("click", async () => {
            const code = editor.value;
            output.textContent = "";

            const originalText = btnRun.textContent;
            btnRun.textContent = "Ejecutando...";
            btnRun.disabled = true;

            try {
                const result = await runPythonInBrowser(code, { statusEl });
                renderConsoleResult(output, result);
            } catch (err) {
                output.textContent = "";
                const errSpan = document.createElement("span");
                errSpan.style.color = "#ef5350";
                errSpan.textContent = err.message || String(err);
                output.appendChild(errSpan);
            } finally {
                btnRun.textContent = originalText;
                btnRun.disabled = false;
            }
        });
    }
});
