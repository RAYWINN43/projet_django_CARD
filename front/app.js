const screens = [...document.querySelectorAll("[data-screen]")];
const navigationControls = document.querySelectorAll("[data-go-to]");
const staticForms = document.querySelectorAll("[data-static-form]");

const screenTitles = {
  home: "BlackJack — Accueil",
  login: "BlackJack — Login",
  register: "BlackJack — Register",
};

function showScreen(screenName) {
  const nextScreen = screens.find((screen) => screen.dataset.screen === screenName);

  if (!nextScreen) {
    return;
  }

  screens.forEach((screen) => {
    screen.hidden = screen !== nextScreen;
  });

  document.title = screenTitles[screenName] ?? screenTitles.home;
}

navigationControls.forEach((control) => {
  control.addEventListener("click", () => showScreen(control.dataset.goTo));
});

staticForms.forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
  });
});
