document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.card');

    // تأثير حركة الظهور المتتابع للبطاقات بشكل ناعم واحترافي
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        
        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 150 * (index + 1));
    });
});