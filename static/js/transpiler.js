/**
 * Visual Transpiler (AST Mapper)
 * Generates mapped tokens from basic Python to Java for visual hover tracking.
 */

document.addEventListener('DOMContentLoaded', () => {
    const inputArea = document.getElementById('python-input');
    const pyOutput = document.getElementById('python-ast-output');
    const javaOutput = document.getElementById('java-ast-output');
    
    let tokenCounter = 0;
    
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
        tokenCounter = 0;
        
        let indentLevel = 0;
        
        // Java boilerplate start
        const classId = generateTokenId();
        const mainId = generateTokenId();
        
        javaHtml += `${createTokenHtml("public class", "keyword", classId)} ${createTokenHtml("Programa", "variable", classId)} {\n`;
        javaHtml += `    ${createTokenHtml("public static void", "keyword", mainId)} ${createTokenHtml("main(String[] args)", "variable", mainId)} {\n`;
        
        for (let i = 0; i < lines.length; i++) {
            let line = lines[i];
            let trimmed = line.trim();
            
            // Detect indentation to close Java blocks (very naive logic for demo)
            let currentIndent = line.search(/\S/);
            if (currentIndent === -1) currentIndent = 0;
            
            if (currentIndent < indentLevel && trimmed !== '') {
                // Close Java blocks
                javaHtml += `        }\n`;
                indentLevel = currentIndent;
            }
            
            if (trimmed === '') {
                pyHtml += '\n';
                javaHtml += '\n';
                continue;
            }
            
            if (trimmed.startsWith('#')) {
                const id = generateTokenId();
                pyHtml += `${createTokenHtml(line, "comment", id)}\n`;
                javaHtml += `        ${createTokenHtml("//" + trimmed.substring(1), "comment", id)}\n`;
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
                indentLevel = currentIndent + 4;
                continue;
            }
            
            // Unhandled lines
            const id = generateTokenId();
            pyHtml += `${createTokenHtml(line, "punctuation", id)}\n`;
            javaHtml += `        // ${createTokenHtml("Sin traducción directa", "comment", id)}\n`;
        }
        
        // Close pending blocks
        while(indentLevel > 0) {
            javaHtml += `        }\n`;
            indentLevel -= 4;
        }
        
        // Java boilerplate end
        javaHtml += `    }\n`;
        javaHtml += `}\n`;
        
        pyOutput.innerHTML = pyHtml;
        javaOutput.innerHTML = javaHtml;
        
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

    // Run on load and on typing
    inputArea.addEventListener('input', transpile);
    transpile();
});
