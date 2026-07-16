(function () {
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function ready(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  }

  ready(function () {
    var targets = document.querySelectorAll(
      '.section, .stats-band, .trust-strip, .credentials-section, .service-area-strip, .cta, ' +
      '.service-card, .project-card, .credential-card, .why-cards article, .content-card, .gallery-card'
    );
    if (!targets.length) return;

    if (reduceMotion || !('IntersectionObserver' in window)) {
      targets.forEach(function (el) { el.classList.add('reveal-3d', 'is-visible'); });
      return;
    }

    targets.forEach(function (el, i) {
      el.classList.add('reveal-3d');
      el.style.transitionDelay = Math.min((i % 4) * 70, 210) + 'ms';
    });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.14, rootMargin: '0px 0px -8% 0px' });

    targets.forEach(function (el) { io.observe(el); });
  });
})();
