// search.js - Lógica de Búsqueda Global

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('search-modal');
    const input = document.getElementById('global-search-input');
    const resultsContainer = document.getElementById('search-results');
    const btnOpen = document.getElementById('btn-open-search');
    const btnClose = document.getElementById('btn-close-search');

    if (!modal || !input) return;

    function openSearch() {
        modal.style.display = 'flex';
        // Animación suave de entrada (si el CSS lo soporta)
        modal.style.opacity = '1';
        setTimeout(() => input.focus(), 100);
    }

    function closeSearch() {
        modal.style.display = 'none';
    }

    if (btnOpen) btnOpen.addEventListener('click', openSearch);
    if (btnClose) btnClose.addEventListener('click', closeSearch);

    // Clic fuera del modal para cerrar
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeSearch();
        }
    });

    // Atajo Ctrl+K
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            openSearch();
        }
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            closeSearch();
        }
    });

    function renderSearchMessage(text, color) {
        resultsContainer.textContent = '';
        const p = document.createElement('p');
        p.style.textAlign = 'center';
        p.style.padding = '2rem 1rem';
        if (color) p.style.color = color;
        p.textContent = text;
        resultsContainer.appendChild(p);
    }

    let debounceTimer;
    input.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            renderSearchMessage('Escribe al menos 2 caracteres...', '#888');
            return;
        }

        debounceTimer = setTimeout(() => {
            renderSearchMessage('Buscando...', null);
            fetch(`/api/buscar?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    resultsContainer.textContent = '';
                    if (!Array.isArray(data) || data.length === 0) {
                        renderSearchMessage(`No se encontraron resultados para "${query}".`, '#888');
                        return;
                    }
                    
                    data.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'search-result-item';
                        
                        const link = document.createElement('a');
                        link.href = `/leccion/${encodeURIComponent(String(item.id || ''))}`;
                        link.className = 'search-result-link';

                        const titleEl = document.createElement('h4');
                        titleEl.className = 'search-result-title';
                        titleEl.textContent = String(item.title || '');

                        const snippetEl = document.createElement('p');
                        snippetEl.className = 'search-result-snippet';
                        // Quitar etiquetas HTML del snippet por estética; textContent impide inyección HTML
                        const cleanSnippet = String(item.snippet || '').replace(/<[^>]*>?/gm, '');
                        snippetEl.textContent = cleanSnippet;

                        link.appendChild(titleEl);
                        link.appendChild(snippetEl);
                        div.appendChild(link);
                        resultsContainer.appendChild(div);
                    });
                })
                .catch(err => {
                    console.error('Search error:', err);
                    renderSearchMessage('Ocurrió un error en la búsqueda.', '#ef5350');
                });
        }, 300);
    });
});
