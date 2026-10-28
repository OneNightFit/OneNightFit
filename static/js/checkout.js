/* For Checkout, keep the Checkout button disabled until a payment method is chosen.
   Without JS the button stays enabled and the server validates instead. */
(function () {
    "use strict";
    var form = document.getElementById("checkout-form");
    if (!form) return;
    var btn = document.getElementById("checkout-submit");
    var hint = document.getElementById("checkout-hint");

    function sync() {
        var ok = !!form.querySelector('input[name="payment"]:checked');
        btn.disabled = !ok;
        if (hint) hint.hidden = ok;
    }
    form.addEventListener("change", sync);
    sync();
})();