(() => {
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector("#main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const isOpen = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(isOpen));
      toggle.textContent = isOpen ? "Close" : "Menu";
    });
  }

  const bankToggle = document.querySelector('input[name="use_bank_offers"]');
  const exchangeToggle = document.querySelector('input[name="use_exchange"]');
  const extra = document.querySelector("#offer-extra");
  const bankFields = document.querySelector("#bank-fields");
  const exchangeFields = document.querySelector("#exchange-fields");

  function updateOfferFields() {
    if (!extra) return;
    const bankOn = Boolean(bankToggle && bankToggle.checked);
    const exchangeOn = Boolean(exchangeToggle && exchangeToggle.checked);
    extra.hidden = !bankOn && !exchangeOn;
    if (bankFields) bankFields.hidden = !bankOn;
    if (exchangeFields) exchangeFields.hidden = !exchangeOn;
  }
  if (bankToggle) bankToggle.addEventListener("change", updateOfferFields);
  if (exchangeToggle) exchangeToggle.addEventListener("change", updateOfferFields);
  updateOfferFields();
})();
