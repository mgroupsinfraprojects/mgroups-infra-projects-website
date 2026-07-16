(function () {
  if (typeof THREE === 'undefined') return;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) return;

  var root = getComputedStyle(document.documentElement);
  var amber = (root.getPropertyValue('--amber2') || '#E8A046').trim() || '#E8A046';
  var amber2 = (root.getPropertyValue('--amber') || '#C4822A').trim() || '#C4822A';
  var navyAccent = 0x6ea8ff;
  var colors = [amber, amber2, 0xffffff, navyAccent];

  function buildScene(container, canvas, opts) {
    opts = opts || {};
    var count = opts.count || 16;
    var camZ = opts.camZ || 9;
    var interactive = opts.interactive !== false;

    var width = container.clientWidth;
    var height = container.clientHeight;
    if (!width || !height) return;

    var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);

    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 0.5, camZ);

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    var key = new THREE.DirectionalLight(amber, 1.1);
    key.position.set(4, 5, 6);
    scene.add(key);
    var rim = new THREE.DirectionalLight(navyAccent, 0.35);
    rim.position.set(-6, -2, -4);
    scene.add(rim);

    var group = new THREE.Group();
    scene.add(group);

    function edgeMesh(geo, color, op) {
      return new THREE.LineSegments(
        new THREE.EdgesGeometry(geo),
        new THREE.LineBasicMaterial({ color: color, transparent: true, opacity: op })
      );
    }

    var shapes = [];
    for (var i = 0; i < count; i++) {
      var pick = Math.random();
      var geo;
      if (pick < 0.34) geo = new THREE.BoxGeometry(0.85, 0.85, 0.85);
      else if (pick < 0.67) geo = new THREE.OctahedronGeometry(0.65);
      else geo = new THREE.TetrahedronGeometry(0.7);

      var color = colors[i % colors.length];
      var wire = edgeMesh(geo, color, 0.3 + Math.random() * 0.35);

      var solid = new THREE.Mesh(
        geo,
        new THREE.MeshStandardMaterial({ color: color, transparent: true, opacity: 0.05, roughness: 0.6, metalness: 0.2 })
      );
      wire.add(solid);

      var radius = 2.6 + Math.random() * (opts.spread || 3.2);
      var angle = Math.random() * Math.PI * 2;
      var yy = (Math.random() - 0.5) * (opts.vertSpread || 4.2);
      wire.position.set(Math.cos(angle) * radius, yy, Math.sin(angle) * radius - 2.2);
      wire.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
      wire.scale.setScalar(0.5 + Math.random() * 0.8);

      wire.userData = {
        spin: new THREE.Vector3((Math.random() - 0.5) * 0.006, (Math.random() - 0.5) * 0.008, (Math.random() - 0.5) * 0.005),
        float: 0.3 + Math.random() * 0.45,
        floatSpeed: 0.3 + Math.random() * 0.4,
        floatOffset: Math.random() * Math.PI * 2,
        baseY: yy
      };
      group.add(wire);
      shapes.push(wire);
    }

    var mouseX = 0, mouseY = 0, targetRotY = 0, targetRotX = 0;
    if (interactive) {
      container.addEventListener('mousemove', function (e) {
        var rect = container.getBoundingClientRect();
        mouseX = (e.clientX - rect.left) / rect.width - 0.5;
        mouseY = (e.clientY - rect.top) / rect.height - 0.5;
      });
    }

    var visible = true;
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        visible = entries[0].isIntersecting;
      }, { threshold: 0.05 }).observe(container);
    }

    var clock = new THREE.Clock();
    function animate() {
      requestAnimationFrame(animate);
      if (!visible) return;
      var t = clock.getElapsedTime();
      targetRotY += (mouseX * 0.5 - targetRotY) * 0.03;
      targetRotX += (-mouseY * 0.25 - targetRotX) * 0.03;
      group.rotation.y = targetRotY + t * (opts.autoSpin || 0);
      group.rotation.x = targetRotX;
      for (var i = 0; i < shapes.length; i++) {
        var s = shapes[i], u = s.userData;
        s.rotation.x += u.spin.x;
        s.rotation.y += u.spin.y;
        s.rotation.z += u.spin.z;
        s.position.y = u.baseY + Math.sin(t * u.floatSpeed + u.floatOffset) * u.float;
      }
      renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('resize', function () {
      var w = container.clientWidth, h = container.clientHeight;
      if (!w || !h) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
  }

  function init() {
    var mainHero = document.getElementById('hero3d-canvas');
    if (mainHero) {
      buildScene(mainHero.closest('.hero'), mainHero, { count: window.innerWidth < 768 ? 9 : 16, camZ: 9, spread: 3.2, vertSpread: 4.2 });
    }

    document.querySelectorAll('.page-hero').forEach(function (heroEl) {
      if (heroEl.querySelector('#hero3d-canvas')) return;
      heroEl.style.position = 'relative';
      heroEl.style.overflow = 'hidden';
      var canvas = document.createElement('canvas');
      canvas.className = 'hero-3d-canvas page-hero-3d-canvas';
      canvas.setAttribute('aria-hidden', 'true');
      heroEl.insertBefore(canvas, heroEl.firstChild);
      buildScene(heroEl, canvas, {
        count: window.innerWidth < 768 ? 5 : 9,
        camZ: 7.5,
        spread: 2.6,
        vertSpread: 2.6,
        autoSpin: 0.02
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
