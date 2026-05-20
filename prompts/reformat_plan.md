# Analyse et plan — Reformatage d'un ebook existant

Tu reçois le texte brut d'un ebook existant. Ta mission : en extraire la structure et produire un plan JSON identique à celui utilisé par le générateur Yeelen.

## Texte de l'ebook à analyser

```
{{ texte_ebook }}
```

## Instructions

1. Identifie le titre principal, le sous-titre (si présent), et l'auteur.
2. Détecte les chapitres et leurs sections à partir des titres et de la progression du texte.
3. Pour chaque section, estime le nombre de mots utiles dans le texte source.
4. Génère un plan JSON complet qui reflète fidèlement la structure existante de l'ebook.

**Important :** tu ne dois PAS inventer de nouveau contenu dans le plan. Tu dois refléter ce qui existe déjà dans le texte fourni.

## Format de sortie

Renvoie **uniquement un JSON valide**, sans préambule ni commentaire, avec cette structure exacte :

```json
{
  "titre": "Titre exact ou légèrement amélioré",
  "sous_titre": "Sous-titre si présent, sinon une phrase descriptive courte",
  "deck_couverture": "Phrase courte pour la couverture (max 25 mots)",
  "preface": {
    "accroche": "Première phrase forte du livre ou intro détectée",
    "promesse": "Ce que le livre apprend au lecteur",
    "audience": "À qui s'adresse ce livre, détecté ou inféré"
  },
  "parties": [
    {
      "numero": 1,
      "titre": "Nom de la partie ou thème détecté",
      "chapitres": [
        {
          "numero": 1,
          "titre": "Titre du chapitre tel que dans le texte",
          "deck": "Phrase d'intro du chapitre (existante ou synthétisée en 30 mots)",
          "objectifs_lecteur": [
            "Ce que le lecteur apprend dans ce chapitre",
            "Objectif 2",
            "Objectif 3"
          ],
          "sections": [
            {
              "numero": "1.1",
              "titre": "Titre de section tel que dans le texte",
              "intention": "Résumé en 1 phrase de ce que couvre la section",
              "encadres_prevus": [
                {"type": "ANALOGY", "sujet": "Analogie à intégrer"},
                {"type": "CALLOUT-KEY", "sujet": "À retenir de cette section"}
              ],
              "longueur_estimee_mots": 600
            }
          ],
          "encadre_a_retenir": "Idée centrale du chapitre"
        }
      ]
    }
  ],
  "bonus": [
    {"type": "glossaire", "termes_estimes": 25, "description": "Glossaire des termes clés"},
    {"type": "checklist", "phases": ["Phase 1", "Phase 2"], "description": "Checklist pratique"}
  ],
  "page_finale": {
    "message_cloture": "Message de clôture inspirant (existant ou créé dans l'esprit du livre)",
    "call_to_action": ["Plateforme Yeelen PV", "Contacts auteur"]
  },
  "estimation_pages_totales": 35,
  "logique_pedagogique": "Justification courte de la structure détectée"
}
```

Ne renvoie **rien d'autre** que le JSON.
