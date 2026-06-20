// progress.js - Manejo del progreso y gamificación en el cliente

document.addEventListener('DOMContentLoaded', () => {
    // 1. Rastrear si el usuario llega al final de la lección para marcarla completada
    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            // El usuario vio el final de la lección
            const lessonId = window.currentLessonId;
            if (lessonId) {
                markLessonCompleted(lessonId);
            }
            observer.disconnect(); // Solo contar una vez por carga de página
        }
    }, { threshold: 0.5 });
    
    // Observar el pie de página de la lección o los botones de navegación
    const lessonNav = document.querySelector('.lesson-navigation');
    if (lessonNav) {
        observer.observe(lessonNav);
    }

    // Actualizar sidebar inmediatamente al cargar
    fetchProgressSummary();
});

// Función global para que los quizzes puedan llamar al responder correctamente
window.trackProgress = function(lessonId, exerciseId) {
    fetch('/api/progreso/ejercicio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lesson_id: lessonId, exercise_id: exerciseId, passed: true })
    })
    .then(res => res.json())
    .then(data => {
        if (data.xp_gained > 0) {
            showXPNotification(`+${data.xp_gained} XP`, '¡Ejercicio completado!');
            updateSidebarProgress(data.summary);
        }
        if (data.badge_unlocked) {
            showBadgeNotification(data.badge);
        }
    })
    .catch(err => console.error("Error saving exercise progress:", err));
};

function markLessonCompleted(lessonId) {
    fetch('/api/progreso/leccion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lesson_id: lessonId })
    })
    .then(res => res.json())
    .then(data => {
        if (data.xp_gained > 0) {
            showXPNotification(`+${data.xp_gained} XP`, '¡Lección completada!');
            updateSidebarProgress(data.summary);
            
            // Marcar en la UI del sidebar
            const link = document.querySelector(`.nav-link[href*="${lessonId}"]`);
            if (link && !link.querySelector('.check-icon')) {
                link.innerHTML += ' <span class="check-icon" style="color:var(--green)">✓</span>';
            }
        }
        if (data.badge_unlocked) {
            showBadgeNotification(data.badge);
        }
    })
    .catch(err => console.error("Error saving lesson progress:", err));
}

function fetchProgressSummary() {
    fetch('/api/progreso/resumen')
        .then(res => res.json())
        .then(data => {
            if (data && data.success !== false) {
                updateSidebarProgress(data);
                // Marcar lecciones completadas en el menú
                if (data.completed_lessons) {
                    data.completed_lessons.forEach(lid => {
                        const link = document.querySelector(`.nav-link[href*="${lid}"]`);
                        if (link && !link.querySelector('.check-icon')) {
                            link.innerHTML += ' <span class="check-icon" style="color:var(--green)">✓</span>';
                        }
                    });
                }
            }
        })
        .catch(err => console.error("Error fetching progress summary:", err));
}

function updateSidebarProgress(data) {
    if (!data) return;
    
    // Si tenemos un contenedor para info de progreso (XP, nivel) en el sidebar
    let infoDiv = document.getElementById('sidebar-user-info');
    if (!infoDiv) {
        // Crear si no existe (normalmente debajo del buscador)
        const searchDiv = document.querySelector('.sidebar-search');
        if (searchDiv) {
            infoDiv = document.createElement('div');
            infoDiv.id = 'sidebar-user-info';
            infoDiv.className = 'sidebar-user-info';
            searchDiv.parentNode.insertBefore(infoDiv, searchDiv.nextSibling);
        }
    }
    
    if (infoDiv) {
        const level = Math.floor(data.total_xp / 100) + 1;
        const progressToNext = (data.total_xp % 100);
        
        infoDiv.innerHTML = `
            <div class="user-level-badge">Nivel ${level}</div>
            <div class="user-xp-text">${data.total_xp} XP Total</div>
            <div class="xp-bar-container">
                <div class="xp-bar-fill" style="width: ${progressToNext}%"></div>
            </div>
        `;
    }
}

// UI Helpers para notificaciones
function showXPNotification(xpText, title) {
    const notif = document.createElement('div');
    notif.className = 'xp-notification';
    notif.innerHTML = `<strong>${title}</strong><br><span class="xp-amount">${xpText}</span>`;
    document.body.appendChild(notif);
    
    // Animar y eliminar
    setTimeout(() => notif.classList.add('show'), 10);
    setTimeout(() => {
        notif.classList.remove('show');
        setTimeout(() => notif.remove(), 500);
    }, 3000);
}

function showBadgeNotification(badge) {
    const notif = document.createElement('div');
    notif.className = 'badge-notification';
    notif.innerHTML = `
        <div class="badge-icon">${badge.icon}</div>
        <div class="badge-text">
            <small>¡Insignia Desbloqueada!</small>
            <strong>${badge.name}</strong>
        </div>
    `;
    document.body.appendChild(notif);
    
    setTimeout(() => notif.classList.add('show'), 10);
    setTimeout(() => {
        notif.classList.remove('show');
        setTimeout(() => notif.remove(), 500);
    }, 5000);
}
