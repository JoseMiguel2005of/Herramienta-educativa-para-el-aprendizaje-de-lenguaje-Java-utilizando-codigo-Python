// progress.js - Manejo del progreso y gamificación en el cliente

// ===== LEVEL TITLES MAP (1.4) =====
const LEVEL_TITLES = {
    1: "Iniciado",
    2: "Novato",
    3: "Aprendiz",
    4: "Estudiante",
    5: "Practicante",
    6: "Competente",
    7: "Hábil",
    8: "Experto",
    9: "Veterano",
    10: "Pythonista",
    11: "Maestro",
    12: "Arquitecto",
    13: "Virtuoso",
    14: "Gurú",
    15: "Sensei",
    16: "Leyenda",
    17: "Oráculo",
    18: "Iluminado",
    19: "Trascendente",
    20: "Omnisciente"
};

function getLevelTitle(level) {
    if (level >= 20) return LEVEL_TITLES[20];
    return LEVEL_TITLES[level] || "Iniciado";
}

function getNextLevelTitle(level) {
    const next = level + 1;
    if (next > 20) return null;
    return LEVEL_TITLES[next] || null;
}

// ===== ACHIEVEMENT DEFINITIONS (for client-side detection) (1.7) =====
function computeAchievements(summary) {
    const completedCount = summary.completed_lessons ? summary.completed_lessons.length : 0;
    const totalXp = summary.total_xp || 0;

    return [
        { id: "01", name: "Primer Paso", desc: "Gana tu primer XP", unlocked: totalXp > 0 },
        { id: "02", name: "Estudiante", desc: "Completa 1 lección", unlocked: completedCount >= 1 },
        { id: "03", name: "En Racha", desc: "Completa 5 lecciones", unlocked: completedCount >= 5 },
        { id: "04", name: "Explorador", desc: "Completa 10 lecciones", unlocked: completedCount >= 10 },
        { id: "05", name: "Imparable", desc: "Completa 25 lecciones", unlocked: completedCount >= 25 },
        { id: "06", name: "Medio Camino", desc: "Completa 50 lecciones", unlocked: completedCount >= 50 },
        { id: "07", name: "Maestro", desc: "Completa 100 lecciones", unlocked: completedCount >= 100 },
        { id: "09", name: "Nivel 5", desc: "Alcanza nivel 5", unlocked: totalXp >= 400 },
        { id: "10", name: "Nivel 10", desc: "Alcanza nivel 10", unlocked: totalXp >= 900 },
    ];
}

function checkForNewAchievements(summary) {
    const currentAchievements = computeAchievements(summary);
    const unlockedIds = currentAchievements.filter(a => a.unlocked).map(a => a.id);

    // Compare with stored state
    const storedStr = localStorage.getItem('py2java_achievements');
    const previousIds = storedStr ? JSON.parse(storedStr) : [];

    // Find newly unlocked
    const newlyUnlocked = unlockedIds.filter(id => !previousIds.includes(id));

    // Update stored state
    localStorage.setItem('py2java_achievements', JSON.stringify(unlockedIds));

    // Show modal for each new achievement
    if (newlyUnlocked.length > 0) {
        const newAchievements = currentAchievements.filter(a => newlyUnlocked.includes(a.id));
        showAchievementUnlockModal(newAchievements);
    }
}

// ===== XP TOAST COMPONENT (1.3) =====
function showXPNotification(xpText, title) {
    // Create toast container if it doesn't exist
    let container = document.getElementById('xp-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'xp-toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'xp-toast';
    toast.innerHTML = `
        <div class="xp-toast-icon">⚡</div>
        <div class="xp-toast-content">
            <span class="xp-toast-title">${title}</span>
            <span class="xp-toast-amount">${xpText}</span>
        </div>
        <div class="xp-toast-particles" aria-hidden="true"></div>
    `;

    container.appendChild(toast);

    // Spawn particles
    spawnParticles(toast.querySelector('.xp-toast-particles'));

    // Animate in
    requestAnimationFrame(() => {
        toast.classList.add('xp-toast-show');
    });

    // Animate out and remove
    setTimeout(() => {
        toast.classList.add('xp-toast-hide');
        setTimeout(() => toast.remove(), 600);
    }, 3500);
}

function spawnParticles(container) {
    const colors = ['#00e5ff', '#ffd700', '#ff6b6b', '#51cf66', '#845ef7'];
    for (let i = 0; i < 12; i++) {
        const particle = document.createElement('span');
        particle.className = 'xp-particle';
        particle.style.setProperty('--x', `${(Math.random() - 0.5) * 120}px`);
        particle.style.setProperty('--y', `${-Math.random() * 80 - 20}px`);
        particle.style.setProperty('--delay', `${Math.random() * 0.3}s`);
        particle.style.setProperty('--color', colors[Math.floor(Math.random() * colors.length)]);
        container.appendChild(particle);
    }
}

// ===== ACHIEVEMENT UNLOCK MODAL (1.7) =====
function showAchievementUnlockModal(achievements) {
    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'achievement-modal-overlay';

    let achievementCards = achievements.map(a => `
        <div class="achievement-modal-card">
            <div class="achievement-modal-id">${a.id}</div>
            <div class="achievement-modal-info">
                <span class="achievement-modal-name">${a.name}</span>
                <span class="achievement-modal-desc">${a.desc}</span>
            </div>
        </div>
    `).join('');

    overlay.innerHTML = `
        <div class="achievement-modal-content">
            <div class="achievement-modal-confetti" aria-hidden="true"></div>
            <div class="achievement-modal-header">
                <span class="achievement-modal-star">🏆</span>
                <h2>¡Logro${achievements.length > 1 ? 's' : ''} Desbloqueado${achievements.length > 1 ? 's' : ''}!</h2>
            </div>
            <div class="achievement-modal-cards">
                ${achievementCards}
            </div>
            <button class="achievement-modal-btn" id="achievement-close-btn">¡Genial!</button>
        </div>
    `;

    document.body.appendChild(overlay);

    // Animate in
    requestAnimationFrame(() => {
        overlay.classList.add('achievement-modal-visible');
    });

    // Spawn confetti
    spawnConfetti(overlay.querySelector('.achievement-modal-confetti'));

    // Close
    overlay.querySelector('#achievement-close-btn').addEventListener('click', () => {
        overlay.classList.remove('achievement-modal-visible');
        setTimeout(() => overlay.remove(), 400);
    });

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.classList.remove('achievement-modal-visible');
            setTimeout(() => overlay.remove(), 400);
        }
    });
}

function spawnConfetti(container) {
    const colors = ['#ffd700', '#ff6b6b', '#00e5ff', '#51cf66', '#845ef7', '#ff922b', '#ff85c0'];
    for (let i = 0; i < 40; i++) {
        const confetti = document.createElement('span');
        confetti.className = 'confetti-piece';
        confetti.style.setProperty('--x', `${(Math.random() - 0.5) * 300}px`);
        confetti.style.setProperty('--y', `${-Math.random() * 200 - 50}px`);
        confetti.style.setProperty('--r', `${Math.random() * 720 - 360}deg`);
        confetti.style.setProperty('--delay', `${Math.random() * 0.5}s`);
        confetti.style.setProperty('--color', colors[Math.floor(Math.random() * colors.length)]);
        confetti.style.setProperty('--size', `${Math.random() * 6 + 4}px`);
        container.appendChild(confetti);
    }
}

// ===== BADGE NOTIFICATION =====
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

// ===== MAIN INITIALIZATION =====
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
            checkForNewAchievements(data.summary);
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
            checkForNewAchievements(data.summary);

            // Marcar en la UI del sidebar
            markSidebarLesson(lessonId);
        }
        if (data.badge_unlocked) {
            showBadgeNotification(data.badge);
        }
    })
    .catch(err => console.error("Error saving lesson progress:", err));
}

// ===== SIDEBAR CHECKMARKS (1.8) =====
function markSidebarLesson(lessonId) {
    const links = document.querySelectorAll('.nav-link');
    links.forEach(link => {
        const href = link.getAttribute('href') || '';
        if (href.includes(lessonId) && !link.querySelector('.sidebar-check')) {
            const check = document.createElement('span');
            check.className = 'sidebar-check';
            check.textContent = '✓';
            link.appendChild(check);
            link.classList.add('lesson-completed');
        }
    });
}

function fetchProgressSummary() {
    fetch('/api/progreso/resumen')
        .then(res => res.json())
        .then(data => {
            if (data && data.success !== false) {
                updateSidebarProgress(data);
                // Marcar lecciones completadas en el menú (1.8)
                if (data.completed_lessons) {
                    data.completed_lessons.forEach(lid => {
                        markSidebarLesson(lid);
                    });
                }
                // Check achievements on page load (for first-time badge sync)
                checkForNewAchievements(data);
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
        const title = getLevelTitle(level);
        const nextTitle = getNextLevelTitle(level);
        const nextTitleHtml = nextTitle
            ? `<div class="user-next-title">Siguiente: ${nextTitle} (${100 - progressToNext} XP)</div>`
            : `<div class="user-next-title" style="color: var(--green);">¡Nivel máximo!</div>`;

        infoDiv.innerHTML = `
            <div class="user-level-badge">LVL ${level} — ${title}</div>
            <div class="user-xp-text">${data.total_xp} XP Total</div>
            <div class="xp-bar-container">
                <div class="xp-bar-fill" style="width: ${progressToNext}%"></div>
            </div>
            ${nextTitleHtml}
        `;
    }
}
