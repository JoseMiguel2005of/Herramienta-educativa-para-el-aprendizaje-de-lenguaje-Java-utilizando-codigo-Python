/**
 * Evaluation Engine
 * Handles adaptive evaluation flow: start, questions, timer, scoring, results
 */
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('eval-container');
    if (!container) return;

    const sectionKey = container.dataset.sectionKey;
    const totalQuestions = parseInt(container.dataset.total);
    const timeLimit = parseInt(container.dataset.timeLimit);
    const passingScore = parseInt(container.dataset.passingScore);

    // Screens
    const startScreen = document.getElementById('eval-start');
    const activeScreen = document.getElementById('eval-active');
    const resultsScreen = document.getElementById('eval-results');

    // Buttons
    const btnStart = document.getElementById('btn-start-eval');
    const btnPrev = document.getElementById('btn-eval-prev');
    const btnNext = document.getElementById('btn-eval-next');
    const btnSubmit = document.getElementById('btn-eval-submit');
    const btnRetry = document.getElementById('btn-eval-retry');

    // Progress
    const counterEl = document.getElementById('eval-counter');
    const answeredEl = document.getElementById('eval-answered');
    const progressFill = document.getElementById('eval-progress-fill');
    const timerValue = document.getElementById('timer-value');
    const timerEl = document.getElementById('eval-timer');

    // State
    let currentQuestion = 0;
    let answers = {};
    let timerInterval = null;
    let secondsRemaining = timeLimit;
    let startTime = null;

    // ===== START =====
    btnStart.addEventListener('click', () => {
        startScreen.hidden = true;
        activeScreen.hidden = false;
        startTime = Date.now();
        startTimer();
        showQuestion(0);
    });

    // ===== TIMER =====
    function startTimer() {
        secondsRemaining = timeLimit;
        updateTimerDisplay();
        timerInterval = setInterval(() => {
            secondsRemaining--;
            updateTimerDisplay();

            if (secondsRemaining <= 60) {
                timerEl.classList.add('danger');
                timerEl.classList.remove('warning');
            } else if (secondsRemaining <= 300) {
                timerEl.classList.add('warning');
            }

            if (secondsRemaining <= 0) {
                clearInterval(timerInterval);
                submitEvaluation();
            }
        }, 1000);
    }

    function updateTimerDisplay() {
        const mins = Math.floor(secondsRemaining / 60);
        const secs = secondsRemaining % 60;
        timerValue.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // ===== QUESTION NAVIGATION =====
    function showQuestion(idx) {
        currentQuestion = idx;

        // Hide all slides, show current
        document.querySelectorAll('.eval-question-slide').forEach((slide, i) => {
            slide.hidden = (i !== idx);
        });

        // Update counter
        counterEl.textContent = `Pregunta ${idx + 1} de ${totalQuestions}`;
        progressFill.style.width = `${((idx + 1) / totalQuestions) * 100}%`;

        // Update dots
        document.querySelectorAll('.dot-btn').forEach((dot, i) => {
            dot.classList.toggle('active', i === idx);
        });

        // Update nav buttons
        btnPrev.disabled = (idx === 0);

        if (idx === totalQuestions - 1) {
            btnNext.hidden = true;
            btnSubmit.hidden = false;
        } else {
            btnNext.hidden = false;
            btnSubmit.hidden = true;
        }

        updateAnsweredCount();
    }

    btnNext.addEventListener('click', () => {
        if (currentQuestion < totalQuestions - 1) {
            showQuestion(currentQuestion + 1);
        }
    });

    btnPrev.addEventListener('click', () => {
        if (currentQuestion > 0) {
            showQuestion(currentQuestion - 1);
        }
    });

    // Dot navigation
    document.querySelectorAll('.dot-btn').forEach(dot => {
        dot.addEventListener('click', () => {
            showQuestion(parseInt(dot.dataset.idx));
        });
    });

    // ===== ANSWER HANDLING =====

    // Multiple choice - radio change
    document.querySelectorAll('.eval-options-list input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const slide = radio.closest('.eval-question-slide');
            const qid = slide.dataset.qid;
            answers[qid] = parseInt(radio.value);
            markDotAnswered(parseInt(slide.dataset.question));
            updateAnsweredCount();
        });
    });

    // Complete code - input
    document.querySelectorAll('.eval-code-input').forEach(input => {
        input.addEventListener('input', () => {
            const slide = input.closest('.eval-question-slide');
            const qid = slide.dataset.qid;
            answers[qid] = input.value.trim();
            if (input.value.trim()) {
                markDotAnswered(parseInt(slide.dataset.question));
            }
            updateAnsweredCount();
        });
    });

    // True/False buttons
    document.querySelectorAll('.eval-tf-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const slide = btn.closest('.eval-question-slide');
            const qid = slide.dataset.qid;
            const value = btn.dataset.value === 'true';

            // Deselect siblings
            slide.querySelectorAll('.eval-tf-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');

            answers[qid] = value;
            markDotAnswered(parseInt(slide.dataset.question));
            updateAnsweredCount();
        });
    });

    function markDotAnswered(idx) {
        const dot = document.querySelector(`.dot-btn[data-idx="${idx}"]`);
        if (dot) dot.classList.add('answered');
    }

    function updateAnsweredCount() {
        const count = Object.keys(answers).length;
        answeredEl.textContent = `${count} respondidas`;
    }

    // ===== SUBMIT =====
    btnSubmit.addEventListener('click', () => {
        const unanswered = totalQuestions - Object.keys(answers).length;
        if (unanswered > 0) {
            if (!confirm(`Tienes ${unanswered} pregunta(s) sin responder. ¿Deseas enviar de todas formas?`)) {
                return;
            }
        }
        submitEvaluation();
    });

    function submitEvaluation() {
        clearInterval(timerInterval);
        const timeTaken = Math.round((Date.now() - startTime) / 1000);

        // Disable submit button
        btnSubmit.disabled = true;
        btnSubmit.textContent = 'Enviando...';

        fetch('/api/evaluacion/resultado', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section_key: sectionKey,
                answers: answers,
                time_taken: timeTaken,
            }),
        })
        .then(res => res.json())
        .then(data => {
            if (data.ok) {
                showResults(data);
            } else {
                alert('Error: ' + (data.error || 'No se pudo procesar la evaluación'));
                btnSubmit.disabled = false;
                btnSubmit.textContent = 'Enviar Evaluación';
            }
        })
        .catch(err => {
            console.error('Error:', err);
            alert('Error de conexión. Intenta de nuevo.');
            btnSubmit.disabled = false;
            btnSubmit.textContent = 'Enviar Evaluación';
        });
    }

    // ===== RESULTS =====
    function showResults(data) {
        activeScreen.hidden = true;
        resultsScreen.hidden = false;

        const { score, total, percentage, passed, xp_gained, attempt_number, details } = data;

        // Status badge
        const statusEl = document.getElementById('eval-results-status');
        if (passed) {
            statusEl.innerHTML = '<span class="eval-status-passed">EVALUACIÓN APROBADA</span>';
        } else {
            statusEl.innerHTML = '<span class="eval-status-failed">NO APROBADO</span>';
        }

        // Title
        const titleEl = document.getElementById('eval-results-title');
        titleEl.textContent = passed
            ? '¡Excelente Trabajo! Has demostrado tu dominio'
            : 'Sigue practicando para mejorar tu puntaje';

        // Score circle
        const scoreFill = document.getElementById('eval-score-fill');
        const scoreText = document.getElementById('eval-score-text');
        const circumference = 2 * Math.PI * 54;
        const offset = circumference - (percentage / 100) * circumference;

        scoreFill.classList.toggle('passed', passed);
        scoreFill.classList.toggle('failed', !passed);

        setTimeout(() => {
            scoreFill.style.strokeDashoffset = offset;
            animateNumber(scoreText, 0, Math.round(percentage), 1500);
        }, 200);

        // Detail text
        document.getElementById('eval-results-detail').textContent =
            `Respondiste correctamente ${score} de ${total} preguntas (Intento #${attempt_number})`;

        // XP badge
        if (xp_gained > 0) {
            const xpBadge = document.getElementById('eval-xp-badge');
            xpBadge.hidden = false;
            document.getElementById('eval-xp-text').textContent = `+${xp_gained} XP`;
        }

        // Breakdown table
        const breakdownTable = document.getElementById('breakdown-table');
        breakdownTable.innerHTML = '';

        if (details) {
            const sortedDetails = Object.entries(details).sort((a, b) => {
                const pctA = a[1].total > 0 ? (a[1].correct / a[1].total) * 100 : 0;
                const pctB = b[1].total > 0 ? (b[1].correct / b[1].total) * 100 : 0;
                return pctA - pctB; // Worst first
            });

            for (const [lessonId, info] of sortedDetails) {
                const pct = info.total > 0 ? Math.round((info.correct / info.total) * 100) : 0;
                const colorClass = pct >= 70 ? 'good' : pct >= 40 ? 'okay' : 'bad';

                const row = document.createElement('div');
                row.className = 'breakdown-row';
                row.innerHTML = `
                    <span class="breakdown-lesson">${info.lesson_title || lessonId}</span>
                    <span class="breakdown-score ${colorClass}">${info.correct}/${info.total}</span>
                    <div class="breakdown-bar-wrap">
                        <div class="breakdown-bar-fill ${colorClass}" style="width: 0%"></div>
                    </div>
                    <a href="/leccion/${lessonId}" class="breakdown-link">Repasar →</a>
                `;
                breakdownTable.appendChild(row);

                // Animate bar
                setTimeout(() => {
                    row.querySelector('.breakdown-bar-fill').style.width = `${pct}%`;
                }, 300);
            }
        }

        // Confetti if passed
        if (passed) {
            launchConfetti();
        }
    }

    // ===== ANIMATE NUMBER =====
    function animateNumber(el, start, end, duration) {
        const range = end - start;
        const startTimestamp = Date.now();

        function step() {
            const elapsed = Date.now() - startTimestamp;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            const current = Math.round(start + range * eased);
            el.textContent = `${current}%`;

            if (progress < 1) {
                requestAnimationFrame(step);
            }
        }
        requestAnimationFrame(step);
    }

    // ===== CONFETTI =====
    function launchConfetti() {
        const canvas = document.getElementById('confetti-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const particles = [];
        const colors = ['#00e5ff', '#0088ff', '#00c864', '#ffd700', '#ff6b6b', '#a855f7'];

        for (let i = 0; i < 150; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height - canvas.height,
                w: Math.random() * 10 + 5,
                h: Math.random() * 6 + 3,
                color: colors[Math.floor(Math.random() * colors.length)],
                speed: Math.random() * 3 + 2,
                angle: Math.random() * Math.PI * 2,
                spin: (Math.random() - 0.5) * 0.2,
                opacity: 1,
            });
        }

        let frame = 0;
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            frame++;

            particles.forEach(p => {
                p.y += p.speed;
                p.x += Math.sin(p.angle) * 1.5;
                p.angle += p.spin;

                if (frame > 120) {
                    p.opacity -= 0.01;
                }

                ctx.save();
                ctx.globalAlpha = Math.max(0, p.opacity);
                ctx.translate(p.x, p.y);
                ctx.rotate(p.angle);
                ctx.fillStyle = p.color;
                ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
                ctx.restore();
            });

            if (frame < 250 && particles.some(p => p.opacity > 0)) {
                requestAnimationFrame(animate);
            } else {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
            }
        }
        animate();
    }

    // ===== RETRY =====
    btnRetry.addEventListener('click', () => {
        window.location.reload();
    });
});
