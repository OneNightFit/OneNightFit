// Sign up: tampilkan field "Shop name" hanya kalau memilih Seller.
(function () {
  var radios = document.querySelectorAll('input[name="role"]');
  var shopField = document.getElementById("shop-name-field");
  if (!radios.length || !shopField) return;

  function sync() {
    var selected = document.querySelector('input[name="role"]:checked');
    shopField.hidden = !(selected && selected.value === "seller");
  }
  radios.forEach(function (r) { r.addEventListener("change", sync); });
  sync();
})();
