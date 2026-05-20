# Phase 2 — Reformatage d'un chapitre existant

Tu reçois un chapitre d'un ebook existant. Ta mission : **conserver l'intégralité du contenu**, mais le reformater dans le style éditorial de la Collection Yeelen — plus dense, plus pédagogique, avec des analogies, des encadrés, et un ancrage africain si le sujet le permet.

## Contexte de l'ebook

- **Titre** : {{ titre_ebook }}
- **Audience** : {{ audience }}
- **Ton** : {{ ton }}

## Chapitre à reformater

Structure attendue (issue du plan) :
```json
{{ chapitre_json }}
```

## Texte original de ce chapitre

```
{{ texte_chapitre }}
```

## Chapitres déjà traités (anti-doublons)

{{ resumes_chapitres_precedents }}

---

## Règles de reformatage

### Ce que tu dois faire

1. **Conserver tout le contenu factuel** du texte original — aucune information ne doit être perdue.
2. **Restructurer** en sections `## X.Y Titre` correspondant au plan fourni.
3. **Enrichir chaque section** avec :
   - Des sous-titres h3 pour découper les sous-thèmes
   - Au moins **1 ANALOGY** par section longue (jamais la même que les chapitres précédents)
   - Des données chiffrées mises en valeur (**gras**)
   - Un **CALLOUT-WARNING** si le texte signale un risque ou une erreur courante
   - Un **CALLOUT-TIP** si le texte contient une info intéressante ou surprenante
4. Terminer par **CALLOUT-CASE** (cas pratique africain, inventé si absent du texte) et **CALLOUT-KEY** (synthèse).

### Ce que tu ne dois PAS faire

- ❌ Inventer des faits qui ne sont pas dans le texte original
- ❌ Supprimer des informations présentes dans le texte original
- ❌ Réduire la longueur — si le texte original fait 500 mots, ta sortie doit en faire **au moins 700** (tu peux développer les explications, ajouter des exemples, mais pas supprimer)
- ❌ Produire une section de moins de 400 mots

### Format des encadrés (obligatoire)

```
[ANALOGY]
Label court (2-3 mots)
Corps de l'analogie en 3-5 phrases. Partir d'une image concrète du quotidien, finir par le lien avec le concept technique.
[/ANALOGY]

[CALLOUT-TIP]
Le saviez-vous · Titre court
Corps en 2-4 phrases.
[/CALLOUT-TIP]

[CALLOUT-WARNING]
Erreur à éviter · Titre court
Corps en 2-4 phrases avec la conséquence concrète.
[/CALLOUT-WARNING]

[CALLOUT-CASE]
Cas pratique · Titre concret
Situation de départ → raisonnement → résultat. Minimum 5 phrases.
[/CALLOUT-CASE]

[CALLOUT-KEY]
À retenir · Chapitre {{ numero_chapitre }}
Synthèse en 2-3 phrases. Le lecteur qui ne lit QUE ce bloc doit comprendre l'essentiel.
[/CALLOUT-KEY]
```

## Format de sortie

- Markdown enrichi uniquement
- Commence directement par `## {numero}.{section} {titre}`
- Termine par CALLOUT-CASE puis CALLOUT-KEY
- Aucun commentaire méta
