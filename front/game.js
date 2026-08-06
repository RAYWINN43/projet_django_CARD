const gamePage = document.querySelector("[data-game-page]");

if (gamePage) {
  const historyStorageKey = "blackjack:game-history";
  const soundPreferenceKey = "blackjack:sound-muted";
  const ambientPositionKey = "blackjack:ambient-position";
  const dealSoundStorageKey = "blackjack:deal-sound-count";
  const drawSoundOffset = 0;
  const drawSoundPlaybackWindow = 650;
  const rankNames = {
    1: "ace",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "jack",
    12: "queen",
    13: "king",
  };

  const frenchRanks = {
    1: "As",
    2: "Deux",
    3: "Trois",
    4: "Quatre",
    5: "Cinq",
    6: "Six",
    7: "Sept",
    8: "Huit",
    9: "Neuf",
    10: "Dix",
    11: "Valet",
    12: "Dame",
    13: "Roi",
  };

  const frenchSuits = {
    spades: "pique",
    clubs: "trèfle",
    hearts: "cœur",
    diamonds: "carreau",
  };

  const assetsBase = gamePage.dataset.assetsBase;
  const playerAvatar = gamePage.querySelector("[data-game-player-avatar]");
  const endPlayerAvatar = gamePage.querySelector("[data-game-end-player-avatar]");
  const avatarSources = new Map(
    [...gamePage.querySelectorAll("[data-game-avatar-id]")].map((source) => [
      source.dataset.gameAvatarId,
      source.dataset.gameAvatarSrc,
    ]),
  );

  const selectedAvatarId = window.sessionStorage.getItem("blackjack:selected-avatar") || "homme-manteau";
  const selectedAvatarSrc = avatarSources.get(selectedAvatarId) || avatarSources.get("homme-manteau");
  playerAvatar.src = selectedAvatarSrc;

  if (endPlayerAvatar) {
    endPlayerAvatar.src = selectedAvatarSrc;
  }

  function cardAssetNumber(value, suit) {
    switch (suit) {
      case "spades":
        return value + 4 + (value >= 8 ? 1 : 0);
      case "diamonds":
        return value + 18 + (value >= 5 ? 1 : 0);
      case "clubs":
        return value + 32 + (value >= 2 ? 1 : 0) + (value >= 12 ? 1 : 0);
      case "hearts":
        return value + 47 + (value >= 9 ? 1 : 0);
      default:
        return null;
    }
  }

  function cardAssetUrl(card) {
    const value = Number(card.value);
    const suit = String(card.suit).toLowerCase();
    const assetNumber = cardAssetNumber(value, suit);
    const rankName = rankNames[value];

    if (!assetNumber || !rankName) {
      return `${assetsBase}065-playing card.png`;
    }

    return `${assetsBase}${String(assetNumber).padStart(3, "0")}-${rankName} of ${suit}.png`;
  }

  function cardAccessibleName(card) {
    const value = Number(card.value);
    const suit = String(card.suit).toLowerCase();
    return `${frenchRanks[value] || value} de ${frenchSuits[suit] || suit}`;
  }

  function readHand(scriptId, sourceDocument = document) {
    const dataScript = sourceDocument.getElementById(scriptId);

    if (!dataScript) {
      return null;
    }

    try {
      return JSON.parse(dataScript.textContent);
    } catch {
      return null;
    }
  }

  function renderHand(container, payload, isDealer) {
    if (!container || !payload || !Array.isArray(payload.cards)) {
      return;
    }

    container.replaceChildren();

    payload.cards.forEach((card, index) => {
      const cardImage = document.createElement("img");
      const showFace = !isDealer || payload.visible === true || index === 0;

      cardImage.className = `playing-card${showFace ? "" : " playing-card--back"}`;
      cardImage.style.setProperty("--card-index", index);
      cardImage.src = showFace ? cardAssetUrl(card) : `${assetsBase}065-playing card.png`;
      cardImage.alt = showFace ? cardAccessibleName(card) : "Carte du croupier face cachée";
      container.append(cardImage);
    });
  }

  function handValue(payload) {
    if (!payload || !Array.isArray(payload.cards)) {
      return 0;
    }

    let value = 0;
    let aces = 0;

    payload.cards.forEach((card) => {
      const cardValue = Number(card.value);
      value += Math.min(cardValue, 10);
      if (cardValue === 1) {
        aces += 1;
      }
    });

    while (aces > 0 && value <= 11) {
      value += 10;
      aces -= 1;
    }

    return value;
  }

  function gameResult(playerPayload, dealerPayload) {
    const playerScore = handValue(playerPayload);
    const dealerScore = handValue(dealerPayload);
    let result = "draw";

    if ((playerScore < dealerScore && dealerScore <= 21) || playerScore > 21) {
      result = "loss";
    } else if (playerScore > dealerScore || dealerScore > 21) {
      result = "win";
    }

    return { result, playerScore, dealerScore };
  }

  function readHistory() {
    try {
      const history = JSON.parse(window.localStorage.getItem(historyStorageKey) || "[]");
      return Array.isArray(history) ? history : [];
    } catch {
      return [];
    }
  }

  function saveHistoryEntry(entry) {
    if (!entry) {
      return;
    }

    const history = readHistory().filter((item) => String(item.id) !== String(entry.id));
    history.unshift(entry);

    try {
      window.localStorage.setItem(historyStorageKey, JSON.stringify(history.slice(0, 12)));
    } catch {
      // L'historique reste optionnel si le stockage local est indisponible.
    }
  }

  function historyEntryFromDocument(sourceDocument) {
    const sourcePage = sourceDocument.querySelector("[data-game-page]");

    if (!sourcePage || !sourcePage.dataset.gameId || sourcePage.dataset.gameRunning === "true") {
      return null;
    }

    const sourcePlayerHand = readHand("player-hand-data", sourceDocument);
    const sourceDealerHand = readHand("dealer-hand-data", sourceDocument);

    if (!sourcePlayerHand || !sourceDealerHand) {
      return null;
    }

    const { result, playerScore, dealerScore } = gameResult(sourcePlayerHand, sourceDealerHand);

    const pool = Number(sourcePage.dataset.gamePool) || 0;

    return {
      id: sourcePage.dataset.gameId,
      playedAt: new Date().toISOString(),
      bet: Number(sourcePage.dataset.gameBet) || 0,
      bankAfter: Number(sourcePage.dataset.playerBank) || 0,
      result,
      gain: result === "win" ? pool : result === "loss" ? -pool : 0,
      playerScore,
      dealerScore,
      playerCards: sourcePlayerHand.cards,
      dealerCards: sourceDealerHand.cards,
    };
  }

  function historyResultLabel(result) {
    if (result === "win") {
      return "Victoire";
    }

    if (result === "loss") {
      return "Défaite";
    }

    return "Égalité";
  }

  function formatGain(value) {
    const numericValue = Number(value) || 0;
    const prefix = numericValue > 0 ? "+" : "";
    return `${prefix}${numericValue} €`;
  }

  function createHistoryCards(cards) {
    const cardList = document.createElement("div");
    cardList.className = "game-history-cards";

    cards.forEach((card) => {
      const cardImage = document.createElement("img");
      cardImage.className = "game-history-card";
      cardImage.src = cardAssetUrl(card);
      cardImage.alt = cardAccessibleName(card);
      cardList.append(cardImage);
    });

    return cardList;
  }

  function createHistoryHand(label, score, cards) {
    const hand = document.createElement("div");
    hand.className = "game-history-hand";

    const handLabel = document.createElement("span");
    handLabel.className = "game-history-hand__label";
    handLabel.textContent = `${label} · ${score}`;

    hand.append(handLabel, createHistoryCards(cards));
    return hand;
  }

  function renderHistory(historyList, historyEmpty) {
    const history = readHistory();
    historyList.replaceChildren();

    if (history.length === 0) {
      historyList.append(historyEmpty);
      historyEmpty.hidden = false;
      return;
    }

    history.forEach((entry) => {
      const item = document.createElement("article");
      item.className = "game-history-entry";
      item.dataset.result = entry.result;

      const meta = document.createElement("div");
      meta.className = "game-history-entry__meta";

      const number = document.createElement("span");
      number.className = "game-history-entry__number";
      number.textContent = `Partie #${entry.id}`;

      const date = document.createElement("time");
      date.className = "game-history-entry__date";
      date.dateTime = entry.playedAt;
      date.textContent = new Intl.DateTimeFormat("fr-FR", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(entry.playedAt));

      const bet = document.createElement("span");
      bet.className = "game-history-entry__bet";
      bet.textContent = `Mise : ${entry.bet} €`;
      meta.append(number, date, bet);

      const hands = document.createElement("div");
      hands.className = "game-history-entry__hands";
      hands.append(
        createHistoryHand("Vous", entry.playerScore, entry.playerCards),
        createHistoryHand("Bernard", entry.dealerScore, entry.dealerCards),
      );

      const result = document.createElement("div");
      result.className = "game-history-entry__result";

      const status = document.createElement("span");
      status.className = "game-history-entry__status";
      status.textContent = historyResultLabel(entry.result);

      const gain = document.createElement("strong");
      gain.className = "game-history-entry__gain";
      gain.textContent = formatGain(entry.gain);
      result.append(status, gain);

      item.append(meta, hands, result);
      historyList.append(item);
    });
  }

  const dealerHand = readHand("dealer-hand-data");
  const playerHand = readHand("player-hand-data");
  renderHand(gamePage.querySelector("[data-dealer-hand]"), dealerHand, true);
  renderHand(gamePage.querySelector("[data-player-hand]"), playerHand, false);

  function renderEndCards(container, payload) {
    if (!container || !payload || !Array.isArray(payload.cards)) {
      return;
    }

    container.replaceChildren();

    payload.cards.forEach((card) => {
      const cardImage = document.createElement("img");
      cardImage.className = "game-end-card";
      cardImage.src = cardAssetUrl(card);
      cardImage.alt = cardAccessibleName(card);
      container.append(cardImage);
    });
  }

  const endScreen = gamePage.querySelector("[data-game-end-screen]");
  let currentResult = null;

  if (endScreen && dealerHand && playerHand) {
    currentResult = gameResult(playerHand, dealerHand);
    const backendResult = {
      player: "win",
      dealer: "loss",
      draw: "draw",
    }[gamePage.dataset.gameResult];
    if (backendResult) {
      currentResult.result = backendResult;
    }
    const endTitle = endScreen.querySelector("[data-game-end-title]");
    const playerGain = endScreen.querySelector("[data-game-end-player-gain]");
    const dealerGain = endScreen.querySelector("[data-game-end-dealer-gain]");
    const pool = Number(gamePage.dataset.gamePool) || 0;

    endScreen.dataset.result = currentResult.result;
    endTitle.textContent = currentResult.result === "win" ? "GAGNÉ" : currentResult.result === "loss" ? "PERDU" : "ÉGALITÉ";

    renderEndCards(endScreen.querySelector("[data-game-end-player-cards]"), playerHand);
    renderEndCards(endScreen.querySelector("[data-game-end-dealer-cards]"), dealerHand);

    if (currentResult.result === "win") {
      playerGain.textContent = String(pool * 2);
      playerGain.hidden = false;
    } else if (currentResult.result === "loss") {
      dealerGain.textContent = String(pool);
      dealerGain.hidden = false;
    }
  }

  const gameStatus = gamePage.querySelector("[data-game-status]");
  if (dealerHand && playerHand) {
    gameStatus.textContent = `Main du joueur : ${handValue(playerHand)} points. Le croupier possède ${dealerHand.cards.length} cartes.`;
  }

  if (gamePage.dataset.hasGame === "true" && gamePage.dataset.gameRunning === "false") {
    saveHistoryEntry(historyEntryFromDocument(document));
  }

  const betForm = gamePage.querySelector("[data-bet-form]");
  if (betForm) {
    const betInput = betForm.querySelector("[name='bet']");

    betForm.addEventListener("submit", (event) => {
      const betValue = Number(betInput.value);
      const maxBet = Number(betInput.max);
      const isValidBet =
        Number.isInteger(betValue) && betValue > 0 && (!maxBet || betValue <= maxBet);

      betInput.setAttribute("aria-invalid", String(!isValidBet));

      if (!isValidBet) {
        event.preventDefault();
        betInput.focus();
        return;
      }

      window.sessionStorage.setItem(dealSoundStorageKey, "4");
    });

    betInput.addEventListener("input", () => betInput.removeAttribute("aria-invalid"));
  }

  const settingsMenu = gamePage.querySelector("[data-game-settings-menu]");
  const settingsToggle = settingsMenu.querySelector("[data-game-settings-toggle]");
  const settingsPanel = settingsMenu.querySelector("[data-game-settings-panel]");
  const soundToggle = settingsMenu.querySelector("[data-game-sound-toggle]");
  const soundIcon = soundToggle.querySelector("[data-game-sound-icon]");
  const rulesDialog = document.querySelector("[data-game-rules-dialog]");
  const openRulesButton = settingsMenu.querySelector("[data-game-open-rules]");
  const closeRulesButton = rulesDialog.querySelector("[data-game-close-rules]");
  const historyDialog = document.querySelector("[data-game-history-dialog]");
  const openHistoryButton = settingsMenu.querySelector("[data-game-open-history]");
  const closeHistoryButton = historyDialog.querySelector("[data-game-close-history]");
  const historyList = historyDialog.querySelector("[data-game-history-list]");
  const historyEmpty = historyDialog.querySelector("[data-game-history-empty]");
  const ambientAudio = document.querySelector("[data-game-audio-ambient]");
  const drawAudio = document.querySelector("[data-game-audio-draw]");
  const winAudio = document.querySelector("[data-game-audio-win]");
  const lossAudio = document.querySelector("[data-game-audio-loss]");
  const activeEffects = new Set();
  let settingsOpen = false;
  let soundMuted = window.localStorage.getItem(soundPreferenceKey) === "true";
  let endSoundPending = false;
  let ambientPositionRestored = false;

  ambientAudio.volume = 0.12;
  drawAudio.volume = 0.78;
  winAudio.volume = 0.82;
  lossAudio.volume = 0.72;

  function saveAmbientPosition() {
    if (!ambientAudio || !Number.isFinite(ambientAudio.currentTime)) {
      return;
    }

    window.sessionStorage.setItem(
      ambientPositionKey,
      JSON.stringify({ time: ambientAudio.currentTime, savedAt: Date.now() }),
    );
  }

  function restoreAmbientPosition() {
    if (ambientPositionRestored || !ambientAudio) {
      return;
    }

    const storedPosition = window.sessionStorage.getItem(ambientPositionKey);
    if (!storedPosition) {
      ambientPositionRestored = true;
      return;
    }

    const applyStoredPosition = () => {
      try {
        const { time, savedAt } = JSON.parse(storedPosition);
        const elapsed = Number.isFinite(savedAt) ? Math.max(0, (Date.now() - savedAt) / 1000) : 0;
        const nextPosition = Number(time) + elapsed;

        if (Number.isFinite(nextPosition) && Number.isFinite(ambientAudio.duration)) {
          ambientAudio.currentTime = nextPosition % ambientAudio.duration;
        }
      } catch {
        window.sessionStorage.removeItem(ambientPositionKey);
      }

      ambientPositionRestored = true;
    };

    if (ambientAudio.readyState >= 1) {
      applyStoredPosition();
    } else {
      ambientAudio.addEventListener("loadedmetadata", applyStoredPosition, { once: true });
    }
  }

  async function startAmbientAudio() {
    if (soundMuted || !ambientAudio.paused) {
      return true;
    }

    try {
      await ambientAudio.play();
      return true;
    } catch {
      return false;
    }
  }

  async function playEffect(source, startAt = 0) {
    if (soundMuted || !source) {
      return false;
    }

    const effect = source.cloneNode();
    effect.volume = source.volume;
    activeEffects.add(effect);
    effect.addEventListener("ended", () => activeEffects.delete(effect), { once: true });

    const seekToEffect = () => {
      if (startAt > 0 && Number.isFinite(effect.duration)) {
        effect.currentTime = Math.min(startAt, Math.max(0, effect.duration - 0.08));
      }
    };

    if (effect.readyState >= 1) {
      seekToEffect();
    } else {
      effect.addEventListener("loadedmetadata", seekToEffect, { once: true });
      effect.load();
    }

    try {
      // L'appel à play() doit rester synchrone avec le clic utilisateur.
      // Attendre loadedmetadata auparavant faisait perdre l'autorisation audio
      // dans certains navigateurs.
      await effect.play();
      if (source === drawAudio) {
        gamePage.dataset.drawSoundState = "playing";
      }
      return true;
    } catch {
      if (source === drawAudio) {
        gamePage.dataset.drawSoundState = "blocked";
      }
      activeEffects.delete(effect);
      return false;
    }
  }

  async function playDrawEffect() {
    if (soundMuted || !drawAudio) {
      return false;
    }

    try {
      drawAudio.pause();

      if (drawAudio.readyState < 1) {
        await new Promise((resolve, reject) => {
          drawAudio.addEventListener("loadedmetadata", resolve, { once: true });
          drawAudio.addEventListener("error", reject, { once: true });
          drawAudio.load();
        });
      }

      drawAudio.currentTime = Math.min(
        drawSoundOffset,
        Math.max(0, drawAudio.duration - 0.08),
      );
      await drawAudio.play();
      gamePage.dataset.drawSoundState = "playing";
      return true;
    } catch {
      gamePage.dataset.drawSoundState = "blocked";
      return false;
    }
  }

  function stopAllAudio() {
    ambientAudio.pause();
    drawAudio.pause();
    activeEffects.forEach((effect) => effect.pause());
    activeEffects.clear();
  }

  function updateSoundControl() {
    soundIcon.src = soundMuted ? soundToggle.dataset.mutedSrc : soundToggle.dataset.soundSrc;
    soundToggle.setAttribute("aria-pressed", String(soundMuted));
    soundToggle.setAttribute("aria-label", soundMuted ? "Activer le son" : "Couper le son");
  }

  async function playEndSoundOnce() {
    if (!currentResult || currentResult.result === "draw" || endSoundPending) {
      return;
    }

    const endSoundKey = `blackjack:end-sound:${gamePage.dataset.gameId}`;
    if (window.sessionStorage.getItem(endSoundKey) === "played") {
      return;
    }

    endSoundPending = true;
    const played = await playEffect(currentResult.result === "win" ? winAudio : lossAudio);
    endSoundPending = false;

    if (played) {
      window.sessionStorage.setItem(endSoundKey, "played");
      endScreen.dataset.endSound = currentResult.result;
    }
  }

  function scheduleInitialDealSounds() {
    const dealSoundCount = Number(window.sessionStorage.getItem(dealSoundStorageKey)) || 0;
    window.sessionStorage.removeItem(dealSoundStorageKey);

    if (dealSoundCount <= 0 || soundMuted) {
      return;
    }

    for (let index = 0; index < dealSoundCount; index += 1) {
      window.setTimeout(() => playEffect(drawAudio, drawSoundOffset), index * 180);
    }
  }

  settingsPanel.inert = true;
  updateSoundControl();
  restoreAmbientPosition();
  startAmbientAudio();
  scheduleInitialDealSounds();
  playEndSoundOnce();

  const unlockAudio = () => {
    startAmbientAudio();
    playEndSoundOnce();
  };

  document.addEventListener("pointerdown", unlockAudio, { once: true, capture: true });
  document.addEventListener("keydown", unlockAudio, { once: true, capture: true });
  window.addEventListener("pagehide", saveAmbientPosition);

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
    window.localStorage.setItem(soundPreferenceKey, String(soundMuted));
    updateSoundControl();

    if (soundMuted) {
      stopAllAudio();
    } else {
      startAmbientAudio();
      playEndSoundOnce();
    }
  });

  openRulesButton.addEventListener("click", () => {
    setSettingsOpen(false);
    rulesDialog.showModal();
  });

  closeRulesButton.addEventListener("click", () => rulesDialog.close());

  openHistoryButton.addEventListener("click", () => {
    setSettingsOpen(false);
    renderHistory(historyList, historyEmpty);
    historyDialog.showModal();
  });

  closeHistoryButton.addEventListener("click", () => historyDialog.close());

  rulesDialog.addEventListener("click", (event) => {
    if (event.target === rulesDialog) {
      rulesDialog.close();
    }
  });

  historyDialog.addEventListener("click", (event) => {
    if (event.target === historyDialog) {
      historyDialog.close();
    }
  });

  const gameActionControls = [...gamePage.querySelectorAll("[data-game-action]")];
  const gameRecap = gamePage.querySelector("[data-game-recap]");
  const currentBetOutput = gamePage.querySelector("[data-game-current-bet]");
  let actionPending = false;

  gameActionControls.forEach((actionControl) => {
    actionControl.addEventListener("click", async (event) => {
      if (actionPending) {
        event.preventDefault();
        return;
      }

      event.preventDefault();
      const actionForm = actionControl.closest("[data-game-action-form]");
      if (!actionForm) {
        return;
      }

      actionPending = true;
      gameActionControls.forEach((control) => {
        control.classList.add("is-loading");
        control.disabled = true;
      });

      const playsDrawSound = ["hit", "double"].includes(
        actionControl.dataset.gameActionType,
      );
      const drawSoundWindow = playsDrawSound
        ? new Promise((resolve) => window.setTimeout(resolve, drawSoundPlaybackWindow))
        : Promise.resolve();

      if (playsDrawSound) {
        playDrawEffect();
      }

      if (actionControl.dataset.gameActionType === "double" && gameRecap && currentBetOutput) {
        const currentBet = Number(gameRecap.dataset.gameCurrentBet) || 0;
        const doubledBet = currentBet * 2;
        gameRecap.dataset.gameCurrentBet = String(doubledBet);
        currentBetOutput.textContent = `${doubledBet} €`;
        gameStatus.textContent = `Mise actuelle doublée : ${doubledBet} euros.`;
      }

      let actionApplied = false;

      try {
        const response = await window.fetch(actionForm.action, {
          method: "POST",
          body: new FormData(actionForm),
          credentials: "same-origin",
          redirect: "follow",
        });

        if (!response.ok) {
          throw new Error(`Action impossible (${response.status})`);
        }

        actionApplied = true;

        if (response.redirected && gamePage.dataset.gameDetailUrl) {
          const detailResponse = await window.fetch(gamePage.dataset.gameDetailUrl, {
            credentials: "same-origin",
          });

          if (detailResponse.ok) {
            const detailMarkup = await detailResponse.text();
            const detailDocument = new DOMParser().parseFromString(detailMarkup, "text/html");
            saveHistoryEntry(historyEntryFromDocument(detailDocument));
          }
        }

        // Laisse au pop le temps d'être entendu avant le rafraîchissement de page.
        await drawSoundWindow;

        saveAmbientPosition();
        window.location.assign(
          response.redirected ? response.url : gamePage.dataset.gameDetailUrl || response.url,
        );
      } catch {
        saveAmbientPosition();
        if (actionApplied && gamePage.dataset.gameDetailUrl) {
          window.location.assign(gamePage.dataset.gameDetailUrl);
        } else {
          actionForm.submit();
        }
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }

    if (rulesDialog.open) {
      rulesDialog.close();
      return;
    }

    if (historyDialog.open) {
      historyDialog.close();
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
