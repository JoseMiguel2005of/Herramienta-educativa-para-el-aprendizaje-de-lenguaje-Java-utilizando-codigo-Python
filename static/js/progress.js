// progress.js - Manejo del progreso y gamificación en el cliente

function getScopedStorageKey(baseKey) {
    const uid = window.PY2JAVA_USER_ID;
    const scope = (uid !== undefined && uid !== null && String(uid).trim() !== '') ? String(uid) : 'anon';
    return `${baseKey}_${scope}`;
}

window.getScopedStorageKey = getScopedStorageKey;

function _getLevelTitlesMap() {
    return (window.PY2JAVA_LEVEL_TITLES && typeof window.PY2JAVA_LEVEL_TITLES === 'object')
        ? window.PY2JAVA_LEVEL_TITLES
        : {};
}

function getLevelTitle(level) {
    const titles = _getLevelTitlesMap();
    const lvl = parseInt(level, 10) || 1;
    if (lvl >= 20) return titles[20] || titles['20'] || 'Entidad Binaria Superior';
    return titles[lvl] || titles[String(lvl)] || titles[1] || titles['1'] || 'Iniciado';
}

function getNextLevelTitle(level) {
    const titles = _getLevelTitlesMap();
    const next = (parseInt(level, 10) || 1) + 1;
    if (next > 20) return null;
    return titles[next] || titles[String(next)] || null;
}

function _isAuthPage() {
    const path = (window.location.pathname || '').toLowerCase();
    return path.startsWith('/login') || path.startsWith('/register') || path.startsWith('/recuperar');
}

function _isAuthenticatedClient() {
    return window.PY2JAVA_USER_ID !== undefined && window.PY2JAVA_USER_ID !== null && String(window.PY2JAVA_USER_ID).trim() !== '';
}

// Definiciones de logros del cliente
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

function checkForNewAchievements(summary, isLiveAction = false) {
    if (!summary || !_isAuthenticatedClient()) return;
    const currentAchievements = computeAchievements(summary);
    const unlockedIds = currentAchievements.filter(a => a.unlocked).map(a => a.id);

    const storageKey = getScopedStorageKey('py2java_achievements');
    const storedStr = localStorage.getItem(storageKey);
    let previousIds = [];
    if (storedStr) {
        try {
            previousIds = JSON.parse(storedStr) || [];
        } catch (e) {
            previousIds = [];
        }
    }

    // Identificar logros recién desbloqueados
    const newlyUnlocked = unlockedIds.filter(id => !previousIds.includes(id));

    // Actualizar estado en almacenamiento local segmentado por user_id
    try {
        localStorage.setItem(storageKey, JSON.stringify(unlockedIds));
    } catch (e) {}

    // SOLO mostrar modal si fue una acción en vivo (ej: terminar ejercicio/lección) y ya existía historial previo
    if (isLiveAction && newlyUnlocked.length > 0 && storedStr !== null) {
        const newAchievements = currentAchievements.filter(a => newlyUnlocked.includes(a.id));
        showAchievementUnlockModal(newAchievements);
    }
}

// Notificación emergente de XP
function showXPNotification(xpText, title) {
    let container = document.getElementById('xp-toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'xp-toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'xp-toast';

    const iconDiv = document.createElement('div');
    iconDiv.className = 'xp-toast-icon';
    iconDiv.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" fill="none" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path></svg>';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'xp-toast-content';
    const titleSpan = document.createElement('span');
    titleSpan.className = 'xp-toast-title';
    titleSpan.textContent = title;
    const amountSpan = document.createElement('span');
    amountSpan.className = 'xp-toast-amount';
    amountSpan.textContent = xpText;
    contentDiv.appendChild(titleSpan);
    contentDiv.appendChild(amountSpan);

    const particlesDiv = document.createElement('div');
    particlesDiv.className = 'xp-toast-particles';
    particlesDiv.setAttribute('aria-hidden', 'true');

    toast.appendChild(iconDiv);
    toast.appendChild(contentDiv);
    toast.appendChild(particlesDiv);

    container.appendChild(toast);
    spawnParticles(particlesDiv);

    requestAnimationFrame(() => {
        toast.classList.add('xp-toast-show');
    });

    setTimeout(() => {
        toast.classList.add('xp-toast-hide');
        setTimeout(() => toast.remove(), 600);
    }, 3500);
}

function spawnParticles(container) {
    if (!container) return;
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

// Modal de logro desbloqueado
function showAchievementUnlockModal(achievements) {
    if (!achievements || achievements.length === 0) return;

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
                <div class="neu-icon-box" style="margin:0 auto 0.5rem; color:#FFD700;">
                    <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" fill="none" stroke-width="2"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>
                </div>
                <h2>¡Logro${achievements.length > 1 ? 's' : ''} Desbloqueado${achievements.length > 1 ? 's' : ''}!</h2>
            </div>
            <div class="achievement-modal-cards">
                ${achievementCards}
            </div>
            <button class="achievement-modal-btn" id="achievement-close-btn">¡Genial!</button>
        </div>
    `;

    document.body.appendChild(overlay);

    requestAnimationFrame(() => {
        overlay.classList.add('achievement-modal-visible');
    });

    spawnConfetti(overlay.querySelector('.achievement-modal-confetti'));

    overlay.querySelector('#achievement-close-btn').addEventListener('click', () => {
        overlay.classList.remove('achievement-modal-visible');
        setTimeout(() => overlay.remove(), 400);
    });

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.classList.remove('achievement-modal-visible');
            setTimeout(() => overlay.remove(), 400);
        }
    });
}

function spawnConfetti(container) {
    if (!container) return;
    const reduceMotion =
        (typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) ||
        document.documentElement.dataset.a11yMotion === 'reduce';
    if (reduceMotion) return;
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

function showBadgeNotification(badge) {
    if (!badge) return;
    const notif = document.createElement('div');
    notif.className = 'badge-notification';
    const iconDiv = document.createElement('div');
    iconDiv.className = 'badge-icon';
    iconDiv.textContent = badge.icon || '★';
    const textDiv = document.createElement('div');
    textDiv.className = 'badge-text';
    const small = document.createElement('small');
    small.textContent = '¡Insignia Desbloqueada!';
    const strong = document.createElement('strong');
    strong.textContent = badge.name || '';
    textDiv.appendChild(small);
    textDiv.appendChild(strong);
    notif.appendChild(iconDiv);
    notif.appendChild(textDiv);
    document.body.appendChild(notif);

    setTimeout(() => notif.classList.add('show'), 10);
    setTimeout(() => {
        notif.classList.remove('show');
        setTimeout(() => notif.remove(), 500);
    }, 5000);
}

// Inicialización (sin autocompletado por scroll; utiliza botón explícito en lesson.html)
document.addEventListener('DOMContentLoaded', () => {
    const completeBtn = document.getElementById('btn-complete-lesson');
    if (completeBtn && !completeBtn.disabled) {
        completeBtn.addEventListener('click', () => {
            const lessonId = completeBtn.dataset.lessonId || window.currentLessonId;
            if (lessonId) {
                markLessonCompleted(lessonId, completeBtn);
            }
        });
    }

    // No consultar ni renderizar "0 XP Total" en /login, /register, /recuperar o sin sesión
    if (_isAuthenticatedClient() && !_isAuthPage()) {
        fetchProgressSummary();
    }
});

function _getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

// Sincroniza notificaciones y sidebar a partir de respuestas verificadas por el servidor
window.onProgressXpUpdate = function(data, titleText) {
    if (!data) return;
    if (data.xp_gained > 0) {
        showXPNotification(`+${data.xp_gained} XP`, titleText || '¡Ejercicio completado!');
        if (data.summary) {
            updateSidebarProgress(data.summary);
            checkForNewAchievements(data.summary, true);
        }
    }
    if (data.badge_unlocked) {
        showBadgeNotification(data.badge);
    }
};

function markLessonCompleted(lessonId, triggerBtn) {
    const statusEl = document.getElementById('lesson-complete-status');
    const origText = triggerBtn ? triggerBtn.textContent : '';
    if (triggerBtn) {
        triggerBtn.disabled = true;
        triggerBtn.textContent = 'Guardando progreso...';
    }

    fetch('/api/progreso/leccion', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': _getCsrfToken()
        },
        body: JSON.stringify({ lesson_id: lessonId })
    })
    .then(async res => {
        const data = await res.json().catch(() => ({ ok: false }));
        if (!res.ok || !data.ok) {
            throw new Error(data.error || 'No se pudo marcar la lección como completada.');
        }
        return data;
    })
    .then(data => {
        if (data.xp_gained > 0) {
            showXPNotification(`+${data.xp_gained} XP`, '¡Lección completada!');
        }
        if (data.summary) {
            updateSidebarProgress(data.summary);
            checkForNewAchievements(data.summary, true);
        }
        markSidebarLesson(lessonId);
        if (triggerBtn) {
            triggerBtn.textContent = '✓ Lección completada';
            triggerBtn.classList.add('is-completed');
            triggerBtn.disabled = true;
        }
        if (statusEl) {
            statusEl.textContent = data.xp_gained > 0
                ? `Progreso guardado (+${data.xp_gained} XP).`
                : 'Esta lección ya estaba marcada como completada.';
        }
        if (data.badge_unlocked) {
            showBadgeNotification(data.badge);
        }
    })
    .catch(err => {
        console.error('Error al registrar lección:', err);
        if (triggerBtn) {
            triggerBtn.disabled = false;
            triggerBtn.textContent = origText || 'Marcar lección como completada';
        }
        if (statusEl) {
            statusEl.textContent = err.message || 'No se pudo guardar el progreso.';
        }
    });
}

function markSidebarLesson(lessonId) {
    if (!lessonId) return;
    const expectedPath = `/leccion/${lessonId}`;
    const links = document.querySelectorAll('.nav-link');
    links.forEach(link => {
        const href = link.getAttribute('href') || '';
        let linkPath = '';
        try {
            linkPath = new URL(href, window.location.origin).pathname;
        } catch (e) {
            linkPath = href.split('?')[0].split('#')[0];
        }
        if (linkPath === expectedPath && !link.querySelector('.sidebar-check')) {
            const check = document.createElement('span');
            check.className = 'sidebar-check';
            check.textContent = '✓';
            check.setAttribute('aria-label', 'Lección completada');
            check.setAttribute('title', 'Completada');
            link.appendChild(check);
            link.classList.add('lesson-completed');
        }
    });
}

function fetchProgressSummary() {
    if (!_isAuthenticatedClient() || _isAuthPage()) return;
    fetch('/api/progreso/resumen')
        .then(res => res.json())
        .then(data => {
            if (data && data.authenticated && data.success !== false) {
                updateSidebarProgress(data);
                if (data.completed_lessons) {
                    data.completed_lessons.forEach(lid => {
                        markSidebarLesson(lid);
                    });
                }
                // Sincronizar estado de logros de forma silenciosa sin abrir modales
                checkForNewAchievements(data, false);
            }
        })
        .catch(err => console.error('Error al sincronizar resumen:', err));
}

function updateSidebarProgress(data) {
    if (!data || !_isAuthenticatedClient() || _isAuthPage()) return;

    let infoDiv = document.getElementById('sidebar-user-info');
    if (!infoDiv) {
        const searchDiv = document.querySelector('.sidebar-search');
        if (searchDiv) {
            infoDiv = document.createElement('div');
            infoDiv.id = 'sidebar-user-info';
            infoDiv.className = 'sidebar-user-info';
            searchDiv.parentNode.insertBefore(infoDiv, searchDiv.nextSibling);
        }
    }

    if (infoDiv) {
        const totalXp = Number(data.total_xp) || 0;
        const level = Math.floor(totalXp / 100) + 1;
        const progressToNext = totalXp % 100;
        const title = getLevelTitle(level);
        const nextTitle = getNextLevelTitle(level);
        const nextTitleHtml = nextTitle
            ? `<div class="user-next-title">Siguiente: ${nextTitle} (${100 - progressToNext} XP)</div>`
            : `<div class="user-next-title" style="color: var(--green);">¡Nivel máximo!</div>`;

        infoDiv.innerHTML = `
            <div class="user-level-badge">LVL ${level} — ${title}</div>
            <div class="user-xp-text">${totalXp} XP Total</div>
            <div class="xp-bar-container">
                <div class="xp-bar-fill" style="width: ${progressToNext}%"></div>
            </div>
            ${nextTitleHtml}
        `;
    }
}
