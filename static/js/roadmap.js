// roadmap.js - Renderiza el mapa usando Canvas API

document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('roadmap-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const container = document.getElementById('roadmap-container');
    const tooltip = document.getElementById('roadmap-tooltip');
    
    // Configuración
    let width = container.clientWidth;
    let height = container.clientHeight;
    canvas.width = width;
    canvas.height = height;
    
    // Nodos
    const nodes = [];
    const levelHeight = 160;
    const horizontalSpacing = 160;
    
    // Parse data
    let currentY = 80;
    window.ROADMAP_DATA.forEach(cat => {
        cat.sections.forEach(sec => {
            const sectionStartX = width / 2;
            let currentX = sectionStartX - ((sec.lessons.length - 1) * horizontalSpacing) / 2;
            
            sec.lessons.forEach(lesson => {
                // Formatear nombre: "hola-mundo" -> "Hola Mundo"
                let title = lesson.id.replace(/-/g, ' ');
                title = title.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

                nodes.push({
                    id: lesson.id,
                    title: title,
                    x: currentX,
                    y: currentY,
                    completed: window.COMPLETED_LESSONS.includes(lesson.id)
                });
                currentX += horizontalSpacing;
            });
            currentY += levelHeight;
        });
    });
    
    // Transformaciones para pan/zoom
    let scale = 1;
    let panX = 0;
    let panY = 0;
    let isDragging = false;
    let dragStartX, dragStartY;
    let lastMouseMove = 0; // Para evitar clicks accidentales tras drag largo
    
    function draw() {
        ctx.clearRect(0, 0, width, height);
        ctx.save();
        ctx.translate(panX, panY);
        ctx.scale(scale, scale);
        
        // Dibujar Grid
        const gridSize = 40;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.lineWidth = 1;
        const left = -panX/scale;
        const top = -panY/scale;
        const right = left + width/scale;
        const bottom = top + height/scale;
        
        ctx.beginPath();
        for (let x = Math.floor(left/gridSize)*gridSize; x < right; x+=gridSize) {
            ctx.moveTo(x, top);
            ctx.lineTo(x, bottom);
        }
        for (let y = Math.floor(top/gridSize)*gridSize; y < bottom; y+=gridSize) {
            ctx.moveTo(left, y);
            ctx.lineTo(right, y);
        }
        ctx.stroke();

        // Dibujar líneas
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
        ctx.lineWidth = 2;
        for (let i = 0; i < nodes.length - 1; i++) {
            const current = nodes[i];
            const next = nodes[i+1];
            // Solo dibujar líneas si están cerca verticalmente
            if (next.y - current.y <= levelHeight + 10) {
                ctx.beginPath();
                ctx.moveTo(current.x, current.y);
                const midY = current.y + (next.y - current.y) / 2;
                ctx.lineTo(current.x, midY);
                ctx.lineTo(next.x, midY);
                ctx.lineTo(next.x, next.y);
                ctx.stroke();
            }
        }
        
        // Dibujar nodos
        const rectSize = 48;
        const half = rectSize / 2;
        nodes.forEach(node => {
            ctx.fillStyle = node.completed ? '#04aa6d' : '#1a1a1a';
            ctx.fillRect(node.x - half, node.y - half, rectSize, rectSize);
            
            ctx.strokeStyle = node.completed ? '#00e5ff' : '#444';
            if (!node.completed) ctx.setLineDash([4, 4]);
            else ctx.setLineDash([]);
            
            ctx.lineWidth = 2;
            ctx.strokeRect(node.x - half, node.y - half, rectSize, rectSize);
            ctx.setLineDash([]);
            
            // Icono o inicial
            ctx.fillStyle = node.completed ? '#000' : '#fff';
            ctx.font = 'bold 18px "JetBrains Mono", monospace';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const initial = node.completed ? '✓' : node.title.charAt(0);
            ctx.fillText(initial, node.x, node.y + 2);
            
            // Texto pequeño debajo (si zoom > 0.8)
            if (scale > 0.8) {
                ctx.font = '12px "JetBrains Mono", monospace';
                ctx.fillStyle = 'rgba(255,255,255,0.8)';
                ctx.fillText(node.title.substring(0, 15) + (node.title.length > 15 ? '...' : ''), node.x, node.y + half + 15);
            }
        });
        
        ctx.restore();
    }
    
    function getTransformedPoint(x, y) {
        return {
            x: (x - panX) / scale,
            y: (y - panY) / scale
        };
    }
    
    // Eventos
    container.addEventListener('mousedown', e => {
        isDragging = true;
        dragStartX = e.clientX - panX;
        dragStartY = e.clientY - panY;
        container.style.cursor = 'grabbing';
    });
    
    window.addEventListener('mouseup', e => {
        isDragging = false;
        container.style.cursor = 'grab';
    });
    
    container.addEventListener('mousemove', e => {
        if (isDragging) {
            panX = e.clientX - dragStartX;
            panY = e.clientY - dragStartY;
            lastMouseMove = Date.now();
            draw();
            return;
        }
        
        // Hover
        const rect = canvas.getBoundingClientRect();
        const pt = getTransformedPoint(e.clientX - rect.left, e.clientY - rect.top);
        
        let hoveredNode = null;
        for (const node of nodes) {
            const dx = Math.abs(node.x - pt.x);
            const dy = Math.abs(node.y - pt.y);
            if (dx <= 24 && dy <= 24) {
                hoveredNode = node;
                break;
            }
        }
        
        if (hoveredNode) {
            canvas.style.cursor = 'pointer';
            tooltip.style.display = 'block';
            tooltip.style.left = (e.clientX + 15) + 'px';
            tooltip.style.top = (e.clientY + 15) + 'px';
            tooltip.innerHTML = `<div><span style="color:var(--python-color);">[MODULE]</span> ${hoveredNode.title}</div><div style="margin-top:0.5rem; color:${hoveredNode.completed ? 'var(--green)' : '#888'};">>_ STATUS: ${hoveredNode.completed ? '[ COMPLETED ]' : '[ LOCKED ]'}</div>`;
        } else {
            canvas.style.cursor = 'grab';
            tooltip.style.display = 'none';
        }
    });
    
    container.addEventListener('wheel', e => {
        e.preventDefault();
        const zoomIntensity = 0.1;
        const wheel = e.deltaY < 0 ? 1 : -1;
        const zoomFactor = Math.exp(wheel * zoomIntensity);
        
        const rect = canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        panX = mouseX - (mouseX - panX) * zoomFactor;
        panY = mouseY - (mouseY - panY) * zoomFactor;
        scale *= zoomFactor;
        
        draw();
    });
    
    container.addEventListener('click', e => {
        if (Date.now() - lastMouseMove < 100) return; // Ignore click if we were dragging
        
        const rect = canvas.getBoundingClientRect();
        const pt = getTransformedPoint(e.clientX - rect.left, e.clientY - rect.top);
        
        for (const node of nodes) {
            const dx = Math.abs(node.x - pt.x);
            const dy = Math.abs(node.y - pt.y);
            if (dx <= 24 && dy <= 24) {
                window.location.href = '/leccion/' + node.id;
                break;
            }
        }
    });
    
    window.addEventListener('resize', () => {
        width = container.clientWidth;
        height = container.clientHeight;
        canvas.width = width;
        canvas.height = height;
        draw();
    });
    
    // Centrar inicialmente el primer nodo no completado
    const firstUncompleted = nodes.find(n => !n.completed);
    if (firstUncompleted) {
        panX = width/2 - firstUncompleted.x * scale;
        panY = height/2 - firstUncompleted.y * scale;
    } else if (nodes.length > 0) {
        panX = width/2 - nodes[0].x * scale;
        panY = 100;
    }
    
    draw();
});
