(function () {
    "use strict";
    var root = document.getElementById("cart-root");
    if (!root) return;

    var minDays = parseInt(root.dataset.minDays, 10) || 1;
    var maxDays = parseInt(root.dataset.maxDays, 10) || 30;
    var errorBox = document.getElementById("cart-error");
    var checkoutBtn = document.getElementById("cart-checkout");
    var busy = false;

    function showError(msg) {
        if (!errorBox) return;
        errorBox.textContent = msg || "";
        errorBox.hidden = !msg;
    }

    function applyCart(cart) {
        if (cart.item_count === 0) { window.location.reload(); return; } // server renders empty state

        var seen = {};
        var stores = {};
        cart.stores.forEach(function (store) {
            stores[store.slug] = store;
            store.items.forEach(function (it) { seen[it.id] = it; });
        });

        root.querySelectorAll(".cart-item").forEach(function (li) {
            var it = seen[li.dataset.id];
            if (!it) { li.remove(); return; }
            li.querySelector(".cart-item-check").checked = it.selected;
            li.querySelector(".cart-days").textContent = it.days;
            li.querySelector(".cart-item-subtotal").textContent = it.subtotal_display;
            li.querySelector(".cart-minus").disabled = it.days <= minDays;
            li.querySelector(".cart-plus").disabled = it.days >= maxDays;
        });

        root.querySelectorAll(".cart-store").forEach(function (sec) {
            var store = stores[sec.dataset.store];
            if (!store) { sec.remove(); return; }
            var box = sec.querySelector(".cart-store-check");
            box.checked = store.all_selected;
            box.dataset.indeterminate = store.some_selected ? "1" : "0";   // CSS shows the partial state
        });

        document.getElementById("cart-count").textContent = cart.selected_count;
        document.getElementById("cart-total").textContent = cart.total_display;
        var hint = document.getElementById("cart-hint");
        if (hint) hint.hidden = cart.can_checkout;
        if (checkoutBtn) {
            checkoutBtn.classList.toggle("is-disabled", !cart.can_checkout);
            if (cart.can_checkout) { checkoutBtn.removeAttribute("aria-disabled"); checkoutBtn.removeAttribute("tabindex"); }
            else { checkoutBtn.setAttribute("aria-disabled", "true"); checkoutBtn.setAttribute("tabindex", "-1"); }
        }
    }

    function send(form, submitter) {
        if (busy) return;
        busy = true;
        showError("");
        var body;
        try { body = new FormData(form, submitter || undefined); }
        catch (e) { body = new FormData(form); if (submitter && submitter.name) body.append(submitter.name, submitter.value); }

        fetch(form.action, {
            method: "POST",
            body: body,
            credentials: "same-origin",
            headers: { "X-Requested-With": "XMLHttpRequest", "Accept": "application/json" }
        })
            .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, status: res.status, data: data }; }); })
            .then(function (r) {
                if (r.status === 401) { window.location.reload(); return; }   // sesi habis: server mengarahkan ke login
                if (r.ok && r.data.ok) applyCart(r.data.cart);
                else { showError(r.data.error || "Something went wrong. Please try again."); }
            })
            .catch(function () { showError("Could not reach the server. Please try again."); })
            .then(function () { busy = false; });
    }

    root.addEventListener("submit", function (e) {
        var form = e.target.closest("form.cart-form");
        if (!form) return;
        e.preventDefault();
        send(form, e.submitter);
    });

    root.addEventListener("change", function (e) {
        if (e.target.matches(".cart-item-check, .cart-store-check")) {
            var form = e.target.closest("form");
            if (form.requestSubmit) form.requestSubmit(); else form.submit();
        }
    });

    if (checkoutBtn) {
            checkoutBtn.addEventListener("click", function (e) {
            if (checkoutBtn.classList.contains("is-disabled")) e.preventDefault();
        });
    }
})();