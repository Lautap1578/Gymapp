(function() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;
    const body = document.body;
    const stored = localStorage.getItem('theme');
    if (stored === 'light') {
        body.classList.remove('dark-mode');
        body.classList.add('light-mode');
    } else {
        body.classList.add('dark-mode');
    }
    toggle.addEventListener('click', function() {
        body.classList.toggle('light-mode');
        body.classList.toggle('dark-mode');
        const theme = body.classList.contains('light-mode') ? 'light' : 'dark';
        localStorage.setItem('theme', theme);
    });
})();

