const playerDashboard = document.querySelector("[data-player-dashboard]");

if (playerDashboard) {
  const searchInput = playerDashboard.querySelector("[data-player-search]");
  const playerCards = [...playerDashboard.querySelectorAll("[data-player-card]")];
  const searchEmpty = playerDashboard.querySelector("[data-player-search-empty]");
  const historyDialog = document.querySelector("[data-player-history-dialog]");
  const historyTitle = historyDialog.querySelector("[data-player-history-title]");
  const historyEmail = historyDialog.querySelector("[data-player-history-email]");
  const historyStats = historyDialog.querySelector("[data-player-history-stats]");
  const historyContent = historyDialog.querySelector("[data-player-history-content]");
  const closeHistory = historyDialog.querySelector("[data-player-history-close]");
  const rankLabels = { 1: "A", 11: "V", 12: "D", 13: "R" };
  const suitLabels = { spades: "♠", clubs: "♣", hearts: "♥", diamonds: "♦" };
  const dateFormatter = new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  });

  function createElement(tagName, className, text) {
    const element = document.createElement(tagName);
    if (className) {
      element.className = className;
    }
    if (text !== undefined) {
      element.textContent = text;
    }
    return element;
  }

  function signedValue(value) {
    const numericValue = Number(value) || 0;
    return `${numericValue > 0 ? "+" : ""}${numericValue}`;
  }

  function cardLabel(card) {
    const value = Number(card?.value);
    const suit = String(card?.suit || "");
    return `${rankLabels[value] || value || "?"}${suitLabels[suit] || ""}`;
  }

  function renderCards(cards) {
    const container = createElement("span", "player-game-log__cards");
    if (!Array.isArray(cards) || cards.length === 0) {
      container.textContent = "Aucune carte";
      return container;
    }

    cards.forEach((card) => {
      const chip = createElement("span", "admin-card-chip", cardLabel(card));
      chip.dataset.suit = card.suit || "";
      container.append(chip);
    });
    return container;
  }

  function renderHand(label, cards) {
    const hand = createElement("div", "player-game-log__hand");
    hand.append(createElement("strong", "", label), renderCards(cards));
    return hand;
  }

  function renderMoves(moves) {
    const details = document.createElement("details");
    const moveList = Array.isArray(moves) ? moves : [];
    details.append(createElement("summary", "", `${moveList.length} action(s) enregistrée(s)`));

    const list = document.createElement("ol");
    moveList.forEach((move) => {
      const card = move.card ? ` · ${cardLabel(move.card)}` : "";
      list.append(createElement("li", "", `${move.actor} — ${move.move}${card}`));
    });
    details.append(list);
    return details;
  }

  function renderGame(game) {
    const article = createElement("article", "player-game-log");
    const header = createElement("header", "player-game-log__header");
    const headingGroup = document.createElement("div");
    const date = new Date(game.created_at);
    headingGroup.append(
      createElement("h3", "", `Partie #${game.id}`),
      createElement("time", "", Number.isNaN(date.getTime()) ? "Date inconnue" : dateFormatter.format(date)),
    );

    const result = createElement("span", "player-game-log__result", game.result_label);
    result.dataset.result = game.result || "running";
    header.append(headingGroup, result);

    const meta = createElement("div", "player-game-log__meta");
    meta.append(
      createElement("span", "", `Mise : ${game.current_bet} jetons`),
      createElement("strong", Number(game.net_gain) > 0 ? "is-positive" : Number(game.net_gain) < 0 ? "is-negative" : "", `Variation : ${signedValue(game.net_gain)}`),
    );

    const hands = createElement("div", "player-game-log__hands");
    hands.append(
      renderHand("Joueur", game.player_cards),
      renderHand("Croupier", game.dealer_cards),
    );
    article.append(header, meta, hands, renderMoves(game.moves));
    return article;
  }

  function renderStats(data) {
    historyStats.replaceChildren();
    const stats = [
      ["Banque restante", `${data.player.bank} jetons`, ""],
      ["Gain net total", `${signedValue(data.player.total_gain)} jetons`, Number(data.player.total_gain) > 0 ? "is-positive" : Number(data.player.total_gain) < 0 ? "is-negative" : ""],
      ["Parties affichées", String(data.games.length), ""],
    ];

    stats.forEach(([label, value, stateClass]) => {
      const stat = createElement("div", "player-history-stat");
      stat.append(createElement("span", "", label), createElement("strong", stateClass, value));
      historyStats.append(stat);
    });
  }

  function renderHistory(data) {
    historyTitle.textContent = data.player.username;
    historyEmail.textContent = data.player.email || "Aucun email renseigné";
    renderStats(data);
    historyContent.replaceChildren();

    if (!data.games.length) {
      historyContent.append(
        createElement("p", "player-history-empty", "Ce joueur n’a encore aucune partie enregistrée."),
      );
      return;
    }

    data.games.forEach((game) => historyContent.append(renderGame(game)));
  }

  async function openPlayerHistory(button) {
    historyTitle.textContent = button.querySelector(".admin-player-card__identity strong").textContent;
    historyEmail.textContent = "";
    historyStats.replaceChildren();
    historyContent.replaceChildren(
      createElement("p", "player-history-dialog__loading", "Chargement de l’historique…"),
    );
    historyDialog.showModal();

    try {
      const response = await fetch(button.dataset.historyUrl, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(`Historique indisponible (${response.status})`);
      }
      renderHistory(await response.json());
    } catch (error) {
      historyContent.replaceChildren(
        createElement("p", "player-history-error", error.message),
      );
    }
  }

  searchInput.addEventListener("input", () => {
    const query = searchInput.value.trim().toLocaleLowerCase("fr-FR");
    let visibleCount = 0;

    playerCards.forEach((card) => {
      const matches = card.dataset.searchValue.includes(query);
      card.hidden = !matches;
      visibleCount += Number(matches);
    });
    searchEmpty.hidden = visibleCount > 0;
  });

  playerCards.forEach((button) => {
    button.addEventListener("click", () => openPlayerHistory(button));
  });

  closeHistory.addEventListener("click", () => historyDialog.close());
  historyDialog.addEventListener("click", (event) => {
    if (event.target === historyDialog) {
      historyDialog.close();
    }
  });
}
