/* For Checkout, keep the Checkout button disabled until a payment method is chosen.
   Without JS the button stays enabled and the server validates instead. */
(function () {
    "use strict";
    var form = document.getElementById("checkout-form");
    if (!form) return;
    var btn = document.getElementById("checkout-submit");
    var hint = document.getElementById("checkout-hint");

    function sync() {
        var profileOk = form.dataset.profileComplete === "true";
        var paymentOk = !!form.querySelector('input[name="payment"]:checked');

        var stores = form.querySelectorAll(".checkout-store");
        var shippingOk = true;
        for (var i = 0; i < stores.length; i++) {
            if (!stores[i].querySelector('input[name^="shipping_"]:checked')) {
                shippingOk = false;
                break;
            }
        }
        var ok = profileOk && paymentOk && shippingOk;
        btn.disabled = !ok;
        if (hint) hint.hidden = ok;
    }
    form.addEventListener("change", sync);
    sync();
})();
