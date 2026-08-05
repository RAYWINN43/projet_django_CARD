const avatarPage = document.querySelector("[data-avatar-page]");

if (avatarPage) {
  const carousel = avatarPage.querySelector("[data-avatar-carousel]");
  const avatarSources = [...carousel.querySelectorAll("[data-avatar-id]")].map((source) => ({
    id: source.dataset.avatarId,
    name: source.dataset.avatarName,
    src: source.dataset.avatarSrc,
  }));

  const previousPreview = carousel.querySelector("[data-avatar-previous]");
  const activePreview = carousel.querySelector("[data-avatar-active]");
  const nextPreview = carousel.querySelector("[data-avatar-next]");
  const avatarStatus = carousel.querySelector("[data-avatar-status]");
  const previousButton = carousel.querySelector("[data-carousel-previous]");
  const nextButton = carousel.querySelector("[data-carousel-next]");
  const selectButton = avatarPage.querySelector("[data-select-avatar]");
  const launchButton = avatarPage.querySelector("[data-launch-game]");

  let currentIndex = Number.parseInt(carousel.dataset.avatarStart, 10) || 0;
  let selectedIndex = currentIndex;
  let selectionConfirmed = false;
  let switchTimer;

  const wrappedIndex = (index) => (index + avatarSources.length) % avatarSources.length;

  function updateSelectionState() {
    const isCurrentAvatarSelected = selectionConfirmed && currentIndex === selectedIndex;
    selectButton.textContent = isCurrentAvatarSelected ? "SELECTED" : "SELECT";
    selectButton.setAttribute("aria-pressed", String(isCurrentAvatarSelected));
    activePreview.classList.toggle("is-selected", isCurrentAvatarSelected);
  }

  function renderCarousel(direction = "next") {
    const previousAvatar = avatarSources[wrappedIndex(currentIndex - 1)];
    const activeAvatar = avatarSources[currentIndex];
    const nextAvatar = avatarSources[wrappedIndex(currentIndex + 1)];

    previousPreview.src = previousAvatar.src;
    previousPreview.alt = "";
    nextPreview.src = nextAvatar.src;
    nextPreview.alt = "";
    activePreview.src = activeAvatar.src;
    activePreview.alt = `Personnage affiché : ${activeAvatar.name}`;
    avatarStatus.textContent = `${activeAvatar.name}, personnage ${currentIndex + 1} sur ${avatarSources.length}.`;
    carousel.dataset.direction = direction;

    carousel.classList.remove("is-switching");
    window.clearTimeout(switchTimer);
    window.requestAnimationFrame(() => {
      carousel.classList.add("is-switching");
      switchTimer = window.setTimeout(() => carousel.classList.remove("is-switching"), 190);
    });

    updateSelectionState();
  }

  function moveCarousel(step) {
    currentIndex = wrappedIndex(currentIndex + step);
    renderCarousel(step > 0 ? "next" : "previous");
  }

  previousButton.addEventListener("click", () => moveCarousel(-1));
  nextButton.addEventListener("click", () => moveCarousel(1));

  carousel.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      moveCarousel(-1);
    }

    if (event.key === "ArrowRight") {
      event.preventDefault();
      moveCarousel(1);
    }
  });

  selectButton.addEventListener("click", () => {
    selectedIndex = currentIndex;
    selectionConfirmed = true;
    const selectedAvatar = avatarSources[selectedIndex];
    window.sessionStorage.setItem("blackjack:selected-avatar", selectedAvatar.id);
    updateSelectionState();

    avatarPage.dispatchEvent(
      new CustomEvent("blackjack:avatar-selected", {
        detail: selectedAvatar,
      }),
    );
  });

  launchButton.addEventListener("click", () => {
    const selectedAvatar = avatarSources[selectedIndex];
    window.sessionStorage.setItem("blackjack:selected-avatar", selectedAvatar.id);

    const launchEvent = new CustomEvent("blackjack:launch-game", {
      cancelable: true,
      detail: selectedAvatar,
    });

    if (avatarPage.dispatchEvent(launchEvent)) {
      window.location.assign(avatarPage.dataset.gameUrl);
    }
  });

  renderCarousel();

  const settingsMenu = avatarPage.querySelector("[data-settings-menu]");
  const settingsToggle = settingsMenu.querySelector("[data-settings-toggle]");
  const settingsPanel = settingsMenu.querySelector("[data-settings-panel]");
  const soundToggle = settingsMenu.querySelector("[data-sound-toggle]");
  const soundIcon = soundToggle.querySelector("[data-sound-icon]");
  const rulesDialog = document.querySelector("[data-rules-dialog]");
  const openRulesButton = settingsMenu.querySelector("[data-open-rules]");
  const closeRulesButton = rulesDialog.querySelector("[data-close-rules]");
  let settingsOpen = false;
  let soundMuted = true;

  settingsPanel.inert = true;

  function setSettingsOpen(open) {
    settingsOpen = open;
    settingsMenu.classList.toggle("is-open", settingsOpen);
    settingsToggle.setAttribute("aria-expanded", String(settingsOpen));
    settingsToggle.setAttribute("aria-label", settingsOpen ? "Fermer les paramètres" : "Ouvrir les paramètres");
    settingsPanel.setAttribute("aria-hidden", String(!settingsOpen));
    settingsPanel.inert = !settingsOpen;
  }

  settingsToggle.addEventListener("click", () => setSettingsOpen(!settingsOpen));

  soundToggle.addEventListener("click", () => {
    soundMuted = !soundMuted;
    soundIcon.src = soundMuted ? soundToggle.dataset.mutedSrc : soundToggle.dataset.soundSrc;
    soundToggle.setAttribute("aria-pressed", String(soundMuted));
    soundToggle.setAttribute("aria-label", soundMuted ? "Activer le son" : "Couper le son");
  });

  openRulesButton.addEventListener("click", () => {
    setSettingsOpen(false);
    rulesDialog.showModal();
  });

  closeRulesButton.addEventListener("click", () => rulesDialog.close());

  rulesDialog.addEventListener("click", (event) => {
    if (event.target === rulesDialog) {
      rulesDialog.close();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }

    if (rulesDialog.open) {
      rulesDialog.close();
      return;
    }

    setSettingsOpen(false);
  });

  document.addEventListener("pointerdown", (event) => {
    if (settingsOpen && !settingsMenu.contains(event.target)) {
      setSettingsOpen(false);
    }
  });
}
