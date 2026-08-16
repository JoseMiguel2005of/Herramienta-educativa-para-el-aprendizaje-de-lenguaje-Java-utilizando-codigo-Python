/**
 * Py2Java Focus Study Timer (Temporizador / Cronómetro de Estudio)
 * Permite a los estudiantes fijar una meta de estudio (ej. 60 min),
 * seguir su tiempo de estudio de forma no invasiva entre páginas,
 * reproducir un sonido/celebración al alcanzar la meta y continuar
 * cronometrando el tiempo sin interrupciones.
 */

(function () {
    'use strict';

    const STORAGE_KEY = 'py2java_study_timer_v1';

    // Default state
    let state = {
        accumulatedSeconds: 0,
        targetMinutes: 25, // default 25 min (Pomodoro)
        isRunning: true,   // auto-starts when studying
        lastTimestamp: Date.now(),
        goalNotified: false,
        soundEnabled: true
    };

    let timerInterval = null;
    let audioCtx = null;

    // Load persisted state
    function loadState() {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                state = { ...state, ...parsed };
                
                // If it was running when navigated away, add elapsed delta
                if (state.isRunning && state.lastTimestamp) {
                    const elapsed = Math.floor((Date.now() - state.lastTimestamp) / 1000);
                    if (elapsed > 0 && elapsed < 86400) { // cap at 24 hours
                        state.accumulatedSeconds += elapsed;
                    }
                }
            }
        } catch (e) {
            console.warn('Could not load study timer state:', e);
        }
        state.lastTimestamp = Date.now();
    }

    function saveState() {
        try {
            state.lastTimestamp = Date.now();
            localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        } catch (e) {}
    }

    // Format seconds into HH:MM:SS or MM:SS
    function formatTime(totalSeconds) {
        const h = Math.floor(totalSeconds / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        const s = totalSeconds % 60;

        const pad = (n) => String(n).padStart(2, '0');
        if (h > 0) {
            return `${h}:${pad(m)}:${pad(s)}`;
        }
        return `${pad(m)}:${pad(s)}`;
    }

    // Web Audio API Synthesized Victory Chime
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

    // Celebration Toast & Mini Confetti
    function showCelebration() {
        // Play chime
        playChime();

        // Create celebration toast
        const existing = document.querySelector('.study-celebration-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'study-celebration-toast';
        toast.innerHTML = `
            <div class="celebration-icon">🎉</div>
            <div class="celebration-body">
                <h4>¡Objetivo de Estudio Cumplido!</h4>
                <p>Has alcanzado tu meta de <b>${state.targetMinutes} minutos</b> de estudio. Tu reloj sigue activo registrando el tiempo extra.</p>
            </div>
            <button class="celebration-close" aria-label="Cerrar">&times;</button>
        `;

        document.body.appendChild(toast);

        toast.querySelector('.celebration-close').addEventListener('click', () => {
            toast.remove();
        });

        // Launch lightweight confetti canvas
        launchConfetti();

        // Auto remove toast after 10 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(20px)';
                toast.style.transition = 'all 0.5s ease';
                setTimeout(() => toast.remove(), 500);
            }
        }, 10000);
    }

    // Simple, lightweight canvas confetti
    function launchConfetti() {
        const canvas = document.createElement('canvas');
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
        const colors = ['#00e5ff', '#4ade80', '#f59e0b', '#ec4899', '#a855f7', '#3b82f6'];

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

        let animationFrame;
        let start = Date.now();

        function render() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let active = false;

            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                p.vy += 0.35; // gravity
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
                animationFrame = requestAnimationFrame(render);
            } else {
                canvas.remove();
            }
        }

        render();
    }

    // Tick loop (every second)
    function tick() {
        if (state.isRunning) {
            state.accumulatedSeconds += 1;
            saveState();

            const targetSeconds = (state.targetMinutes || 0) * 60;
            if (targetSeconds > 0 && state.accumulatedSeconds >= targetSeconds && !state.goalNotified) {
                state.goalNotified = true;
                saveState();
                showCelebration();
            }
        }
        updateUI();
    }

    // UI Updates
    function updateUI() {
        const topbarDisplay = document.getElementById('study-timer-display');
        const topbarBtn = document.getElementById('btn-study-timer');
        const goalPill = document.getElementById('study-timer-goal-pill');

        const modalBigClock = document.getElementById('timer-modal-clock');
        const modalStatusBadge = document.getElementById('timer-status-badge');
        const progressBar = document.getElementById('timer-progress-bar');
        const progressPercent = document.getElementById('timer-progress-percent');
        const progressLabel = document.getElementById('timer-progress-label');
        const startBtn = document.getElementById('btn-timer-start-toggle');

        const formatted = formatTime(state.accumulatedSeconds);
        const targetSeconds = (state.targetMinutes || 0) * 60;
        const isGoalMet = targetSeconds > 0 && state.accumulatedSeconds >= targetSeconds;

        // Topbar updates
        if (topbarDisplay) {
            topbarDisplay.textContent = formatted;
        }

        if (topbarBtn) {
            topbarBtn.classList.toggle('running', state.isRunning);
            topbarBtn.classList.toggle('goal-reached', isGoalMet);
            topbarBtn.title = `Modo Estudio: ${formatted} ${state.targetMinutes ? `(Meta: ${state.targetMinutes}m)` : ''}`;
        }

        if (goalPill) {
            if (state.targetMinutes > 0) {
                goalPill.style.display = 'inline';
                goalPill.textContent = isGoalMet ? `🎯 ¡Meta!` : `/ ${state.targetMinutes}m`;
            } else {
                goalPill.style.display = 'none';
            }
        }

        // Modal updates
        if (modalBigClock) {
            modalBigClock.textContent = formatted;
        }

        if (modalStatusBadge) {
            if (isGoalMet) {
                const overtimeMinutes = Math.floor((state.accumulatedSeconds - targetSeconds) / 60);
                modalStatusBadge.className = 'timer-status-badge goal-met';
                modalStatusBadge.textContent = overtimeMinutes > 0 
                    ? `🎯 ¡Meta Cumplida! (+${overtimeMinutes} min extra)` 
                    : `🎯 ¡Meta Alcanzada! (${state.targetMinutes}m)`;
            } else if (state.isRunning) {
                modalStatusBadge.className = 'timer-status-badge active';
                modalStatusBadge.textContent = '● Sesión Activa';
            } else {
                modalStatusBadge.className = 'timer-status-badge';
                modalStatusBadge.textContent = '⏸ En Pausa';
            }
        }

        if (progressBar && progressPercent) {
            if (targetSeconds > 0) {
                const pct = Math.min(100, Math.round((state.accumulatedSeconds / targetSeconds) * 100));
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
                startBtn.innerHTML = '<span>⏸</span> Pausar';
            } else {
                startBtn.className = 'timer-btn-action btn-timer-start';
                startBtn.innerHTML = '<span>▶</span> Continuar';
            }
        }

        // Active preset chips
        document.querySelectorAll('.timer-chip').forEach(chip => {
            const min = parseInt(chip.dataset.minutes);
            chip.classList.toggle('active', min === state.targetMinutes);
        });
    }

    // Build the Dropdown Modal
    function buildModal() {
        if (document.getElementById('study-timer-modal')) return;

        const modal = document.createElement('div');
        modal.id = 'study-timer-modal';
        modal.className = 'study-timer-modal';
        modal.innerHTML = `
            <div class="timer-modal-header">
                <div class="timer-modal-title">
                    <span>⏱️</span>
                    <span>Modo Estudio</span>
                </div>
                <button type="button" class="timer-modal-close" id="btn-close-timer-modal">&times;</button>
            </div>

            <div class="timer-clock-area">
                <div class="timer-big-clock" id="timer-modal-clock">00:00</div>
                <div class="timer-status-badge active" id="timer-status-badge">● Sesión Activa</div>
            </div>

            <div class="timer-progress-wrap">
                <div class="timer-progress-labels">
                    <span id="timer-progress-label">Progreso hacia meta (25 min):</span>
                    <span id="timer-progress-percent" style="font-weight:700; color:#00e5ff;">0%</span>
                </div>
                <div class="timer-progress-bar-bg">
                    <div class="timer-progress-bar-fill" id="timer-progress-bar"></div>
                </div>
            </div>

            <div class="timer-controls-row">
                <button type="button" class="timer-btn-action btn-timer-pause" id="btn-timer-start-toggle">
                    <span>⏸</span> Pausar
                </button>
                <button type="button" class="timer-btn-action btn-timer-reset" id="btn-timer-reset" title="Reiniciar tiempo">
                    <span>🔄</span> Reiniciar
                </button>
            </div>

            <div class="timer-presets-section">
                <div class="timer-section-label">Fijar Meta de Estudio</div>
                <div class="timer-preset-chips">
                    <button type="button" class="timer-chip" data-minutes="15">15 min</button>
                    <button type="button" class="timer-chip active" data-minutes="25">25 min (Pomodoro)</button>
                    <button type="button" class="timer-chip" data-minutes="45">45 min</button>
                    <button type="button" class="timer-chip" data-minutes="60">60 min (1h)</button>
                    <button type="button" class="timer-chip" data-minutes="90">90 min</button>
                </div>

                <div class="timer-custom-goal">
                    <input type="number" id="timer-custom-input" class="timer-custom-input" placeholder="Minutos personalizados..." min="1" max="600">
                    <button type="button" id="btn-set-custom-goal" class="timer-btn-set-goal">Fijar</button>
                </div>

                <div class="timer-sound-row">
                    <span>Sonido al completar:</span>
                    <button type="button" id="btn-toggle-sound" class="timer-sound-toggle">
                        <span id="sound-icon">🔔</span> <span id="sound-text">Activado</span>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Bind events
        document.getElementById('btn-close-timer-modal').addEventListener('click', () => {
            modal.classList.remove('open');
        });

        document.getElementById('btn-timer-start-toggle').addEventListener('click', () => {
            state.isRunning = !state.isRunning;
            saveState();
            updateUI();
        });

        document.getElementById('btn-timer-reset').addEventListener('click', () => {
            if (confirm('¿Deseas reiniciar el contador de estudio a 0?')) {
                state.accumulatedSeconds = 0;
                state.goalNotified = false;
                saveState();
                updateUI();
            }
        });

        // Presets
        modal.querySelectorAll('.timer-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const min = parseInt(chip.dataset.minutes);
                state.targetMinutes = min;
                state.goalNotified = (state.accumulatedSeconds >= min * 60);
                saveState();
                updateUI();
            });
        });

        // Custom goal
        document.getElementById('btn-set-custom-goal').addEventListener('click', () => {
            const val = parseInt(document.getElementById('timer-custom-input').value);
            if (val && val > 0) {
                state.targetMinutes = val;
                state.goalNotified = (state.accumulatedSeconds >= val * 60);
                saveState();
                updateUI();
                document.getElementById('timer-custom-input').value = '';
            }
        });

        // Sound toggle
        const soundBtn = document.getElementById('btn-toggle-sound');
        const soundIcon = document.getElementById('sound-icon');
        const soundText = document.getElementById('sound-text');

        function updateSoundUI() {
            soundIcon.textContent = state.soundEnabled ? '🔔' : '🔕';
            soundText.textContent = state.soundEnabled ? 'Activado' : 'Silenciado';
        }

        soundBtn.addEventListener('click', () => {
            state.soundEnabled = !state.soundEnabled;
            saveState();
            updateSoundUI();
            if (state.soundEnabled) playChime(); // quick test chime
        });

        updateSoundUI();
    }

    // Toggle modal visibility
    function toggleModal() {
        buildModal();
        const modal = document.getElementById('study-timer-modal');
        if (modal) {
            modal.classList.toggle('open');
            updateUI();
        }
    }

    // Initialize on DOM ready
    function init() {
        loadState();
        buildModal();

        // Topbar button
        const topbarBtn = document.getElementById('btn-study-timer');
        if (topbarBtn) {
            topbarBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleModal();
            });
        }

        // Close on outside click
        document.addEventListener('click', (e) => {
            const modal = document.getElementById('study-timer-modal');
            const topbarBtn = document.getElementById('btn-study-timer');
            if (modal && modal.classList.contains('open')) {
                if (!modal.contains(e.target) && (!topbarBtn || !topbarBtn.contains(e.target))) {
                    modal.classList.remove('open');
                }
            }
        });

        // Start tick interval
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(tick, 1000);
        updateUI();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Export API
    window.StudyTimer = {
        getState: () => ({ ...state }),
        setGoal: (minutes) => {
            state.targetMinutes = minutes;
            state.goalNotified = false;
            saveState();
            updateUI();
        },
        toggle: () => {
            state.isRunning = !state.isRunning;
            saveState();
            updateUI();
        }
    };
})();
