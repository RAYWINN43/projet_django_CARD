---
title: "Plateforme de Jeu de Cartes (Django & Infra)"
icon: "🃏"
description: "Conception, modélisation ORM, développement UI/UX et conteneurisation Docker d'un jeu de cartes web complet."
categories:
  - Projets
  - Django
  - UI/UX
  - Docker
---

# 🃏 Projet Django Artisanal : Plateforme de Jeu de Cartes Web

### 1.0.1. Contexte & Objectifs

Contrairement à la démarche du **Vibe Coding** où l'IA génère du code de manière autonome, ce projet met l'accent sur le **développement artisanal et guidé**. En tant que futur développeur fullstack, vous devez maîtriser chaque ligne de code, chaque modèle ORM et chaque choix d'infrastructure.

L'objectif est de concevoir, développer et déployer une **plateforme web de jeu de cartes** (ex: *Bataille*, *Blackjack*, *Belote*, *Uno* ou *Tarot simplifié*) basée sur le framework **Django**. Ce projet fait le pont entre vos cours de **développement web (Django)**, d'**intégration UI/UX (Design Tokens, Atomic Design)** et d'**infrastructure (Docker & Compose)**.

::: {.callout-note collapse="true" title="Pourquoi le code manuel sur ce projet ?"}
- **Maîtrise de l'ORM et des algorithmes** : La gestion d'une main de cartes, le mélange de paquets (*shuffle*), la validation des coups et la machine à états d'une partie requièrent une logique pure et contrôlée sans bugs d'effets de bord.
- **Appropriation du Design System** : Créer un jeu de cartes réactif exige une maîtrise fine des CSS Design Tokens et des composants atomiques.
- **Restauration de la confiance Infra** : Configurer manuellement Docker Compose et isoler PostgreSQL de Django permet d'assimiler concrètement le fonctionnement des réseaux et volumes de conteneurs.
:::

### 1.0.2. Modalités de Rendu

* **Groupe :** 1 à 3 personnes maximum.
* **Livrable :** Un lien vers un dépôt **GitHub Public**.
* **Environnement :** Le projet doit pouvoir s'exécuter localement en une seule commande (`docker compose up --build`).
* **Organisation Git :** Commits atomiques et explicites avec une répartition claire du travail au sein de l'équipe (pas de commit unique monolithique).

### 1.0.3. Spécifications Techniques Obligatoires

::: {.row gap=3 mb=4}
:::: {.col span=6}
::::: {.card-window}
#### 🐍 Backend & Logique Métier Django {.bi-code-slash}

* **Modélisation ORM complète :**
  * `Game` / `Session` : Suivi de l'état de la partie (*EN_ATTENTE*, *EN_COURS*, *TERMINEE*), du tour actuel et des joueurs.
  * `Player` / `Profile` : Intégration de la gestion d'utilisateurs Django (Authentification, Statistiques, Score).
  * `Card` & `Deck` : Modélisation des enseignes, valeurs et du paquet de cartes avec méthodes d'action (`draw()`, `shuffle()`).
  * `MoveLog` : Historique traçable des coups joués dans la partie.
* **Architecture MVT & SRP :**
  * Isolation stricte du moteur de jeu (`game_engine.py`) en dehors des vues Django.
  * Vues basées sur les formulaires ou API AJAX/Fetch pour interagir sans rechargement complet si souhaité.
* **Sécurité & Authentification :**
  * Validation stricte des règles côté serveur (impossible de tricher en modifiant la requête client).
  * CSRF Tokens activés et gestion des sessions sécurisées.
:::::
::::

:::: {.col span=6}
::::: {.card-window}
#### 🎨 Frontend, UI/UX & Design Tokens {.bi-palette}

* **Design System & Tokens :**
  * Centralisation des variables CSS dans une feuille de style (`tokens.css` ou SCSS) : couleurs des enseignes (Cœur, Carreau, Pique, Trèfle), espacements et typographies.
* **Atomic Design pour le Jeu :**
  * **Atomes** : Cartes individuelles (`.card-unit`), badges d'état, boutons d'action.
  * **Molécules** : Main du joueur (`.player-hand`), pioche (`.deck-stack`), zone d'action.
  * **Organismes** : Tapis de jeu réactif (`.game-table`), tableau de bord des scores.
* **Retours Visuels & Ergonomie :**
  * Transitions CSS fluides pour le survol et le jeu d'une carte.
  * Indication visuelle claire du tour de jeu actuel et du joueur actif.
:::::
::::
:::

::: {.row gap=3 mb=4}
:::: {.col span=6}
::::: {.card-window}
#### 🐳 Infrastructure & Docker Compose {.bi-box-seam}

* **Conteneurisation Django (`Dockerfile`) :**
  * Utilisation d'une image Python légère (`python:3.11-slim`).
  * Exécution sous un utilisateur non-root pour la sécurité.
  * Automatisation des migrations (`python manage.py migrate`) et du rassemblement des fichiers statiques.
* **Orchestration Multi-Services (`docker-compose.yml`) :**
  * Service `web` : Application Django exécutée via Gunicorn/Uvicorn.
  * Service `db` : Base de données PostgreSQL avec volume nommé persistant (`postgres_data`).
  * Service `cache` : Redis pour la gestion efficace des sessions et le cache de l'état de jeu.
* **Réseau & Isolement :**
  * Utilisation de variables d'environnement (`.env`) pour `SECRET_KEY`, `POSTGRES_PASSWORD`, etc.
  * Utilisation d'un réseau privé conteneurisé et de **healthchecks** pour garantir que Django attend PostgreSQL avant de démarrer.
:::::
::::

:::: {.col span=6}
::::: {.card-window}
#### 🧪 DevOps, QA & Qualité de Code {.bi-check2-circle}

* **Tests Automatisés Django (`tests.py`) :**
  * Tests unitaires sur la distribution des cartes, le comptage des points et les transitions d'état.
  * Tests d'intégration sur les vues Django et le respect des permissions d'accès.
* **Règles de Clean Code :**
  * Respect des règles PEP8.
  * Linting automatisé avec `flake8` ou `ruff`, formatage propre avec `black`.
* **CI/CD Pipeline (GitHub Actions) :**
  * Pipeline automatisé exécutant le linter et la suite de tests Django à chaque `push` ou `pull_request`.
:::::
::::
:::

### 1.0.4. Le Rapport Technique (README.md)

Le fichier `README.md` est la vitrine de votre architecture technique. Il doit documenter rigoureusement la démarche de l'équipe :

1. **Présentation & En-tête :** Noms, Prénoms, règles du jeu retenu et capture d'écran de l'interface principale.
2. **Guide de Démarrage Rapide :** Instructions exactes pour lancer l'infrastructure complète avec `docker compose up --build` et créer un compte administrateur.
3. **Architecture Logicielle (UML / ERD) :**
   * Diagramme de classes des modèles ORM Django (Cartes, Joueurs, Parties).
   * Schéma de la Machine à États (*State Machine*) régissant les tours de jeu.
4. **Choix UI/UX & Design Tokens :** Explication de la structure des tokens et de la hiérarchie des composants d'Atomic Design.
5. **Journal d'Architecture & Auto-Évaluation :** Rétrospective sur le code écrit manuellement, les difficultés rencontrées sur l'ORM ou Docker et la façon dont elles ont été résolues.

---

# 📝 Fiche de Notation (20 Points)

## 🚫 Critères Éliminatoires (Go / No-Go)

*Si l'une des cases ci-dessous est cochée "NON", le projet n'est pas corrigé (Note = 0 ou rattrapage).*

| **Critère**                                                                                         | **OUI** | **NON** |
| :-------------------------------------------------------------------------------------------------- | :------ | :------ |
| Présence du fichier `README.md` complet avec le guide de lancement et les schémas                   | ☐       | ☐       |
| L'application démarre sans erreur via `docker compose up` avec PostgreSQL                           | ☐       | ☐       |
| La boucle de jeu complète (distribution, tours, fin de partie, calcul de score) est jouable        | ☐       | ☐       |
| Le code métier backend/frontend est rédigé et maîtrisé par les étudiants (pas de copier-coller brut) | ☐       | ☐       |

## 📊 Grille Détaillée

### 2.2.1. Backend Django & Modélisation Métier (6 pts)

| **Critère**                   | **Détail**                                                                                                 | **Note** |
| :---------------------------- | :--------------------------------------------------------------------------------------------------------- | :------- |
| **Modélisation ORM & SRP**    | Les modèles (Game, Player, Card, Deck) sont propres, indexés et respectent le découplage métier.            | **/ 2.5**|
| **Logique de Jeu & Moteur**   | Le moteur (`game_engine.py`) gère la machine à états, le mélange et la validation des coups de façon robuste. | **/ 2.5**|
| **Sécurité & Sessions**       | Gestion des droits, protection CSRF et sécurité des données d'authentification.                            | **/ 1**  |

### 2.2.2. UI/UX & Design System (5 pts)

| **Critère**                   | **Détail**                                                                                                 | **Note** |
| :---------------------------- | :--------------------------------------------------------------------------------------------------------- | :------- |
| **Design Tokens (CSS)**       | Intégration claire des variables de design (enseignes, thèmes, espacements) sans valeurs codées en dur.    | **/ 2**  |
| **Atomic Design & Ergonomie** | Composants bien hiérarchisés (Atomes de carte, Molécules de main, Table de jeu) et interface réactive.    | **/ 2**  |
| **Feedback Visuel**           | Transitions CSS soignées lors du tirage/jeu de cartes, affichage clair du joueur actif et du score.        | **/ 1**  |

### 2.2.3. DevOps, Docker & Infrastructure (5 pts)

| **Critère**                   | **Détail**                                                                                                 | **Note** |
| :---------------------------- | :--------------------------------------------------------------------------------------------------------- | :------- |
| **Dockerfile de Prod/Dev**    | `Dockerfile` optimisé, multi-stage ou slim, exécuté en utilisateur non-root avec gestion des statiques.     | **/ 2**  |
| **Orchestration Compose**     | `docker-compose.yml` avec services Django, PostgreSQL et Redis interconnectés avec volumes nommés.         | **/ 2**  |
| **Variables & Healthchecks**  | Isolation stricte dans `.env`, configuration des dépendances de service (`depends_on` avec `healthcheck`). | **/ 1**  |

### 2.2.4. Qualité du Code, Tests & QA (4 pts)

| **Critère**                   | **Détail**                                                                                                 | **Note** |
| :---------------------------- | :--------------------------------------------------------------------------------------------------------- | :------- |
| **Tests Automatisés Django**  | Couverture de la logique métier (modèles, règles de jeu, vues) par des tests unitaires `TestCase`.         | **/ 2**  |
| **Linting & Propreté Git**    | Code formaté (`black`/`ruff`), historique de commits Git clair et collaboratif.                            | **/ 1**  |
| **Intégration Continue (CI)** | Pipeline GitHub Actions automatisé exécutant les tests et le linter à chaque commit/PR.                    | **/ 1**  |