# Phase 2 — Rédaction d'un chapitre

Tu rédiges maintenant le **contenu intégral** d'un chapitre de l'ebook Yeelen, à partir du plan validé.

## Contexte de l'ebook

- **Titre** : {{ titre_ebook }}
- **Sous-titre** : {{ sous_titre }}
- **Audience** : {{ audience }}
- **Ton** : {{ ton }}

## Chapitre à rédiger

```json
{{ chapitre_json }}
```

## Chapitres déjà rédigés (anti-doublons)

{{ resumes_chapitres_precedents }}

---

## STANDARD DE QUALITÉ OBLIGATOIRE

Avant d'écrire la première ligne, intègre ces exigences non négociables :

### Densité minimale par section

Chaque section `## X.Y` doit contenir **au minimum 500 mots de corps de texte** (hors encadrés). Une section qui fait moins est incomplète. Le seuil minimum par chapitre complet est **1 500 mots** (hors encadrés, hors titres).

Pour atteindre cette densité, chaque section doit :
1. Ouvrir sur un **paragraphe d'accroche** (2-3 phrases qui posent le problème ou la question centrale)
2. Développer **2 à 3 sous-angles** du concept principal avec au moins 2 paragraphes chacun
3. Ancrer les explications dans **des exemples chiffrés africains** (noms de villes, de pays, de prix réels)
4. Clore sur un **paragraphe de transition** vers la suite ou un appel à l'encadré

### Encadrés obligatoires par chapitre

Un chapitre sans encadrés est un chapitre raté. Tu dois inclure :
- **MINIMUM 2 [ANALOGY]** par chapitre (jamais la même que les chapitres précédents)
- **MINIMUM 1 [CALLOUT-WARNING]** par chapitre
- **MINIMUM 1 [CALLOUT-TIP]** par chapitre
- **EXACTEMENT 1 [CALLOUT-CASE]** en fin de chapitre
- **EXACTEMENT 1 [CALLOUT-KEY]** en toute dernière position

Un [CALLOUT-DATA] est recommandé si des chiffres frappants existent sur le sujet.

### Ancrage africain systématique

Dans chaque section, intègre **au moins un** de ces éléments :
- Un chiffre réel avec source (ex. « À Bamako, l'irradiation moyenne est de 5,8 kWh/m²/jour »)
- Un exemple de terrain localisé (ex. « Dans le Sahel burkinabè... »)
- Un prix ou coût en FCFA ou contexte économique local
- Une référence climatique africaine (Harmattan, saison des pluies, chaleur tropicale)

---

## Format de sortie obligatoire

Tu rédiges chaque section avec ce **format markdown enrichi** :

```
## {{ numero_section }} {{ titre_section }}

[Paragraphe d'accroche : 2-3 phrases qui posent la question ou le problème. Commence par une phrase qui surprend ou interpelle le lecteur.]

[Développement du premier sous-angle : 3-5 phrases. Explique le concept en partant du général vers le particulier. Utilise la voix active.]

### Sous-titre si nécessaire (en MAJUSCULES ABRÉGÉES)

[Développement du deuxième sous-angle : 3-5 phrases. Donne des exemples chiffrés. Ancre dans la réalité africaine.]

[ANALOGY]
Label en 2-3 mots (ex. « Le puits et l'eau »)
Corps de l'analogie sur 4-6 phrases. Commence par une situation concrète du quotidien africain. Développe le parallèle. Conclus par le lien direct avec le concept technique. Ne jamais utiliser la même analogie que dans les chapitres précédents.
[/ANALOGY]

[Suite de l'explication technique qui reprend et prolonge l'analogie : 2-4 phrases.]

[CALLOUT-TIP]
Le saviez-vous · Titre court accrocheur
Fait surprenant, anecdote historique ou donnée inattendue en 2-4 phrases. Doit être mémorable et concret.
[/CALLOUT-TIP]

[Développement du troisième sous-angle ou approfondissement : 3-5 phrases.]

[CALLOUT-WARNING]
Erreur à éviter · Titre court
Description du piège classique. Explique POURQUOI c'est une erreur et QUELLE EST la conséquence concrète (matériel détruit, argent perdu, risque). 2-4 phrases.
[/CALLOUT-WARNING]
```

À la fin du chapitre (après toutes les sections), TOUJOURS conclure par :

```
[CALLOUT-CASE]
Cas pratique · Titre concret et localisé (ex. « Une école solaire à Kaffrine »)
Présenter la situation de départ avec des chiffres précis.
Poser le problème ou la décision à prendre.
Dérouler le raisonnement ou le calcul étape par étape.
Donner le résultat concret et actionnable.
Minimum 6 phrases. Idéalement ancré en Afrique de l'Ouest ou centrale.
[/CALLOUT-CASE]

[CALLOUT-KEY]
À retenir · Chapitre {{ numero_chapitre }}
Synthèse percutante en 2-3 phrases. Le lecteur qui ne lit QUE ce bloc doit comprendre l'essentiel du chapitre. Utilise des formules mémorables, pas du jargon.
[/CALLOUT-KEY]
```

---

## Règles de rédaction

### Style et voix

- **Voix active obligatoire** : « Le panneau capte la lumière » jamais « La lumière est captée ».
- Phrases de **15-25 mots maximum**. Couper les phrases longues en deux.
- **Bannir sans exception** : « il est important de noter », « il convient de souligner », « par ailleurs », « en effet », « ainsi », « il faut savoir que ».
- Le ton est celui d'un **mentor de terrain** qui partage son vécu, pas d'un manuel scolaire.
- Tutoyer si le contexte s'y prête (certains sujets) ou vouvoyer de façon constante — jamais mélanger.

### Vocabulaire technique

- À la **première mention** d'un terme : **[terme]** (explication courte entre parenthèses).
- Ne pas redéfinir dans le même chapitre.
- Mettre en **gras** : valeurs chiffrées importantes, termes nouveaux, mises en garde.
- Utiliser *italique* uniquement pour les concepts en cours de définition.

### Ce qu'un chapitre de qualité Yeelen doit contenir

Voici ce qui distingue un chapitre Yeelen d'un chapitre générique :

✅ Des chiffres réels et localisés (pas « environ » ou « autour de »)
✅ Des prénoms ou lieux africains dans les exemples
✅ Des analogies issues du quotidien local (marché, puits, mil, pirogue, tontine…)
✅ Des encadrés qui apportent vraiment une valeur (pas du remplissage)
✅ Des sous-titres h3 qui donnent la structure d'un coup d'œil
✅ Des paragraphes qui se suivent de façon logique et fluide
✅ Un cas pratique qui se lit comme une petite histoire avec début, problème, solution

❌ Pas de paragraphes génériques applicables à n'importe quel pays du monde
❌ Pas de répétitions entre les encadrés et le texte principal
❌ Pas de sections qui font moins de 300 mots
❌ Pas de callout KEY placé ailleurs qu'en toute dernière position

### Anti-doublons stricts

Vérifie les résumés des chapitres précédents fournis plus haut. Interdictions absolues :
- Reprendre la même analogie (même concept, même image)
- Répéter le même cas pratique ou le même exemple chiffré
- Redéfinir un terme déjà expliqué dans un autre chapitre (faire une référence courte : « comme nous l'avons vu au chapitre X »)

---

## Format de sortie

- **Markdown enrichi uniquement** (pas de HTML, pas de YAML, pas de commentaires)
- Commence directement par `## {numero}.{section} {titre}`, sans titre h1 ni préambule
- Termine obligatoirement par CALLOUT-CASE puis CALLOUT-KEY
- Aucune note méta, aucun commentaire sur le chapitre, aucun « voici le chapitre rédigé »
