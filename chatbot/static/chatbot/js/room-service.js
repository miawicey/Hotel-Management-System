/* Room-service portal interactions: cart, menu filters, concierge and live tracking. */
(() => {
    'use strict';

    const numberFormatter = new Intl.NumberFormat('id-ID', {
        maximumFractionDigits: 0,
    });
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    function formatRupiah(value) {
        const amount = Number(value);
        if (!Number.isFinite(amount)) {
            return 'Rp 0';
        }
        return `Rp ${numberFormatter.format(Math.round(amount))}`;
    }

    function parseQuantity(value) {
        const parsed = parseInt(value, 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 0;
    }

    function getCookie(name) {
        const prefix = `${name}=`;
        const parts = document.cookie ? document.cookie.split(';') : [];
        for (const part of parts) {
            const cookie = part.trim();
            if (cookie.startsWith(prefix)) {
                return decodeURIComponent(cookie.slice(prefix.length));
            }
        }
        return '';
    }

    function csrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) {
            return meta.content;
        }
        const field = document.querySelector(
            'input[name="csrfmiddlewaretoken"]'
        );
        if (field && field.value) {
            return field.value;
        }
        return getCookie('csrftoken');
    }

    /* ------------------------------------------------------------- cart -- */

    function initOrdering() {
        const form = document.getElementById('room-service-form');
        if (!form) {
            return;
        }

        const quantityInputs = Array.from(
            form.querySelectorAll('.qty-input[data-menu-id]')
        );
        if (!quantityInputs.length) {
            return;
        }

        const inputById = new Map(
            quantityInputs.map((input) => [String(input.dataset.menuId), input])
        );
        const cartLines = document.getElementById('cart-lines');
        const cartCount = document.getElementById('cart-count');
        const cartEta = document.getElementById('cart-eta');
        const cartTotal = document.getElementById('cart-total');
        const cartEmpty = document.getElementById('cart-empty');
        const fulfilmentNote = form.querySelector('[data-fulfillment-note]');
        const submitButton = form.querySelector('.nh-rs-submit');
        const fulfilmentInputs = Array.from(
            form.querySelectorAll('input[name="fulfillment"]')
        );
        const feedbackTimers = new WeakMap();
        const emptyMessage = cartEmpty
            ? cartEmpty.textContent.trim()
            : 'Belum ada menu dipilih.';
        const MAX_LINES = 15;
        const MAX_TOTAL = 3000000;
        const MAX_QUANTITY = 20;
        let currentState = { count: 0, total: 0, lines: 0 };

        function fulfilment() {
            const checked = fulfilmentInputs.find((input) => input.checked);
            return checked ? checked.value : 'DELIVERY';
        }

        function handoffMinutes() {
            return fulfilment() === 'PICKUP' ? 8 : 12;
        }

        function setQuantity(input, quantity) {
            const max = Number(input.max) || MAX_QUANTITY;
            const next = Math.min(max, Math.max(0, quantity));
            input.value = String(next);
            return next;
        }

        function readQuantity(input) {
            return Math.min(
                Number(input.max) || MAX_QUANTITY,
                parseQuantity(input.value)
            );
        }

        function describeFulfilment() {
            if (!fulfilmentNote) {
                return;
            }
            fulfilmentNote.textContent = fulfilment() === 'PICKUP'
                ? 'Pesanan akan disiapkan untuk diambil atau dinikmati di The Grand Dining & Lounge.'
                : 'Pesanan akan diantar hangat ke kamar Anda oleh tim room service.';
        }

        function renderCart() {
            let count = 0;
            let total = 0;
            let prep = 0;
            const selected = [];

            quantityInputs.forEach((input) => {
                const quantity = readQuantity(input);
                const card = input.closest('[data-menu-card]');
                if (card) {
                    card.classList.toggle('is-selected', quantity > 0);
                }
                if (!quantity) {
                    return;
                }
                const price = Number(input.dataset.price) || 0;
                const itemPrep = Number(input.dataset.prep) || 0;
                count += quantity;
                total += price * quantity;
                prep = Math.max(prep, itemPrep);
                selected.push({
                    name: input.dataset.name || 'Menu',
                    quantity,
                    price,
                });
            });

            const eta = selected.length
                ? Math.min(prep + handoffMinutes(), 90)
                : 0;

            if (cartLines) {
                const fragment = document.createDocumentFragment();
                selected.forEach((item) => {
                    const row = document.createElement('li');
                    const label = document.createElement('span');
                    label.textContent = item.name;
                    const multiplier = document.createElement('em');
                    multiplier.textContent = ` ×${item.quantity}`;
                    label.appendChild(multiplier);
                    const amount = document.createElement('strong');
                    amount.textContent = formatRupiah(item.price * item.quantity);
                    row.append(label, amount);
                    fragment.appendChild(row);
                });
                cartLines.replaceChildren(fragment);
            }

            if (cartCount) {
                cartCount.textContent = String(count);
            }
            if (cartEta) {
                cartEta.textContent = selected.length ? `±${eta} mnt` : '—';
            }
            if (cartTotal) {
                cartTotal.textContent = formatRupiah(total);
            }

            if (cartEmpty) {
                const warnings = [];
                if (selected.length > MAX_LINES) {
                    warnings.push(
                        `Maksimal ${MAX_LINES} jenis menu dalam satu pesanan.`
                    );
                }
                if (total > MAX_TOTAL) {
                    warnings.push(
                        'Total melebihi batas pemesanan otomatis. Hubungi resepsionis untuk pesanan besar.'
                    );
                }
                cartEmpty.classList.toggle('is-warning', warnings.length > 0);
                if (warnings.length) {
                    cartEmpty.textContent = warnings.join(' ');
                    cartEmpty.hidden = false;
                } else {
                    cartEmpty.textContent = emptyMessage;
                    cartEmpty.hidden = selected.length > 0;
                }
            }

            currentState = { count, total, lines: selected.length };
            return currentState;
        }

        function flashAdded(button) {
            const original = button.dataset.originalLabel
                || button.innerHTML;
            button.dataset.originalLabel = original;
            button.innerHTML = 'Ditambahkan <span aria-hidden="true">✓</span>';
            window.clearTimeout(feedbackTimers.get(button));
            feedbackTimers.set(button, window.setTimeout(() => {
                button.innerHTML = original;
            }, 1400));
        }

        form.addEventListener('click', (event) => {
            const target = event.target instanceof Element ? event.target : null;
            if (!target) {
                return;
            }

            const stepButton = target.closest('[data-step]');
            if (stepButton) {
                const input = stepButton
                    .closest('[data-stepper]')
                    ?.querySelector('.qty-input');
                if (input) {
                    const direction = Number(stepButton.dataset.step) || 0;
                    setQuantity(input, readQuantity(input) + direction);
                    renderCart();
                }
                return;
            }

            const addButton = target.closest('[data-add-item]');
            if (addButton) {
                const input = inputById.get(String(addButton.dataset.addItem));
                if (input) {
                    setQuantity(input, readQuantity(input) + 1);
                    renderCart();
                    flashAdded(addButton);
                }
            }
        });

        form.addEventListener('input', (event) => {
            if (event.target.classList?.contains('qty-input')) {
                renderCart();
            }
        });

        form.addEventListener('change', (event) => {
            if (event.target.classList?.contains('qty-input')) {
                setQuantity(event.target, readQuantity(event.target));
                renderCart();
                return;
            }
            if (event.target.name === 'fulfillment') {
                describeFulfilment();
                renderCart();
            }
        });

        form.addEventListener('submit', (event) => {
            renderCart();
            if (!currentState.count) {
                event.preventDefault();
                if (cartEmpty) {
                    cartEmpty.hidden = false;
                    cartEmpty.textContent = 'Pilih minimal satu menu sebelum mengirim pesanan.';
                    cartEmpty.classList.add('is-warning');
                }
                const panel = form.querySelector('.nh-rs-order-panel');
                if (panel) {
                    panel.scrollIntoView({
                        behavior: reducedMotion.matches ? 'auto' : 'smooth',
                        block: 'center',
                    });
                }
                return;
            }
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = 'Mengirim pesanan ke dapur…';
            }
        });

        describeFulfilment();
        renderCart();
    }

    /* ---------------------------------------------------------- filters -- */

    function initMenuFilters() {
        const bar = document.querySelector('.nh-rs-filter-groups');
        const cards = Array.from(document.querySelectorAll('[data-menu-card]'));
        if (!bar || !cards.length) {
            return;
        }

        const groupButtons = Array.from(
            bar.querySelectorAll('[data-filter-group]')
        );
        const subBar = document.querySelector('[data-filter-subgroups]');
        const subButtons = subBar
            ? Array.from(subBar.querySelectorAll('[data-filter-sub]'))
            : [];
        const groups = Array.from(document.querySelectorAll('[data-menu-group]'));
        const sections = Array.from(
            document.querySelectorAll('[data-menu-section]')
        );
        const featured = document.querySelector('[data-featured-section]');
        const search = document.querySelector('[data-menu-search]');
        const empty = document.querySelector('[data-menu-empty]');

        if (empty && !empty.hasAttribute('aria-live')) {
            empty.setAttribute('aria-live', 'polite');
        }

        let activeGroup = 'all';
        let activeSub = 'all';
        let query = '';

        function setPressed(buttons, isActive) {
            buttons.forEach((button) => {
                button.setAttribute(
                    'aria-pressed',
                    String(isActive(button))
                );
                button.classList.toggle('is-active', isActive(button));
            });
        }

        function refreshSubBar() {
            const hasCategory = activeGroup !== 'all' && activeGroup !== 'recommended';
            if (subBar) {
                subBar.hidden = !hasCategory;
            }
            if (!hasCategory) {
                activeSub = 'all';
            }
            subButtons.forEach((button) => {
                const parent = button.dataset.parentGroup;
                const relevant = !parent
                    || (hasCategory && parent === activeGroup);
                button.hidden = !relevant;
                const isActive = button.dataset.filterSub === activeSub;
                button.classList.toggle('is-active', isActive);
                button.setAttribute('aria-pressed', String(isActive));
            });
        }

        function applyFilters() {
            const tokens = query
                .trim()
                .toLowerCase()
                .split(/\s+/)
                .filter(Boolean);

            cards.forEach((card) => {
                const group = card.dataset.parentGroup;
                const recommended = card.dataset.recommended === 'true';
                let visible = true;

                if (activeGroup === 'recommended') {
                    visible = recommended;
                } else if (activeGroup !== 'all') {
                    visible = group === activeGroup;
                }

                if (visible && activeSub !== 'all') {
                    visible = card.dataset.subcategory === activeSub;
                }

                if (visible && tokens.length) {
                    const haystack = `${card.dataset.search || ''} ${
                        card.dataset.recommended || ''
                    }`.toLowerCase();
                    visible = tokens.every((token) => haystack.includes(token));
                }

                card.hidden = !visible;
            });

            sections.forEach((section) => {
                const hasVisibleCard = Array.from(
                    section.querySelectorAll('[data-menu-card]')
                ).some((card) => !card.hidden);
                section.hidden = !hasVisibleCard;
            });

            groups.forEach((group) => {
                const hasVisibleSection = Array.from(
                    group.querySelectorAll('[data-menu-section]')
                ).some((section) => !section.hidden);
                group.hidden = !hasVisibleSection;
            });

            if (featured) {
                const relevantGroup = activeGroup === 'all'
                    || activeGroup === 'recommended';
                featured.hidden = tokens.length > 0 || !relevantGroup;
            }

            if (empty) {
                empty.hidden = cards.some((card) => !card.hidden);
            }
        }

        groupButtons.forEach((button) => {
            button.addEventListener('click', () => {
                activeGroup = button.dataset.filterGroup || 'all';
                activeSub = 'all';
                setPressed(
                    groupButtons,
                    (item) => item.dataset.filterGroup === activeGroup
                );
                refreshSubBar();
                applyFilters();
            });
        });

        subButtons.forEach((button) => {
            button.addEventListener('click', () => {
                activeSub = button.dataset.filterSub || 'all';
                subButtons.forEach((item) => {
                    const isActive = (item.dataset.filterSub || 'all') === activeSub;
                    item.classList.toggle('is-active', isActive);
                    item.setAttribute('aria-pressed', String(isActive));
                });
                applyFilters();
            });
        });

        if (search) {
            search.addEventListener('input', () => {
                query = search.value;
                // Search is global: release any category filter so a drink
                // can be found while "Makanan Berat" is still selected.
                if (query.trim() && activeGroup !== 'all') {
                    activeGroup = 'all';
                    activeSub = 'all';
                    setPressed(
                        groupButtons,
                        (item) => item.dataset.filterGroup === activeGroup
                    );
                    refreshSubBar();
                }
                applyFilters();
            });
        }

        setPressed(
            groupButtons,
            (button) => button.dataset.filterGroup === activeGroup
        );
        refreshSubBar();
        applyFilters();
    }
    /* --------------------------------------------------------- concierge -- */

    function initConcierge() {
        const panel = document.querySelector('[data-concierge-panel]');
        if (!panel) {
            return;
        }

        const toggle = document.querySelector('[data-concierge-toggle]');
        const closeButton = panel.querySelector('[data-concierge-close]');
        const resetButton = panel.querySelector('[data-concierge-reset]');
        const form = panel.querySelector('[data-concierge-form]');
        const input = panel.querySelector('[data-concierge-input]');
        const sendButton = form
            ? form.querySelector('button[type="submit"]')
            : null;
        const messages = panel.querySelector('[data-concierge-messages]');
        const typing = panel.querySelector('[data-concierge-typing]');
        const suggestions = panel.querySelector('[data-concierge-suggestions]');
        const endpoint = panel.dataset.chatEndpoint;
        const configured = panel.dataset.configured === 'true';
        const welcome = messages
            ? messages.querySelector('.nh-rs-msg.is-bot')?.cloneNode(true)
            : null;

        if (!messages || !form || !input || !endpoint) {
            return;
        }

        let closeTimer = null;
        let busy = false;
        let cooldown = false;
        let cooldownTimer = null;

        function scrollMessages() {
            window.requestAnimationFrame(() => {
                messages.scrollTop = messages.scrollHeight;
            });
        }

        function syncControls() {
            const disabled = !configured || busy || cooldown;
            input.disabled = disabled;
            if (sendButton) {
                sendButton.disabled = disabled;
            }
            if (typing) {
                typing.hidden = !busy;
            }
            messages.setAttribute('aria-busy', String(busy));
        }

        function addMessage(kind, text) {
            const row = document.createElement('div');
            row.className = `nh-rs-msg ${
                kind === 'user' ? 'is-user' : 'is-bot'
            }${kind === 'error' ? ' is-error' : ''}`;

            if (kind !== 'user') {
                const avatar = document.createElement('span');
                avatar.className = 'nh-rs-msg-avatar';
                avatar.setAttribute('aria-hidden', 'true');
                avatar.textContent = 'A';
                row.appendChild(avatar);
            }

            const bubble = document.createElement('div');
            bubble.className = 'nh-rs-msg-bubble';
            const paragraph = document.createElement('p');
            paragraph.textContent = text;
            bubble.appendChild(paragraph);
            row.appendChild(bubble);
            messages.appendChild(row);
            scrollMessages();
        }

        function openPanel() {
            window.clearTimeout(closeTimer);
            panel.hidden = false;
            window.requestAnimationFrame(() => panel.classList.add('is-open'));
            if (toggle) {
                toggle.setAttribute('aria-expanded', 'true');
            }
            document.body.classList.add('nh-concierge-open');
            if (!input.disabled) {
                window.setTimeout(() => {
                    input.focus({ preventScroll: true });
                }, 140);
            }
            scrollMessages();
        }

        function closePanel(restoreFocus = true) {
            panel.classList.remove('is-open');
            if (toggle) {
                toggle.setAttribute('aria-expanded', 'false');
            }
            document.body.classList.remove('nh-concierge-open');
            window.clearTimeout(closeTimer);
            closeTimer = window.setTimeout(() => {
                panel.hidden = true;
            }, 220);
            if (restoreFocus && toggle) {
                toggle.focus({ preventScroll: true });
            }
        }

        function startCooldown(seconds) {
            const duration = Math.min(
                120,
                Math.max(1, parseInt(seconds, 10) || 5)
            );
            const originalPlaceholder = input.getAttribute('placeholder') || '';
            let remaining = duration;

            window.clearInterval(cooldownTimer);
            cooldown = true;
            cooldownTimer = window.setInterval(() => {
                remaining -= 1;
                if (remaining <= 0) {
                    window.clearInterval(cooldownTimer);
                    cooldownTimer = null;
                    cooldown = false;
                    input.placeholder = originalPlaceholder;
                    syncControls();
                    if (!panel.hidden) {
                        input.focus({ preventScroll: true });
                    }
                    return;
                }
                input.placeholder = `Coba lagi dalam ${remaining} detik…`;
                syncControls();
            }, 1000);

            input.placeholder = `Coba lagi dalam ${remaining} detik…`;
            syncControls();
        }

        function handleResponse(response, data) {
            if (data && data.ok && data.reply) {
                addMessage('bot', data.reply);
                return;
            }

            if (response && response.status === 403) {
                addMessage(
                    'error',
                    'Sesi keamanan halaman kedaluwarsa. Muat ulang halaman lalu coba lagi.'
                );
                return;
            }

            if (response && response.status === 429) {
                addMessage(
                    'error',
                    (data && data.error)
                        || 'Anda mengirim pesan terlalu cepat. Coba lagi sebentar lagi.'
                );
                if (data && data.retry_after) {
                    startCooldown(data.retry_after);
                }
                return;
            }

            addMessage(
                'error',
                (data && data.error)
                    || 'Pesan belum dapat dikirim. Coba lagi atau hubungi resepsionis.'
            );
        }

        async function sendMessage(rawMessage) {
            if (!configured || busy || cooldown) {
                return;
            }
            const message = String(rawMessage || '').trim().slice(0, 1000);
            if (!message) {
                return;
            }

            addMessage('user', message);
            input.value = '';
            busy = true;
            syncControls();
            scrollMessages();

            const controller = new AbortController();
            const timeout = window.setTimeout(() => controller.abort(), 45000);

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        Accept: 'application/json',
                        'X-CSRFToken': csrfToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({ message }),
                    signal: controller.signal,
                });

                let data = null;
                try {
                    data = await response.json();
                } catch (error) {
                    data = null;
                }
                handleResponse(response, data);
            } catch (error) {
                addMessage(
                    'error',
                    error && error.name === 'AbortError'
                        ? 'Concierge AI tidak merespons tepat waktu. Coba lagi atau hubungi resepsionis.'
                        : 'Koneksi ke concierge terputus. Periksa jaringan Anda lalu coba lagi.'
                );
            } finally {
                window.clearTimeout(timeout);
                busy = false;
                syncControls();
                if (!panel.hidden) {
                    input.focus({ preventScroll: true });
                    scrollMessages();
                }
            }
        }

        async function resetConversation() {
            if (busy) {
                return;
            }
            busy = true;
            syncControls();

            const controller = new AbortController();
            const timeout = window.setTimeout(() => controller.abort(), 10000);

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        Accept: 'application/json',
                        'X-CSRFToken': csrfToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({ reset: true }),
                    signal: controller.signal,
                });
                let data = null;
                try {
                    data = await response.json();
                } catch (error) {
                    data = null;
                }
                if (!response.ok || !data || !data.ok) {
                    throw new Error('reset failed');
                }
                messages.replaceChildren();
                if (welcome) {
                    messages.appendChild(welcome.cloneNode(true));
                }
                input.value = '';
                scrollMessages();
            } catch (error) {
                addMessage(
                    'error',
                    'Percakapan belum dapat direset. Coba lagi sebentar lagi.'
                );
            } finally {
                window.clearTimeout(timeout);
                busy = false;
                syncControls();
                if (!panel.hidden) {
                    input.focus({ preventScroll: true });
                }
            }
        }

        if (toggle) {
            toggle.addEventListener('click', () => {
                if (panel.hidden) {
                    openPanel();
                } else {
                    closePanel();
                }
            });
        }

        if (closeButton) {
            closeButton.addEventListener('click', () => closePanel());
        }

        if (resetButton) {
            resetButton.addEventListener('click', resetConversation);
        }

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            sendMessage(input.value);
        });

        if (suggestions) {
            suggestions.addEventListener('click', (event) => {
                const button = event.target.closest('[data-prompt]');
                if (button) {
                    sendMessage(button.dataset.prompt);
                }
            });
        }

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && !panel.hidden) {
                closePanel();
            }
        });

        syncControls();
    }

    /* ---------------------------------------------------------- tracking -- */

    function initOrderTracking() {
        const container = document.querySelector('[data-order-tracking]');
        if (!container) {
            return;
        }
        const endpoint = container.dataset.endpoint;
        if (!endpoint) {
            return;
        }

        const single = container.dataset.mode === 'single';
        const pollInterval = 15000;
        const announcement = document.querySelector('[data-track-status]');
        const section = container.closest('.nh-rs-history')
            || container.closest('section');
        const liveBadge = section
            ? section.querySelector('.nh-rs-live')
            : null;

        let hasActive = container.dataset.hasActive === 'true';
        let stopped = false;
        let inFlight = false;
        let failures = 0;
        let timer = null;

        function updateLiveBadge(active) {
            if (!liveBadge) {
                return;
            }
            liveBadge.classList.toggle('is-live', active);
            let label = 'Status terakhir';
            if (single) {
                label = active ? 'Live' : 'Final';
            } else if (active) {
                label = 'Diperbarui otomatis';
            }
            const last = liveBadge.lastChild;
            if (last && last.nodeType === Node.TEXT_NODE) {
                last.textContent = label;
            } else {
                liveBadge.appendChild(document.createTextNode(label));
            }
        }

        function announce(message) {
            if (!announcement) {
                return;
            }
            announcement.textContent = '';
            window.requestAnimationFrame(() => {
                announcement.textContent = message;
            });
        }

        function cardFromPayload(payload) {
            const template = document.createElement('template');
            template.innerHTML = String(payload.html || '').trim();
            return template.content.firstElementChild;
        }

        function applyOrder(payload) {
            if (!payload || !payload.id) {
                return;
            }
            const selector = `[data-order-track][data-order-id="${payload.id}"]`;
            const existing = container.querySelector(selector);

            if (existing && existing.dataset.status !== payload.status) {
                const replacement = cardFromPayload(payload);
                if (replacement) {
                    existing.replaceWith(replacement);
                    replacement.classList.add('is-updated');
                    window.setTimeout(() => {
                        replacement.classList.remove('is-updated');
                    }, 1600);
                    announce(
                        `Pesanan ${payload.code} diperbarui: ${payload.status_label}.`
                    );
                }
                return;
            }

            if (!existing && !single) {
                const replacement = cardFromPayload(payload);
                if (replacement) {
                    const emptyState = container.querySelector(
                        '.nh-rs-history-empty'
                    );
                    if (emptyState) {
                        emptyState.remove();
                    }
                    container.prepend(replacement);
                    replacement.classList.add('is-updated');
                    window.setTimeout(() => {
                        replacement.classList.remove('is-updated');
                    }, 1600);
                }
            }
        }

        function schedule(delay) {
            window.clearTimeout(timer);
            if (stopped || !hasActive) {
                return;
            }
            timer = window.setTimeout(poll, delay);
        }

        async function poll() {
            if (stopped || inFlight) {
                return;
            }
            if (document.hidden) {
                schedule(pollInterval);
                return;
            }

            inFlight = true;
            const controller = new AbortController();
            const timeout = window.setTimeout(() => controller.abort(), 10000);

            try {
                const response = await fetch(endpoint, {
                    headers: {
                        Accept: 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    credentials: 'same-origin',
                    cache: 'no-store',
                    signal: controller.signal,
                });
                if (!response.ok) {
                    if ([401, 403, 404].includes(response.status)) {
                        stopped = true;
                    }
                    return;
                }
                const data = await response.json();
                if (!data || data.ok !== true) {
                    return;
                }

                failures = 0;
                if (single && data.order) {
                    applyOrder(data.order);
                    hasActive = Boolean(data.order.active);
                } else if (Array.isArray(data.orders)) {
                    data.orders.forEach(applyOrder);
                    hasActive = Boolean(data.has_active);
                }
                updateLiveBadge(hasActive);
                if (!hasActive) {
                    stopped = true;
                }
            } catch (error) {
                failures += 1;
            } finally {
                window.clearTimeout(timeout);
                inFlight = false;
                const delay = failures
                    ? Math.min(pollInterval * 2 ** Math.min(failures, 3), 60000)
                    : pollInterval;
                schedule(delay);
            }
        }

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && hasActive && !stopped) {
                window.clearTimeout(timer);
                poll();
            }
        });

        window.addEventListener('pagehide', () => {
            window.clearTimeout(timer);
        });

        updateLiveBadge(hasActive);
        if (hasActive) {
            schedule(4000);
        }
    }

    /* ------------------------------------------------------------ images -- */

    function initImageFallbacks() {
        const selector = '.nh-rs-card-media img, .nh-rs-feature-media img';

        function hideBroken(image) {
            image.hidden = true;
        }

        document.addEventListener('error', (event) => {
            if (event.target instanceof HTMLImageElement
                && event.target.matches(selector)) {
                hideBroken(event.target);
            }
        }, true);

        document.querySelectorAll(selector).forEach((image) => {
            if (image.complete && image.naturalWidth === 0) {
                hideBroken(image);
            }
        });
    }

    function init() {
        initOrdering();
        initMenuFilters();
        initConcierge();
        initOrderTracking();
        initImageFallbacks();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();
