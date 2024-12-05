document.addEventListener('DOMContentLoaded', () => {
    // Zatvaranje mobilnog menija kada se klikne na link
    const navLinks = document.querySelectorAll('.nav-item');
    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            const hamburger = document.querySelector('.hamburger');
            const navMenu = document.querySelector('.nav-links');
            if (window.innerWidth <= 768) {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            }
        });
    });
});

window.addEventListener('beforeunload', () => {
    document.body.style.opacity = 0;
});