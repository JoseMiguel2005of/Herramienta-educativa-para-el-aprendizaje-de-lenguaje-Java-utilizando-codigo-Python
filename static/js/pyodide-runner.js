// pyodide-runner.js - Carga Lazy de Pyodide y ejecución

let pyodideInstance = null;
let pyodideLoading = false;

async function loadPyodideIfNeeded() {
    const statusEl = document.getElementById('pyodide-status');
    
    if (pyodideInstance) return pyodideInstance;
    
    if (pyodideLoading) {
        // Wait until it's loaded
        return new Promise(resolve => {
            const check = setInterval(() => {
                if (pyodideInstance) {
                    clearInterval(check);
                    resolve(pyodideInstance);
                }
            }, 100);
        });
    }

    pyodideLoading = true;
    if (statusEl) statusEl.textContent = "(Descargando motor Python, ~15MB...)";
    
    try {
        pyodideInstance = await loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/"
        });
        
        // Redirigir stdout a nuestra consola
        pyodideInstance.setStdout({
            batched: (str) => {
                const out = document.getElementById('python-console-output');
                if (out) out.textContent += str + "\n";
            }
        });
        
        if (statusEl) statusEl.textContent = "(Python listo)";
        setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 2000);
        
        return pyodideInstance;
    } catch (err) {
        if (statusEl) statusEl.textContent = "(Error cargando Python)";
        console.error("Pyodide init error:", err);
        throw err;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const btnRun = document.getElementById('btn-run-python');
    const editor = document.getElementById('practice-editor');
    const output = document.getElementById('python-console-output');
    const statusEl = document.getElementById('pyodide-status');

    if (btnRun && editor && output) {
        btnRun.addEventListener('click', async () => {
            const code = editor.value;
            output.textContent = ""; // Clear console
            
            // UI feedback
            const originalText = btnRun.textContent;
            btnRun.textContent = "Ejecutando...";
            btnRun.disabled = true;
            
            try {
                const pyodide = await loadPyodideIfNeeded();
                
                // Ejecutar el código
                // Import sys and setup to catch stderr if possible, or just run it
                await pyodide.runPythonAsync(code);
                
                // Si la ejecución no imprimió nada pero fue exitosa
                if (output.textContent.trim() === "") {
                    output.textContent = "";
                    const doneSpan = document.createElement("span");
                    doneSpan.style.color = "#a6e22e";
                    doneSpan.textContent = "[Ejecución completada sin salida en consola]";
                    output.appendChild(doneSpan);
                }
            } catch (err) {
                // Mostrar error en la consola usando nodos de texto seguros
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
