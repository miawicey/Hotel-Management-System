/* ==========================================================================
   Nocturn Haven — Django admin motion layer
   Adds the same tactile feel as the public site to the staff control room:
   Lenis smooth scrolling plus staggered reveals for modules, metric cards,
   changelist rows and form rows. Nothing here changes Django's own widgets,
   and everything falls back to plain document flow when the library is
   missing or the visitor prefers reduced motion.
   ========================================================================== */
(function () {
    'use strict';

    var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    var lenis = null;
    var rafId = null;

    /* ------------------------------------------------------ smooth scroll -- */

    /* Nested scroll surfaces (select2 menus, read-only code blocks, inline
       tables on small screens) keep their native wheel behaviour so the
       admin's own interactions never fight the smooth scroller. */
    function insideScroller(node) {
        var depth = 0;
        for (var el = node; el && el !== document.body && depth < 8; el = el.parentElement) {
            var overflowY = window.getComputedStyle(el).overflowY;
            if (overflowY === 'auto' || overflowY === 'scroll') return true;
            depth += 1;
        }
        return false;
    }

    function startLenis() {
        if (lenis || prefersReduced.matches || typeof window.Lenis !== 'function') return;
        lenis = new window.Lenis({
            duration: 0.95,
            easing: function (t) { return Math.min(1, 1.001 - Math.pow(2, -10 * t)); },
            smoothWheel: true,
            wheelMultiplier: 0.9,
            touchMultiplier: 1.3,
            prevent: function (node) {
                if (!node || !node.closest) return false;
                if (node.closest('[data-lenis-prevent], .select2-results, .vLargeTextField')) return true;
                return insideScroller(node);
            },
        });
        function raf(time) {
            lenis.raf(time);
            rafId = window.requestAnimationFrame(raf);
        }
        rafId = window.requestAnimationFrame(raf);
        document.documentElement.classList.add('nh-smooth-scroll');
    }

    function stopLenis() {
        if (rafId !== null) window.cancelAnimationFrame(rafId);
        rafId = null;
        if (lenis) { lenis.destroy(); lenis = null; }
        document.documentElement.classList.remove('nh-smooth-scroll');
    }

    startLenis();

    if (typeof prefersReduced.addEventListener === 'function') {
        prefersReduced.addEventListener('change', function (event) {
            if (event.matches) {
                stopLenis();
                revealAll();
            } else {
                startLenis();
            }
        });
    }

    /* ------------------------------------------------------- header state -- */

    var scrolled = false;
    function syncHeaderState() {
        var next = (window.scrollY || document.documentElement.scrollTop) > 20;
        if (next === scrolled) return;
        scrolled = next;
        document.body.classList.toggle('nh-admin-scrolled', scrolled);
    }

    syncHeaderState();
    window.addEventListener('scroll', syncHeaderState, { passive: true });

    /* ------------------------------------------------------------- reveals */

    var REVEAL_GROUPS = [
        { selector: '.nh-admin-metric', max: 8, stagger: 60 },
        { selector: '#content .module', max: 12, stagger: 55 },
        { selector: '#content-main .form-row', max: 30, stagger: 24 },
        { selector: '#changelist-form .results > table > tbody > tr', max: 30, stagger: 20 },
    ];

    var items = [];

    function revealAll() {
        items.forEach(function (item) { item.classList.add('is-revealed'); });
    }

    if (!prefersReduced.matches) {
        REVEAL_GROUPS.forEach(function (group) {
            var nodes = document.querySelectorAll(group.selector);
            Array.prototype.slice.call(nodes, 0, group.max).forEach(function (node, index) {
                node.classList.add('nh-reveal');
                node.style.setProperty('--nh-reveal-delay', Math.min(index * group.stagger, 380) + 'ms');
                items.push(node);
            });
        });

        if (items.length) {
            if ('IntersectionObserver' in window) {
                var observer = new IntersectionObserver(function (entries) {
                    entries.forEach(function (entry) {
                        if (!entry.isIntersecting) return;
                        entry.target.classList.add('is-revealed');
                        observer.unobserve(entry.target);
                    });
                }, { rootMargin: '0px 0px -6% 0px', threshold: 0.05 });
                items.forEach(function (item) { observer.observe(item); });
            } else {
                revealAll();
            }
        }
    }
})();
