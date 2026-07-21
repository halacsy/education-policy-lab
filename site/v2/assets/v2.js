(() => {
  const root = document.documentElement;
  const buttons = [...document.querySelectorAll("[data-set-language]")];
  const setLanguage = (language) => {
    root.dataset.language = language;
    root.lang = language;
    document.title = root.dataset[`title${language === "hu" ? "Hu" : "En"}`] || document.title;
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = description.dataset[`description${language === "hu" ? "Hu" : "En"}`] || description.content;
    document.querySelectorAll("[data-label-en][data-label-hu]").forEach((element) => {
      const localized = element.dataset[`label${language === "hu" ? "Hu" : "En"}`];
      if (element.tagName === "OPTION") element.textContent = localized;
      else element.setAttribute("aria-label", localized);
    });
    document.querySelectorAll("[data-title-en][data-title-hu]").forEach((element) => {
      element.setAttribute("title", element.dataset[`title${language === "hu" ? "Hu" : "En"}`]);
    });
    buttons.forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.setLanguage === language));
    });
    try { localStorage.setItem("epl-v2-language", language); } catch (_) {}
  };
  let saved = "hu";
  try { saved = localStorage.getItem("epl-v2-language") || "hu"; } catch (_) {}
  setLanguage(saved === "en" ? "en" : "hu");
  buttons.forEach((button) => button.addEventListener("click", () => setLanguage(button.dataset.setLanguage)));

  document.querySelectorAll("[data-lens-filter]").forEach((select) => {
    select.addEventListener("change", () => {
      const section = select.closest(".lens-section");
      section.querySelectorAll("tbody tr").forEach((row) => {
        row.hidden = select.value !== "all" && row.dataset.verdict !== select.value;
      });
    });
  });
})();
