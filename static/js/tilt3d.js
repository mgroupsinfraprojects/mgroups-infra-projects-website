(function () {
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) return;
  if (!('ontouchstart' in window)) {
    document.addEventListener('DOMContentLoaded', function () {
      var cards = document.querySelectorAll('.service-card, .project-card, .credential-card, .why-cards article');
      cards.forEach(function (card) {
        card.classList.add('tilt-3d');
        var rect;
        card.addEventListener('mouseenter', function () { rect = card.getBoundingClientRect(); });
        card.addEventListener('mousemove', function (e) {
          if (!rect) rect = card.getBoundingClientRect();
          var px = (e.clientX - rect.left) / rect.width;
          var py = (e.clientY - rect.top) / rect.height;
          var rx = (0.5 - py) * 10;
          var ry = (px - 0.5) * 12;
          card.style.transform = 'perspective(900px) rotateX(' + rx.toFixed(2) + 'deg) rotateY(' + ry.toFixed(2) + 'deg) translateY(-6px)';
          card.style.setProperty('--glow-x', (px * 100).toFixed(1) + '%');
          card.style.setProperty('--glow-y', (py * 100).toFixed(1) + '%');
        });
        card.addEventListener('mouseleave', function () {
          card.style.transform = '';
        });
      });
    });
  }
})();
