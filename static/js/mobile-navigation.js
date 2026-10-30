(() => {
    const trigger = document.querySelector('.nav-hamburg-menu');
    const drawer = document.getElementById('mobile-navigation');

    if (!trigger || !drawer) return;

    const panel = drawer.querySelector('.mobile-nav__panel');
    const closeControls = drawer.querySelectorAll('[data-mobile-nav-close]');
    let previouslyFocused = null;

    const getFocusableElements = () => Array.from(
        drawer.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')
    ).filter((element) => element.getClientRects().length > 0);

    const openDrawer = () => {
        previouslyFocused = document.activeElement;
        drawer.classList.add('is-open');
        drawer.setAttribute('aria-hidden', 'false');
        drawer.removeAttribute('inert');
        trigger.setAttribute('aria-expanded', 'true');
        document.body.classList.add('mobile-nav-open');
        panel.focus();
    };

    const closeDrawer = ({ restoreFocus = true } = {}) => {
        if (!drawer.classList.contains('is-open')) return;

        drawer.classList.remove('is-open');
        drawer.setAttribute('aria-hidden', 'true');
        drawer.setAttribute('inert', '');
        trigger.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('mobile-nav-open');

        if (restoreFocus) {
            const focusTarget = previouslyFocused && previouslyFocused.isConnected
                ? previouslyFocused
                : trigger;
            focusTarget.focus();
        }
    };

    trigger.addEventListener('click', (event) => {
        event.preventDefault();
        if (drawer.classList.contains('is-open')) {
            closeDrawer();
        } else {
            openDrawer();
        }
    });

    trigger.addEventListener('keydown', (event) => {
        if (event.key !== ' ') return;
        event.preventDefault();
        if (drawer.classList.contains('is-open')) {
            closeDrawer();
        } else {
            openDrawer();
        }
    });

    closeControls.forEach((control) => {
        control.addEventListener('click', () => closeDrawer());
    });

    drawer.querySelector('.mobile-nav__links').addEventListener('click', (event) => {
        if (event.target.closest('a')) closeDrawer({ restoreFocus: false });
    });

    document.addEventListener('keydown', (event) => {
        if (!drawer.classList.contains('is-open')) return;

        if (event.key === 'Escape') {
            event.preventDefault();
            closeDrawer();
            return;
        }

        if (event.key !== 'Tab') return;

        const focusableElements = getFocusableElements();
        if (focusableElements.length === 0) {
            event.preventDefault();
            panel.focus();
            return;
        }

        const first = focusableElements[0];
        const last = focusableElements[focusableElements.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === panel)) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });

    window.matchMedia('(min-width: 769px)').addEventListener('change', (event) => {
        if (event.matches) closeDrawer({ restoreFocus: false });
    });
})();
