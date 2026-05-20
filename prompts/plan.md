# Phase 1 — Génération du plan structuré

Ta mission ici est de **concevoir le plan détaillé** d'un ebook de la Collection Yeelen, à partir des paramètres fournis.

## Paramètres reçus

```json
{
  "sujet": "{{ sujet }}",
  "audience": "{{ audience }}",
  "pages_visees": {{ pages }},
  "ton": "{{ ton }}",
  "langue": "{{ langue }}",
  "notes_utilisateur": "{{ notes }}"
}
```

## Calibrage

À partir des pages visées, calcule la structure idéale :

| Pages | Chapitres | Sections/chapitre | Bonus |
|-------|-----------|-------------------|-------|
| 15-25 | 3 | 2-3 | 1 (glossaire OU checklist) |
| 25-40 | 4-5 | 2-3 | 2 (glossaire + checklist) |
| 40-60 | 5-6 | 3-4 | 3 (glossaire + checklist + quiz) |
| 60-100 | 7-9 | 3-5 | 3-4 (+ ressources additionnelles) |

Une page A4 contient en moyenne **350 mots** dans le format Yeelen (avec encadrés et marges). Calcule la quantité de contenu approximative.

**Important v2** : chaque section doit avoir un `longueur_estimee_mots` **minimum de 600 mots** (idéalement 700-900 pour les sections centrales). Un ebook de qualité Yeelen n'a pas de sections courtes — chaque section doit apporter assez de substance pour mériter une page complète.

## Structure de sortie obligatoire

Renvoie **uniquement un JSON valide** avec cette structure exacte :

```json
{
  "titre": "Titre principal accrocheur",
  "sous_titre": "Sous-titre descriptif et engageant",
  "deck_couverture": "Phrase courte qui apparaît sur la couverture (max 25 mots)",
  "preface": {
    "accroche": "Phrase ou statistique forte d'ouverture",
    "promesse": "Ce que le lecteur va apprendre",
    "audience": "À qui s'adresse ce livre"
  },
  "parties": [
    {
      "numero": 1,
      "titre": "Nom de la partie",
      "chapitres": [
        {
          "numero": 1,
          "titre": "Titre du chapitre",
          "deck": "Phrase courte qui ouvre le chapitre (1 phrase italique de 25-40 mots)",
          "objectifs_lecteur": [
            "Compétence 1 acquise après lecture",
            "Compétence 2",
            "Compétence 3"
          ],
          "sections": [
            {
              "numero": "1.1",
              "titre": "Titre de la section",
              "intention": "Description en 1 phrase de ce que la section couvre",
              "encadres_prevus": [
                {"type": "ANALOGY", "sujet": "Description courte de l'analogie envisagée"},
                {"type": "CALLOUT-TIP", "sujet": "Description du saviez-vous prévu"}
              ],
              "longueur_estimee_mots": 400
            }
          ],
          "encadre_a_retenir": "Idée centrale du chapitre à synthétiser en À retenir final"
        }
      ]
    }
  ],
  "bonus": [
    {"type": "glossaire", "termes_estimes": 30, "description": "Glossaire des termes techniques"},
    {"type": "checklist", "phases": ["Phase 1", "Phase 2"], "description": "..."},
    {"type": "quiz", "nb_questions": 15, "description": "..."}
  ],
  "page_finale": {
    "message_cloture": "Phrase de clôture inspirante",
    "call_to_action": ["Volume suivant suggéré", "Plateforme Yeelen PV", "Contacts"]
  },
  "estimation_pages_totales": 35,
  "logique_pedagogique": "Justification courte de la structure choisie"
}
```

## Règles éditoriales du plan

1. **Progression pédagogique** : du plus simple au plus complexe. Le chapitre 1 pose les fondamentaux, les suivants approfondissent ou appliquent.

2. **Ancrage africain** : si le sujet le permet, intégrer dans la structure des sections spécifiques au contexte africain (ex. « Adaptation au climat tropical », « Réalités économiques locales »).

3. **Équilibre théorie/pratique** : alterner sections conceptuelles et sections appliquées. Inclure systématiquement au moins 1 cas pratique chiffré par chapitre.

4. **Découpage en parties** : si plus de 4 chapitres, regrouper en 2 ou 3 parties thématiques (ex. « Comprendre / Concevoir / Installer »).

5. **Bonus pertinents** : choisir parmi glossaire, checklist d'action, quiz, fiches pratiques, études de cas approfondies — selon ce qui sert le mieux le sujet.

## Important

- Tous les titres doivent être **accrocheurs** : pas « Introduction au solaire » mais « Comprendre l'électricité avant le solaire »
- Les decks de chapitre doivent **donner envie de lire**
- Les objectifs lecteur doivent être **concrets et actionnables**
- Le JSON doit être **strictement valide** — pas de virgules en trop, pas de commentaires

Ne renvoie **rien d'autre** que le JSON. Pas de préambule, pas d'explication, pas de markdown autour.
