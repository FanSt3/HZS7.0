document.addEventListener('DOMContentLoaded', () => {
    const hamburger = document.querySelector('.hamburger');
    const navLinks = document.querySelector('.nav-links');

    hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('active');
    });

    const pageTransition = document.querySelector('.page-transition');
    
    pageTransition.addEventListener('animationend', () => {
        pageTransition.remove();
    });

    const sections = document.querySelectorAll('main, .about-container, .form-container, .profile-container');
    sections.forEach(section => {
        section.classList.add('fade-in');
    });

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
    
    // Zatvaranje dropdown menija na klik van menija
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.nav-dropdown')) {
            const dropdowns = document.querySelectorAll('.dropdown-content');
            dropdowns.forEach(dropdown => {
                dropdown.classList.remove('show');
            });
        }
    });
});

window.addEventListener('beforeunload', () => {
    document.body.style.opacity = 0;
});