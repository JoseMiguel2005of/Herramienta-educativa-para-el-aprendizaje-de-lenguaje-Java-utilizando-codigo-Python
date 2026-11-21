// accessibility.js — Panel de Accesibilidad Universal (WCAG 2.1 AA/AAA)
(function () {
    const STORAGE_KEY = 'py2java_a11y';
    const DEFAULTS = {
        textSize: 'md',   // 'md' | 'lg' | 'xl'
        contrast: 'normal', // 'normal' | 'high'
        dyslexia: false,  // boolean
        motion: 'auto'    // 'auto' | 'reduce'
    };

    function loadPrefs() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return { ...DEFAULTS };
            return { ...DEFAULTS, ...JSON.parse(raw) };
        } catch {
            return { ...DEFAULTS };
        }
    }

    function savePrefs(prefs) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
        } catch {
            // Storage unavailable
        }
    }

    function applyPrefs(prefs) {
        const html = document.documentElement;
        if (prefs.textSize && prefs.textSize !== 'md') {
            html.setAttribute('data-a11y-text', prefs.textSize);
        } else {
            html.removeAttribute('data-a11y-text');
        }

        if (prefs.contrast === 'high') {
            html.setAttribute('data-a11y-contrast', 'high');
        } else {
            html.removeAttribute('data-a11y-contrast');
        }

        if (prefs.dyslexia) {
            html.setAttribute('data-a11y-dyslexia', 'true');
        } else {
            html.removeAttribute('data-a11y-dyslexia');
        }

        if (prefs.motion === 'reduce') {
            html.setAttribute('data-a11y-motion', 'reduce');
        } else {
            html.removeAttribute('data-a11y-motion');
        }
    }

    function announce(message) {
        const region = document.getElementById('a11y-announcer');
        if (!region) return;
        region.textContent = '';
        requestAnimationFrame(() => {
            region.textContent = message;
        });
    }

    // Aplicar de inmediato para evitar parpadeos
    const initialPrefs = loadPrefs();
    applyPrefs(initialPrefs);

    document.addEventListener('DOMContentLoaded', () => {
        let prefs = loadPrefs();
        applyPrefs(prefs);

        const toggleBtn = document.getElementById('btn-a11y-toggle');
        const panel = document.getElementById('a11y-panel');
        const closeBtn = document.getElementById('btn-a11y-close');
        const resetBtn = document.getElementById('btn-a11y-reset');

        if (!toggleBtn || !panel) return;

        function syncUI() {
            const hasCustom =
                prefs.textSize !== 'md' ||
                prefs.contrast === 'high' ||
                prefs.dyslexia ||
                prefs.motion === 'reduce';

            toggleBtn.classList.toggle('has-active-a11y', hasCustom);

            panel.querySelectorAll('[data-a11y-text-opt]').forEach(btn => {
                const isSelected = btn.dataset.a11yTextOpt === prefs.textSize;
                btn.setAttribute('aria-pressed', isSelected ? 'true' : 'false');
            });

            const contrastBtn = document.getElementById('a11y-opt-contrast');
            if (contrastBtn) {
                const on = prefs.contrast === 'high';
                contrastBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
                const state = contrastBtn.querySelector('.a11y-switch-state');
                if (state) state.textContent = on ? 'Activado' : 'Inactivo';
            }

            const dyslexiaBtn = document.getElementById('a11y-opt-dyslexia');
            if (dyslexiaBtn) {
                const on = Boolean(prefs.dyslexia);
                dyslexiaBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
                const state = dyslexiaBtn.querySelector('.a11y-switch-state');
                if (state) state.textContent = on ? 'Activado' : 'Inactivo';
            }

            const motionBtn = document.getElementById('a11y-opt-motion');
            if (motionBtn) {
                const on = prefs.motion === 'reduce';
                motionBtn.setAttribute('aria-pressed', on ? 'true' : 'false');
                const state = motionBtn.querySelector('.a11y-switch-state');
                if (state) state.textContent = on ? 'Activado' : 'Inactivo';
            }
        }

        function openPanel() {
            panel.hidden = false;
            toggleBtn.setAttribute('aria-expanded', 'true');
            const firstFocusable = panel.querySelector('button');
            if (firstFocusable) firstFocusable.focus();
        }

        function closePanel(returnFocus) {
            panel.hidden = true;
            toggleBtn.setAttribute('aria-expanded', 'false');
            if (returnFocus) toggleBtn.focus();
        }

        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (panel.hidden) {
                openPanel();
            } else {
                closePanel(false);
            }
        });

        if (closeBtn) {
            closeBtn.addEventListener('click', () => closePanel(true));
        }

        document.addEventListener('click', (e) => {
            if (!panel.hidden && !panel.contains(e.target) && !toggleBtn.contains(e.target)) {
                closePanel(false);
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !panel.hidden) {
                closePanel(true);
            }
        });

        panel.querySelectorAll('[data-a11y-text-opt]').forEach(btn => {
            btn.addEventListener('click', () => {
                prefs.textSize = btn.dataset.a11yTextOpt;
                applyPrefs(prefs);
                savePrefs(prefs);
                syncUI();
                const labels = { md: 'Normal (100%)', lg: 'Grande (112%)', xl: 'Muy grande (125%)' };
                announce('Tamaño de texto cambiado a ' + (labels[prefs.textSize] || prefs.textSize));
            });
        });

        const contrastBtn = document.getElementById('a11y-opt-contrast');
        if (contrastBtn) {
            contrastBtn.addEventListener('click', () => {
                prefs.contrast = prefs.contrast === 'high' ? 'normal' : 'high';
                applyPrefs(prefs);
                savePrefs(prefs);
                syncUI();
                announce(prefs.contrast === 'high' ? 'Modo alto contraste activado' : 'Modo alto contraste desactivado');
            });
        }

        const dyslexiaBtn = document.getElementById('a11y-opt-dyslexia');
        if (dyslexiaBtn) {
            dyslexiaBtn.addEventListener('click', () => {
                prefs.dyslexia = !prefs.dyslexia;
                applyPrefs(prefs);
                savePrefs(prefs);
                syncUI();
                announce(prefs.dyslexia ? 'Modo lectura fácil para dislexia activado' : 'Modo lectura fácil desactivado');
            });
        }

        const motionBtn = document.getElementById('a11y-opt-motion');
        if (motionBtn) {
            motionBtn.addEventListener('click', () => {
                prefs.motion = prefs.motion === 'reduce' ? 'auto' : 'reduce';
                applyPrefs(prefs);
                savePrefs(prefs);
                syncUI();
                announce(prefs.motion === 'reduce' ? 'Animaciones reducidas activadas' : 'Animaciones estándar activadas');
            });
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                prefs = { ...DEFAULTS };
                applyPrefs(prefs);
                savePrefs(prefs);
                syncUI();
                announce('Preferencias de accesibilidad restablecidas');
            });
        }

        syncUI();
    });

    window.Py2JavaA11y = { loadPrefs, applyPrefs };
})();
