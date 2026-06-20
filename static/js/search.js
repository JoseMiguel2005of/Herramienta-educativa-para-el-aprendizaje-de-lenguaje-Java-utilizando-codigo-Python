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

    let debounceTimer;
    input.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            resultsContainer.innerHTML = '<p style="color:#888; text-align:center; padding:2rem 1rem;">Escribe al menos 2 caracteres...</p>';
            return;
        }

        debounceTimer = setTimeout(() => {
            resultsContainer.innerHTML = '<p style="text-align:center; padding:2rem 1rem;">Buscando...</p>';
            fetch(`/api/buscar?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    resultsContainer.innerHTML = '';
                    if (data.length === 0) {
                        resultsContainer.innerHTML = '<p style="color:#888; text-align:center; padding:2rem 1rem;">No se encontraron resultados para "'+ query +'".</p>';
                        return;
                    }
                    
                    data.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'search-result-item';
                        
                        // Quitar etiquetas HTML del snippet por seguridad y estética
                        const cleanSnippet = item.snippet.replace(/<[^>]*>?/gm, '');
                        
                        div.innerHTML = `
                            <a href="/leccion/${item.id}" class="search-result-link">
                                <h4 class="search-result-title">${item.title}</h4>
                                <p class="search-result-snippet">${cleanSnippet}</p>
                            </a>
                        `;
                        resultsContainer.appendChild(div);
                    });
                })
                .catch(err => {
                    console.error('Search error:', err);
                    resultsContainer.innerHTML = '<p style="color:#ef5350; text-align:center; padding:2rem 1rem;">Ocurrió un error en la búsqueda.</p>';
                });
        }, 300);
    });
});
