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
});

window.addEventListener('beforeunload', () => {
    document.body.style.opacity = 0;
});