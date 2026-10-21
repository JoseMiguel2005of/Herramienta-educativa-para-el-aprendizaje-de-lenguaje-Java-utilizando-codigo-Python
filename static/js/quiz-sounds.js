/**
 * quiz-sounds.js
 * Sonidos sintetizados (Web Audio API) para respuestas correctas e incorrectas.
 * - Correcto: dos notas ascendentes, brillantes y cortas.
 * - Incorrecto: dos notas descendentes, suaves y graves (tono "amable", no un zumbido).
 * Respeta el interruptor de sonido del temporizador de estudio.
 */
(function () {
    'use strict';

    const TIMER_STORAGE_KEY = 'py2java_study_timer_v1';
    let ctx = null;

    function soundEnabled() {
        try {
            const saved = JSON.parse(localStorage.getItem(TIMER_STORAGE_KEY) || '{}');
            return saved.soundEnabled !== false;
        } catch (e) {
            return true;
        }
    }

    function getContext() {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return null;
        if (!ctx) ctx = new AC();
        if (ctx.state === 'suspended') ctx.resume();
        return ctx;
    }

    function playNotes(notes, type, peakGain) {
        if (!soundEnabled()) return;
        try {
            const audio = getContext();
            if (!audio) return;
            const now = audio.currentTime;

            notes.forEach(function (n) {
                const osc = audio.createOscillator();
                const gain = audio.createGain();
                const start = now + n.time;

                osc.type = type;
                osc.frequency.setValueAtTime(n.freq, start);

                gain.gain.setValueAtTime(0.0001, start);
                gain.gain.linearRampToValueAtTime(peakGain, start + 0.03);
                gain.gain.exponentialRampToValueAtTime(0.0001, start + n.dur);

                osc.connect(gain);
                gain.connect(audio.destination);
                osc.start(start);
                osc.stop(start + n.dur + 0.05);
            });
        } catch (e) {
            console.warn('Quiz sound error:', e);
        }
    }

    window.QuizSounds = {
        playCorrect: function () {
            playNotes([
                { freq: 659.25, time: 0,    dur: 0.25 }, // E5
                { freq: 987.77, time: 0.12, dur: 0.45 }  // B5
            ], 'sine', 0.22);
        },
        playWrong: function () {
            playNotes([
                { freq: 392.00, time: 0,    dur: 0.25 }, // G4
                { freq: 293.66, time: 0.14, dur: 0.45 }  // D4
            ], 'sine', 0.16);
        },
        play: function (isCorrect) {
            if (isCorrect) this.playCorrect(); else this.playWrong();
        }
    };
})();
