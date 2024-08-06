
document.addEventListener('DOMContentLoaded', () => {
    const slides = document.querySelector('.slides');
    const slide = document.querySelectorAll('.slide');
    const dots = document.querySelectorAll('.dot');

    let index = 0;

    const showSlide = (i) => {
        index = (i + slide.length) % slide.length;
        slides.style.transform = `translateX(${-index * 100}%)`;
        dots.forEach((dot, idx) => {
            dot.classList.toggle('active', idx === index);
        });
    };

    dots.forEach((dot, idx) => {
        dot.addEventListener('click', () => {
            showSlide(idx);
        });
    });

    showSlide(index);
});
