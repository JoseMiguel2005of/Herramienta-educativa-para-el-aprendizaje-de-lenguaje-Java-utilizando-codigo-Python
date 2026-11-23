/**
 * Py2Java Focus Study Timer (Temporizador / Cronómetro de Estudio)
 * - Segmentado por usuario en localStorage
 * - Sin autoinicio en /login, /register ni pantallas de recuperación
 * - Persistencia eficiente por delta de timestamps en visibilitychange/beforeunload (sin escribir cada segundo)
 * - Modal accesible WCAG 2.1 AA (role="dialog", aria-modal, aria-labelledby, Escape, trampa y retorno de foco)
 * - Respeta prefers-reduced-motion y data-a11y-motion="reduce"
 */

(function () {
    'use strict';

    const AUTH_PATHS = ['/login', '/register', '/recuperar', '/restablecer'];
    const MAX_DELTA_SECONDS = 86400; // cap 24h

    function isAuthPage() {
        const path = (window.location && window.location.pathname) ? window.location.pathname : '';
        return AUTH_PATHS.some(prefix => path === prefix || path.startsWith(prefix + '/'));
    }

    function getStorageKey() {
        if (typeof window.getScopedStorageKey === 'function') {
            return window.getScopedStorageKey('py2java_study_timer_v2');
        }
        const uid = window.PY2JAVA_USER_ID;
        const scope = (uid !== undefined && uid !== null && String(uid).trim() !== '') ? String(uid) : 'anon';
        return `py2java_study_timer_v2_${scope}`;
    }

    function prefersReducedMotion() {
        return (
            (typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) ||
            document.documentElement.dataset.a11yMotion === 'reduce'
        );
    }

    // Default state (opt-in: no arranca solo al abrir el sitio por primera vez)
    let state = {
        accumulatedSeconds: 0,
        targetMinutes: 25, // default 25 min (Pomodoro)
        isRunning: false,
        runningSinceMs: null,
        goalNotified: false,
        soundEnabled: true
    };

    let timerInterval = null;
    let audioCtx = null;
    let lastFocusedBeforeModal = null;

    function getCurrentTotalSeconds() {
        if (state.isRunning && state.runningSinceMs) {
            const elapsed = Math.floor((Date.now() - state.runningSinceMs) / 1000);
            if (elapsed > 0) {
                return state.accumulatedSeconds + Math.min(elapsed, MAX_DELTA_SECONDS);
            }
        }
        return state.accumulatedSeconds;
    }

    function commitElapsed() {
        if (state.isRunning && state.runningSinceMs) {
            const elapsed = Math.floor((Date.now() - state.runningSinceMs) / 1000);
            if (elapsed > 0) {
                state.accumulatedSeconds += Math.min(elapsed, MAX_DELTA_SECONDS);
            }
            state.runningSinceMs = Date.now();
        }
    }

    function loadState() {
        const authPage = isAuthPage();
        try {
            const saved = localStorage.getItem(getStorageKey());
            if (saved) {
                const parsed = JSON.parse(saved);
                state.accumulatedSeconds = Number.isFinite(parsed.accumulatedSeconds) && parsed.accumulatedSeconds >= 0
                    ? Math.floor(parsed.accumulatedSeconds)
                    : 0;
                state.targetMinutes = Number.isFinite(parsed.targetMinutes) && parsed.targetMinutes >= 0
                    ? Math.floor(parsed.targetMinutes)
                    : 25;
                state.goalNotified = Boolean(parsed.goalNotified);
                state.soundEnabled = parsed.soundEnabled !== undefined ? Boolean(parsed.soundEnabled) : true;

                if (authPage) {
                    // Nunca autoiniciar en /login, /register o recuperación
                    state.isRunning = false;
                    state.runningSinceMs = null;
                } else {
                    state.isRunning = Boolean(parsed.isRunning);
                    const refTs = Number.isFinite(parsed.runningSinceMs) ? parsed.runningSinceMs : parsed.lastTimestamp;
                    if (state.isRunning && refTs) {
                        const elapsed = Math.floor((Date.now() - refTs) / 1000);
                        if (elapsed > 0 && elapsed < MAX_DELTA_SECONDS) {
                            state.accumulatedSeconds += elapsed;
                        }
                        state.runningSinceMs = Date.now();
                    } else {
                        state.runningSinceMs = state.isRunning ? Date.now() : null;
                    }
                }
                return;
            }
        } catch (e) {
            console.warn('Could not load study timer state:', e);
        }

        // Estado inicial limpio: el usuario activa el cronómetro bajo demanda
        state.isRunning = false;
        state.runningSinceMs = null;
    }

    function saveState() {
        try {
            commitElapsed();
            const payload = {
                accumulatedSeconds: state.accumulatedSeconds,
                targetMinutes: state.targetMinutes,
                isRunning: state.isRunning,
                runningSinceMs: state.isRunning ? state.runningSinceMs : null,
                goalNotified: state.goalNotified,
                soundEnabled: state.soundEnabled
            };
            localStorage.setItem(getStorageKey(), JSON.stringify(payload));
        } catch (e) {
            // Storage unavailable
        }
    }

    function formatTime(totalSeconds) {
        const safe = Math.max(0, Math.floor(totalSeconds));
        const h = Math.floor(safe / 3600);
        const m = Math.floor((safe % 3600) / 60);
        const s = safe % 60;

        const pad = (n) => String(n).padStart(2, '0');
        if (h > 0) {
            return `${h}:${pad(m)}:${pad(s)}`;
        }
        return `${pad(m)}:${pad(s)}`;
    }

    function playChime() {
        if (!state.soundEnabled) return;
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;

            if (!audioCtx) audioCtx = new AudioContext();
            if (audioCtx.state === 'suspended') audioCtx.resume();

            const notes = [
                { freq: 523.25, time: 0 },    // C5
                { freq: 659.25, time: 0.15 }, // E5
                { freq: 783.99, time: 0.30 }, // G5
                { freq: 1046.50, time: 0.45 } // C6
            ];

            notes.forEach(note => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();

                osc.type = 'sine';
                osc.frequency.setValueAtTime(note.freq, audioCtx.currentTime + note.time);

                gain.gain.setValueAtTime(0, audioCtx.currentTime + note.time);
                gain.gain.linearRampToValueAtTime(0.3, audioCtx.currentTime + note.time + 0.05);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + note.time + 0.8);

                osc.connect(gain);
                gain.connect(audioCtx.destination);

                osc.start(audioCtx.currentTime + note.time);
                osc.stop(audioCtx.currentTime + note.time + 0.85);
            });
        } catch (e) {
            console.warn('Web Audio error:', e);
        }
    }

    function showCelebration() {
        playChime();

        const existing = document.querySelector('.study-celebration-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'study-celebration-toast';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');

        const iconDiv = document.createElement('div');
        iconDiv.className = 'celebration-icon';
        iconDiv.setAttribute('aria-hidden', 'true');
        iconDiv.innerHTML = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" fill="none" stroke-width="2"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"></path><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"></path><path d="M4 22h16"></path><path d="M10 14.66V17c0 .55-.45 1-1 1H8c-.55 0-1 .45-1 1v1c0 .55.45 1 1 1h8c.55 0 1-.45 1-1v-1c0-.55-.45-1-1-1h-1c-.55 0-1-.45-1-1v-2.34"></path><path d="M18 2H6v7a6 6 0 0 0 12 0V2z"></path></svg>';

        const bodyDiv = document.createElement('div');
        bodyDiv.className = 'celebration-body';
        const titleEl = document.createElement('h4');
        titleEl.textContent = '¡Objetivo de Estudio Cumplido!';
        const descEl = document.createElement('p');
        descEl.textContent = `Has alcanzado tu meta de ${state.targetMinutes} minutos de estudio. Tu reloj sigue activo registrando el tiempo extra.`;
        bodyDiv.appendChild(titleEl);
        bodyDiv.appendChild(descEl);

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'celebration-close';
        closeBtn.setAttribute('aria-label', 'Cerrar notificación de objetivo cumplido');
        closeBtn.textContent = '×';
        closeBtn.addEventListener('click', () => toast.remove());

        toast.appendChild(iconDiv);
        toast.appendChild(bodyDiv);
        toast.appendChild(closeBtn);
        document.body.appendChild(toast);

        launchConfetti();

        setTimeout(() => {
            if (toast.parentNode) {
                if (prefersReducedMotion()) {
                    toast.remove();
                } else {
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateY(20px)';
                    toast.style.transition = 'all 0.5s ease';
                    setTimeout(() => toast.remove(), 500);
                }
            }
        }, 10000);
    }

    function launchConfetti() {
        if (prefersReducedMotion()) return;

        const canvas = document.createElement('canvas');
        canvas.setAttribute('aria-hidden', 'true');
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100vw';
        canvas.style.height = '100vh';
        canvas.style.pointerEvents = 'none';
        canvas.style.zIndex = '9998';
        document.body.appendChild(canvas);

        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const particles = [];
        const colors = ['#38bdf8', '#2dd4bf', '#fbbf24', '#fb7185', '#a855f7', '#0369a1'];

        for (let i = 0; i < 65; i++) {
            particles.push({
                x: canvas.width / 2 + (Math.random() - 0.5) * 300,
                y: canvas.height * 0.4,
                vx: (Math.random() - 0.5) * 12,
                vy: (Math.random() - 0.8) * 12,
                size: Math.random() * 8 + 4,
                color: colors[Math.floor(Math.random() * colors.length)],
                rotation: Math.random() * 360,
                rotationSpeed: (Math.random() - 0.5) * 10,
                opacity: 1
            });
        }

        const start = Date.now();

        function render() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let active = false;

            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                p.vy += 0.35;
                p.rotation += p.rotationSpeed;
                p.opacity -= 0.009;

                if (p.opacity > 0 && p.y < canvas.height) {
                    active = true;
                    ctx.save();
                    ctx.translate(p.x, p.y);
                    ctx.rotate((p.rotation * Math.PI) / 180);
                    ctx.fillStyle = p.color;
                    ctx.globalAlpha = Math.max(0, p.opacity);
                    ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
                    ctx.restore();
                }
            });

            if (active && Date.now() - start < 4500) {
                requestAnimationFrame(render);
            } else {
                canvas.remove();
            }
        }

        render();
    }

    // Tick loop (actualiza la UI sin escribir en localStorage cada segundo)
    function tick() {
        if (state.isRunning) {
            const totalSeconds = getCurrentTotalSeconds();
            const targetSeconds = (state.targetMinutes || 0) * 60;
            if (targetSeconds > 0 && totalSeconds >= targetSeconds && !state.goalNotified) {
                state.goalNotified = true;
                saveState();
                showCelebration();
            }
        }
        updateUI();
    }

    function updateUI() {
        const totalSeconds = getCurrentTotalSeconds();
        const topbarDisplay = document.getElementById('study-timer-display');
        const topbarBtn = document.getElementById('btn-study-timer');
        const goalPill = document.getElementById('study-timer-goal-pill');

        const modalBigClock = document.getElementById('timer-modal-clock');
        const modalStatusBadge = document.getElementById('timer-status-badge');
        const progressBar = document.getElementById('timer-progress-bar');
        const progressPercent = document.getElementById('timer-progress-percent');
        const progressLabel = document.getElementById('timer-progress-label');
        const startBtn = document.getElementById('btn-timer-start-toggle');

        const formatted = formatTime(totalSeconds);
        const targetSeconds = (state.targetMinutes || 0) * 60;
        const isGoalMet = targetSeconds > 0 && totalSeconds >= targetSeconds;

        if (topbarDisplay) {
            topbarDisplay.textContent = formatted;
        }

        if (topbarBtn) {
            topbarBtn.classList.toggle('running', state.isRunning);
            topbarBtn.classList.toggle('goal-reached', isGoalMet);
            topbarBtn.title = `Modo Estudio: ${formatted} ${state.targetMinutes ? `(Meta: ${state.targetMinutes}m)` : ''}`;
        }

        if (goalPill) {
            const hasGoal = state.targetMinutes > 0;
            goalPill.classList.toggle('is-visible', hasGoal);
            if (hasGoal) {
                goalPill.textContent = isGoalMet ? 'Meta alcanzada' : `/ ${state.targetMinutes}m`;
            }
        }

        if (modalBigClock) {
            modalBigClock.textContent = formatted;
        }

        if (modalStatusBadge) {
            if (isGoalMet) {
                const overtimeMinutes = Math.floor((totalSeconds - targetSeconds) / 60);
                modalStatusBadge.className = 'timer-status-badge goal-met';
                modalStatusBadge.textContent = overtimeMinutes > 0
                    ? `Meta Cumplida (+${overtimeMinutes} min extra)`
                    : `Meta Alcanzada (${state.targetMinutes}m)`;
            } else if (state.isRunning) {
                modalStatusBadge.className = 'timer-status-badge active';
                modalStatusBadge.textContent = 'Sesión Activa';
            } else {
                modalStatusBadge.className = 'timer-status-badge';
                modalStatusBadge.textContent = 'En Pausa';
            }
        }

        if (progressBar && progressPercent) {
            if (targetSeconds > 0) {
                const pct = Math.min(100, Math.round((totalSeconds / targetSeconds) * 100));
                progressBar.style.width = pct + '%';
                progressBar.classList.toggle('gold', isGoalMet);
                progressPercent.textContent = pct + '%';
                if (progressLabel) progressLabel.textContent = `Progreso hacia meta (${state.targetMinutes} min):`;
            } else {
                progressBar.style.width = '100%';
                progressBar.classList.remove('gold');
                progressPercent.textContent = 'Libre';
                if (progressLabel) progressLabel.textContent = 'Sin meta fijada';
            }
        }

        if (startBtn) {
            if (state.isRunning) {
                startBtn.className = 'timer-btn-action btn-timer-pause';
                startBtn.innerHTML = '<span aria-hidden="true"><svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" fill="none" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg></span> Pausar';
            } else {
                startBtn.className = 'timer-btn-action btn-timer-start';
                startBtn.innerHTML = '<span aria-hidden="true"><svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg></span> Continuar';
            }
        }

        document.querySelectorAll('.timer-chip').forEach(chip => {
            const min = parseInt(chip.dataset.minutes, 10);
            const active = min === state.targetMinutes;
            chip.classList.toggle('active', active);
            chip.setAttribute('aria-pressed', active ? 'true' : 'false');
        });
    }

    function getModalFocusables(modal) {
        if (window.Py2JavaA11y && typeof window.Py2JavaA11y.getFocusableElements === 'function') {
            return window.Py2JavaA11y.getFocusableElements(modal);
        }
        return Array.from(modal.querySelectorAll(
            'button:not([disabled]), input:not([disabled]), a[href], select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        ));
    }

    function isModalOpen() {
        const modal = document.getElementById('study-timer-modal');
        return Boolean(modal && modal.classList.contains('open') && !modal.hidden);
    }

    function openModal() {
        buildModal();
        const modal = document.getElementById('study-timer-modal');
        const topbarBtn = document.getElementById('btn-study-timer');
        if (!modal) return;

        lastFocusedBeforeModal = document.activeElement instanceof HTMLElement ? document.activeElement : topbarBtn;
        modal.hidden = false;
        // Force reflow so opacity/transform transitions work smoothly when motion is allowed
        void modal.offsetWidth;
        modal.classList.add('open');
        if (topbarBtn) topbarBtn.setAttribute('aria-expanded', 'true');
        updateUI();

        const focusables = getModalFocusables(modal);
        const preferred = document.getElementById('btn-timer-start-toggle') || focusables[0];
        if (preferred) preferred.focus();
    }

    function closeModal(returnFocus) {
        const modal = document.getElementById('study-timer-modal');
        const topbarBtn = document.getElementById('btn-study-timer');
        if (!modal) return;

        modal.classList.remove('open');
        modal.hidden = true;
        if (topbarBtn) topbarBtn.setAttribute('aria-expanded', 'false');

        if (returnFocus) {
            const target = (lastFocusedBeforeModal && document.body.contains(lastFocusedBeforeModal))
                ? lastFocusedBeforeModal
                : topbarBtn;
            if (target && typeof target.focus === 'function') {
                target.focus();
            }
        }
    }

    function toggleRunning() {
        commitElapsed();
        state.isRunning = !state.isRunning;
        state.runningSinceMs = state.isRunning ? Date.now() : null;
        saveState();
        updateUI();
    }

    // Build the Accessible Dialog Modal
    function buildModal() {
        if (document.getElementById('study-timer-modal')) return;

        const modal = document.createElement('div');
        modal.id = 'study-timer-modal';
        modal.className = 'study-timer-modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-labelledby', 'timer-modal-title');
        modal.hidden = true;
        modal.innerHTML = `
            <div class="timer-modal-header">
                <h2 class="timer-modal-title" id="timer-modal-title">
                    <span aria-hidden="true"><svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg></span>
                    <span>Modo Estudio</span>
                </h2>
                <button type="button" class="timer-modal-close" id="btn-close-timer-modal" aria-label="Cerrar cronómetro de estudio">&times;</button>
            </div>

            <div class="timer-clock-area">
                <div class="timer-big-clock" id="timer-modal-clock" aria-live="off">00:00</div>
                <div class="timer-status-badge active" id="timer-status-badge" role="status" aria-live="polite">Sesión Activa</div>
            </div>

            <div class="timer-progress-wrap">
                <div class="timer-progress-labels">
                    <span id="timer-progress-label">Progreso hacia meta (25 min):</span>
                    <span id="timer-progress-percent" class="timer-progress-percent">0%</span>
                </div>
                <div class="timer-progress-bar-bg">
                    <div class="timer-progress-bar-fill" id="timer-progress-bar"></div>
                </div>
            </div>

            <div class="timer-controls-row">
                <button type="button" class="timer-btn-action btn-timer-pause" id="btn-timer-start-toggle">
                    <span aria-hidden="true"><svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" fill="none" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg></span> Pausar
                </button>
                <button type="button" class="timer-btn-action btn-timer-reset" id="btn-timer-reset" title="Reiniciar tiempo">
                    Reiniciar
                </button>
            </div>

            <div class="timer-presets-section">
                <div class="timer-section-label" id="timer-presets-label">Fijar Meta de Estudio</div>
                <div class="timer-preset-chips" role="group" aria-labelledby="timer-presets-label">
                    <button type="button" class="timer-chip" data-minutes="15" aria-pressed="false">15 min</button>
                    <button type="button" class="timer-chip active" data-minutes="25" aria-pressed="true">25 min (Pomodoro)</button>
                    <button type="button" class="timer-chip" data-minutes="45" aria-pressed="false">45 min</button>
                    <button type="button" class="timer-chip" data-minutes="60" aria-pressed="false">60 min (1h)</button>
                    <button type="button" class="timer-chip" data-minutes="90" aria-pressed="false">90 min</button>
                </div>

                <div class="timer-custom-goal">
                    <label for="timer-custom-input" class="sr-only">Minutos personalizados de estudio</label>
                    <input type="number" id="timer-custom-input" class="timer-custom-input" placeholder="Minutos personalizados..." min="1" max="600">
                    <button type="button" id="btn-set-custom-goal" class="timer-btn-set-goal">Fijar</button>
                </div>

                <div class="timer-sound-row">
                    <span>Sonido al completar:</span>
                    <button type="button" id="btn-toggle-sound" class="timer-sound-toggle" aria-pressed="true">
                        <span id="sound-icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg></span> <span id="sound-text">Activado</span>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        document.getElementById('btn-close-timer-modal').addEventListener('click', () => {
            closeModal(true);
        });

        document.getElementById('btn-timer-start-toggle').addEventListener('click', toggleRunning);

        document.getElementById('btn-timer-reset').addEventListener('click', () => {
            if (confirm('¿Deseas reiniciar el contador de estudio a 0?')) {
                state.accumulatedSeconds = 0;
                state.runningSinceMs = state.isRunning ? Date.now() : null;
                state.goalNotified = false;
                saveState();
                updateUI();
            }
        });

        modal.querySelectorAll('.timer-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const min = parseInt(chip.dataset.minutes, 10);
                state.targetMinutes = min;
                state.goalNotified = (getCurrentTotalSeconds() >= min * 60);
                saveState();
                updateUI();
            });
        });

        document.getElementById('btn-set-custom-goal').addEventListener('click', () => {
            const input = document.getElementById('timer-custom-input');
            const val = parseInt(input.value, 10);
            if (val && val > 0 && val <= 600) {
                state.targetMinutes = val;
                state.goalNotified = (getCurrentTotalSeconds() >= val * 60);
                saveState();
                updateUI();
                input.value = '';
            }
        });

        const soundBtn = document.getElementById('btn-toggle-sound');
        const soundIcon = document.getElementById('sound-icon');
        const soundText = document.getElementById('sound-text');

        function updateSoundUI() {
            soundIcon.innerHTML = state.soundEnabled
                ? '<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>'
                : '<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2"><path d="M13.73 21a2 2 0 0 1-3.46 0"></path><path d="M18.63 13A17.88 17.88 0 0 1 18 8"></path><path d="M6.26 6.26A5.86 5.86 0 0 0 6 8c0 7-3 9-3 9h14"></path><path d="M18 8a6 6 0 0 0-9.33-5"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>';
            soundText.textContent = state.soundEnabled ? 'Activado' : 'Silenciado';
            soundBtn.setAttribute('aria-pressed', state.soundEnabled ? 'true' : 'false');
        }

        soundBtn.addEventListener('click', () => {
            state.soundEnabled = !state.soundEnabled;
            saveState();
            updateSoundUI();
            if (state.soundEnabled) playChime();
        });

        // Trampa de foco y tecla Escape dentro del diálogo
        modal.addEventListener('keydown', (e) => {
            if (!isModalOpen()) return;
            if (window.Py2JavaA11y && typeof window.Py2JavaA11y.trapFocusKeydown === 'function') {
                window.Py2JavaA11y.trapFocusKeydown(e, modal, () => closeModal(true));
                return;
            }
            if (e.key === 'Escape') {
                e.preventDefault();
                closeModal(true);
                return;
            }
            if (e.key === 'Tab') {
                const focusables = getModalFocusables(modal);
                if (!focusables.length) return;
                const first = focusables[0];
                const last = focusables[focusables.length - 1];
                if (e.shiftKey && (document.activeElement === first || !modal.contains(document.activeElement))) {
                    e.preventDefault();
                    last.focus();
                } else if (!e.shiftKey && (document.activeElement === last || !modal.contains(document.activeElement))) {
                    e.preventDefault();
                    first.focus();
                }
            }
        });

        updateSoundUI();
    }

    function toggleModal() {
        if (isModalOpen()) {
            closeModal(true);
        } else {
            openModal();
        }
    }

    function init() {
        loadState();
        buildModal();

        const topbarBtn = document.getElementById('btn-study-timer');
        if (topbarBtn) {
            topbarBtn.setAttribute('aria-expanded', 'false');
            topbarBtn.setAttribute('aria-controls', 'study-timer-modal');
            topbarBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleModal();
            });
        }

        const mobileTimerBtn = document.getElementById('btn-study-timer-mobile');
        if (mobileTimerBtn) {
            mobileTimerBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const sb = document.getElementById('main-sidebar');
                const ov = document.getElementById('mobile-overlay');
                const mt = document.getElementById('mobile-menu-toggle');
                if (sb) sb.classList.remove('active');
                if (ov) ov.style.display = 'none';
                if (mt) mt.setAttribute('aria-expanded', 'false');
                toggleModal();
            });
        }

        // Cerrar al hacer clic fuera
        document.addEventListener('click', (e) => {
            const modal = document.getElementById('study-timer-modal');
            const btn = document.getElementById('btn-study-timer');
            const mbtn = document.getElementById('btn-study-timer-mobile');
            if (isModalOpen() && modal && !modal.contains(e.target) && (!btn || !btn.contains(e.target)) && (!mbtn || !mbtn.contains(e.target))) {
                closeModal(false);
            }
        });

        // Cerrar con Escape aunque el foco haya salido momentáneamente del diálogo
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isModalOpen()) {
                e.preventDefault();
                closeModal(true);
            }
        });

        // Guardar estado por delta de timestamps al cambiar visibilidad o salir de la página
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                saveState();
            } else {
                updateUI();
            }
        });
        window.addEventListener('beforeunload', saveState);
        window.addEventListener('pagehide', saveState);

        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(tick, 1000);
        updateUI();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.StudyTimer = {
        getState: () => ({ ...state, accumulatedSeconds: getCurrentTotalSeconds() }),
        setGoal: (minutes) => {
            state.targetMinutes = minutes;
            state.goalNotified = false;
            saveState();
            updateUI();
        },
        toggle: toggleRunning
    };
})();
