# Yeelen Agent

Un générateur d'ebooks professionnels propulsé par Claude (Anthropic), conçu pour Abdoulaye Gackou et la collection Yeelen.

L'agent prend en entrée un sujet, une audience, un nombre de pages et une charte graphique, puis produit en quelques minutes un ebook complet en **PDF + DOCX + EPUB**, avec couverture pro, encadrés pédagogiques, schémas, glossaire, checklist et quiz final.

---

## Table des matières

1. [Prérequis](#prérequis)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Lancement](#lancement)
5. [Comment ça marche](#comment-ça-marche)
6. [Coûts API](#coûts-api)
7. [Personnalisation](#personnalisation)
8. [Dépannage](#dépannage)

---

## Prérequis

* **Python 3.10+** — vérifie avec `python3 --version`
* **Pandoc** — pour générer DOCX et EPUB
  * Mac : `brew install pandoc`
  * Linux : `sudo apt install pandoc`
  * Windows : <https://pandoc.org/installing.html>
* **Une clé API Anthropic** — récupère-la sur <https://console.anthropic.com/settings/keys>

Tu n'as **pas besoin** d'installer Chrome/Chromium séparément — Playwright le télécharge automatiquement.

---

## Installation

### 1. Récupère le projet

Dézippe le dossier `yeelen-agent` à l'endroit de ton choix (par exemple `~/Documents/yeelen-agent`).

### 2. Crée un environnement virtuel Python (recommandé)

```bash
cd yeelen-agent
python3 -m venv .venv
source .venv/bin/activate    # Mac/Linux
# .venv\Scripts\activate     # Windows
```

### 3. Installe les dépendances

```bash
pip install -r requirements.txt
playwright install chromium
```

L'installation de Chromium prend environ 200 Mo et 2 minutes.

---

## Configuration

### 1. Copie le fichier de configuration

```bash
cp .env.example .env
```

### 2. Édite `.env` et colle ta clé API

```
ANTHROPIC_API_KEY=sk-ant-api03-...ta-clé-réelle...
```

C'est tout. La clé n'est jamais envoyée ailleurs que sur l'API Anthropic.

---

## Lancement

```bash
python3 web/app.py
```

Tu verras ce message :

```
============================================================
  Yeelen Agent — Interface Web
============================================================
  ➤ Ouvre dans ton navigateur : http://localhost:5000
  ✓ Clé API détectée → mode live disponible
============================================================
```

Ouvre **<http://localhost:5000>** dans ton navigateur (Chrome, Firefox, Safari peu importe). L'interface s'affiche.

Pour arrêter le serveur : `Ctrl + C` dans le terminal.

---

## Comment ça marche

### Étape 1 — Tu remplis le formulaire

* **Sujet** : par exemple « L'élevage de poulets de chair en zone tropicale »
* **Audience** : par exemple « Petits éleveurs débutants en Afrique de l'Ouest »
* **Nombre de pages visées** : 20 à 80
* **Charte graphique** : 4 styles disponibles (Solaire, Agriculture, Premium, Pédagogique)
* **Ton** : tu peux personnaliser (par défaut « Vulgarisé, terrain, ancrage Afrique »)
* **Notes** : libres, pour préciser un angle, des éléments à inclure, etc.

### Étape 2 — Génération du plan (Opus)

Claude **Opus** génère un plan structuré : titre, sous-titre, parties, chapitres avec leurs sections et leurs encadrés prévus, plus les bonus. Cette étape coûte ~0,30 € et prend 30 à 60 secondes.

### Étape 3 — Validation du plan

Le plan s'affiche pour relecture. Tu peux le valider tel quel ou le rejeter (et reformuler ton sujet).

### Étape 4 — Rédaction (Sonnet)

Claude **Sonnet** rédige chaque chapitre selon les règles éditoriales Yeelen : analogies, encadrés colorés (À retenir, Erreur à éviter, Le saviez-vous, Cas pratique, Chiffres clés, Question éclair), ton vulgarisé, ancrage Afrique. Cette étape coûte ~0,30 € pour 30 pages et prend 3 à 6 minutes.

### Étape 5 — Bonus

Glossaire (40 termes), checklist d'installation/de mise en pratique (4 phases), quiz final (15 questions + corrigé). Coût : ~0,05 €.

### Étape 6 — Mise en page et export

Application automatique de la charte choisie. Génération PDF haute qualité via Chromium. Conversion en DOCX et EPUB via Pandoc. Tu télécharges les 3 fichiers depuis l'interface.

**Coût total typique pour un ebook de 30 pages : 0,60 à 0,80 €.**

---

## Coûts API

L'agent utilise une stratégie mixte pour minimiser les coûts :

| Étape       | Modèle           | Tarif (par M tokens) | Tokens typiques | Coût estimé |
|-------------|------------------|----------------------|-----------------|-------------|
| Plan        | Opus 4.7         | 15 $ in / 75 $ out   | 5k in / 3k out  | ~0,30 €     |
| Chapitres   | Sonnet 4.6       | 3 $ in / 15 $ out    | 8k in / 20k out | ~0,30 €     |
| Bonus       | Sonnet 4.6       | 3 $ in / 15 $ out    | 4k in / 4k out  | ~0,06 €     |
| **Total**   |                  |                      |                 | **~0,66 €** |

Avec **20 €/mois** de budget API, tu peux générer **environ 30 ebooks par mois**.

L'estimation de coût est affichée en temps réel dans l'interface.

---

## Personnalisation

### Changer ta photo / tes initiales sur la couverture

Édite directement les valeurs par défaut dans `generator.py` (classe `BookSpec`) ou utilise le champ « Auteur » dans le formulaire.

### Ajouter une nouvelle charte graphique

1. Crée un fichier `charters/ma-charte.css` (copie l'une des existantes comme base)
2. Modifie les variables CSS en haut du fichier (`--navy`, `--amber`, etc.)
3. Ajoute l'option dans `web/templates/index.html` (balise `<select id="charte">`)
4. Ajoute l'aperçu dans `web/static/app.js` (objet `CHARTERS`)

### Modifier le ton ou les règles éditoriales

Édite les fichiers dans `prompts/` :
* `system.md` — identité éditoriale globale, règles des encadrés
* `plan.md` — structure du plan demandé à Opus
* `chapter.md` — instructions de rédaction par chapitre
* `bonus.md` — règles pour glossaire, checklist, quiz

### Tester sans consommer d'API (mode démo)

L'agent passe automatiquement en **mode démo** si aucune clé API n'est détectée. Le plan, les chapitres et les bonus sont alors remplis avec du contenu d'exemple — utile pour tester la mise en page et le workflow sans coût.

Pour forcer le mode démo même avec une clé : ajoute `DEMO_MODE=1` dans ton `.env`.

---

## Dépannage

### « Aucun module nommé `anthropic` »

Tu n'as pas activé l'environnement virtuel ou pas installé les dépendances. Exécute :
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### « playwright._impl._errors.Error: Executable doesn't exist »

Lance :
```bash
playwright install chromium
```

### « pandoc: command not found »

Installe Pandoc (voir [Prérequis](#prérequis)).

### Le PDF a des pages vides ou tronquées

Cela peut arriver si Claude génère un chapitre très long. Solutions :
* Diminuer le nombre de pages visées dans le formulaire
* Affiner les notes pour préciser les contraintes de longueur

### Le serveur ne démarre pas (port déjà utilisé)

Édite `web/app.py` à la dernière ligne et change le port :
```python
app.run(debug=False, port=5001, host="127.0.0.1")
```

### Erreur d'API Claude (rate limit, quota, etc.)

Vérifie ton compte sur <https://console.anthropic.com>. Tu as peut-être épuisé tes crédits ou atteint la limite de requêtes par minute.

---

## Structure du projet

```
yeelen-agent/
├── generator.py              ← moteur de génération (BookSpec, BookGenerator)
├── layout.py                 ← assemblage HTML + export PDF/DOCX/EPUB
├── requirements.txt          ← dépendances Python
├── .env.example              ← modèle de configuration
├── README.md                 ← ce fichier
├── charters/                 ← 4 chartes graphiques
│   ├── solaire.css
│   ├── agriculture.css
│   ├── premium.css
│   └── pedago.css
├── prompts/                  ← intelligence éditoriale
│   ├── system.md             ← identité Yeelen, règles d'encadrés
│   ├── plan.md               ← prompt pour la génération du plan
│   ├── chapter.md            ← prompt pour la rédaction des chapitres
│   └── bonus.md              ← prompt pour glossaire/checklist/quiz
├── templates/                ← CSS partagé entre toutes chartes
│   ├── _base.css
│   └── epub.css
├── web/                      ← interface graphique
│   ├── app.py                ← serveur Flask
│   ├── templates/index.html  ← page web
│   └── static/
│       ├── style.css
│       └── app.js
└── output/                   ← ebooks générés (organisés par date)
```

---

## Crédits et contact

Conçu pour la **Collection Yeelen** par **Abdoulaye Gackou**.

* Plateforme : [yeelen-pv.com](https://yeelen-pv.com)
* LinkedIn : Abdoulaye Gackou
* Instagram : @abdgackou

Propulsé par les modèles **Claude** d'Anthropic (Opus 4.7 et Sonnet 4.6).

---

*Yeelen Agent · Édition 2026*
