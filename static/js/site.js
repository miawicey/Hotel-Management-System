/* ==========================================================================
   Nocturn Haven — shared site behaviour
   Smooth scrolling (Lenis), scroll reveals, pointer tilt, mobile navigation.
   Everything degrades to a static, usable page: no library, no motion API,
   or prefers-reduced-motion all fall back to plain document flow.
   ========================================================================== */
(function () {
    'use strict';

    var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)');

    /* ------------------------------------------------------ smooth scroll -- */

    var lenis = null;
    var rafId = null;

    function startLenis() {
        if (lenis || prefersReduced.matches || typeof window.Lenis !== 'function') return;
        lenis = new window.Lenis({
            duration: 1.05,
            easing: function (t) { return Math.min(1, 1.001 - Math.pow(2, -10 * t)); },
            smoothWheel: true,
            wheelMultiplier: 0.95,
            touchMultiplier: 1.4,
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
            if (event.matches) stopLenis(); else startLenis();
        });
    }

    /* In-page anchors: route through Lenis when it is active. */
    document.addEventListener('click', function (event) {
        var link = event.target.closest('a[href^="#"]');
        if (!link) return;
        var id = link.getAttribute('href');
        if (!id || id === '#') return;
        var target = document.querySelector(id);
        if (!target) return;
        event.preventDefault();
        if (lenis) {
            lenis.scrollTo(target, { offset: -96, duration: 1.1 });
        } else {
            target.scrollIntoView({ behavior: prefersReduced.matches ? 'auto' : 'smooth', block: 'start' });
        }
        if (history.replaceState) history.replaceState(null, '', id);
    });

    /* --------------------------------------------------------- header state */

    var header = document.querySelector('.site-header');
    if (header) {
        var setHeaderState = function () {
            var scrolled = (window.scrollY || document.documentElement.scrollTop) > 24;
            header.classList.toggle('is-scrolled', scrolled);
        };
        setHeaderState();
        window.addEventListener('scroll', setHeaderState, { passive: true });
    }

    /* -------------------------------------------------------- mobile menu -- */

    var navToggle = document.querySelector('[data-nav-toggle]');
    var mobileNav = document.querySelector('[data-mobile-nav]');

    function closeMobileNav(restoreFocus) {
        if (!navToggle || !mobileNav) return;
        navToggle.setAttribute('aria-expanded', 'false');
        mobileNav.classList.remove('is-open');
        mobileNav.setAttribute('aria-hidden', 'true');
        document.documentElement.style.removeProperty('overflow');
        if (lenis) lenis.start();
        if (restoreFocus) navToggle.focus({ preventScroll: true });
    }

    if (navToggle && mobileNav) {
        mobileNav.setAttribute('aria-hidden', 'true');
        var links = mobileNav.querySelectorAll('a');
        Array.prototype.forEach.call(links, function (link, index) {
            link.style.transitionDelay = (60 + index * 45) + 'ms';
            /* Same-page links (e.g. /#facilities) don't reload, so the panel
               has to close itself or the page would stay scroll-locked. */
            link.addEventListener('click', function () { closeMobileNav(); });
        });

        navToggle.addEventListener('click', function () {
            var open = navToggle.getAttribute('aria-expanded') === 'true';
            if (open) { closeMobileNav(); return; }
            navToggle.setAttribute('aria-expanded', 'true');
            mobileNav.classList.add('is-open');
            mobileNav.setAttribute('aria-hidden', 'false');
            document.documentElement.style.overflow = 'hidden';
            if (lenis) lenis.stop();
            var first = mobileNav.querySelector('a');
            if (first) first.focus({ preventScroll: true });
        });

        document.addEventListener('keydown', function (event) {
            if (event.key !== 'Escape') return;
            if (!mobileNav.classList.contains('is-open')) return;
            closeMobileNav(true);
        });
    }

    /* ------------------------------------------------------ scroll reveals */

    var revealables = document.querySelectorAll('[data-reveal]');
    if (revealables.length) {
        Array.prototype.forEach.call(document.querySelectorAll('[data-reveal-group]'), function (group) {
            var index = 0;
            Array.prototype.forEach.call(group.querySelectorAll('[data-reveal]'), function (item) {
                item.style.setProperty('--reveal-delay', Math.min(index * 70, 350) + 'ms');
                index += 1;
            });
        });

        if ('IntersectionObserver' in window && !prefersReduced.matches) {
            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (!entry.isIntersecting) return;
                    entry.target.classList.add('is-revealed');
                    observer.unobserve(entry.target);
                });
            }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
            Array.prototype.forEach.call(revealables, function (item) { observer.observe(item); });
        } else {
            Array.prototype.forEach.call(revealables, function (item) { item.classList.add('is-revealed'); });
        }
    }

    /* ------------------------------------------------------- pointer tilt -- */

    var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
    if (finePointer.matches && !prefersReduced.matches) {
        Array.prototype.forEach.call(document.querySelectorAll('[data-tilt]'), function (card) {
            var inner = card.querySelector('.tilt-inner');
            if (!inner) return;
            var frame = null;

            function apply(event) {
                var rect = card.getBoundingClientRect();
                var px = (event.clientX - rect.left) / rect.width - 0.5;
                var py = (event.clientY - rect.top) / rect.height - 0.5;
                frame = window.requestAnimationFrame(function () {
                    inner.style.transform = 'perspective(900px) rotateX(' + (-py * 5).toFixed(2) + 'deg) rotateY(' + (px * 6).toFixed(2) + 'deg) translateZ(0)';
                });
            }

            card.classList.add('is-tilting');
            card.addEventListener('pointermove', apply);
            card.addEventListener('pointerleave', function () {
                if (frame !== null) window.cancelAnimationFrame(frame);
                card.classList.remove('is-tilting');
                inner.style.transform = '';
            });
        });
    }

    /* ------------------------------------------- auto-submitting filters ---- */

    Array.prototype.forEach.call(document.querySelectorAll('[data-auto-submit]'), function (field) {
        field.addEventListener('change', function () {
            if (field.form) field.form.submit();
        });
    });
})();
