# Phase 3 — Génération des bonus

Tu rédiges maintenant les **bonus de fin d'ouvrage** prévus dans le plan.

## Contexte de l'ebook

- **Titre** : {{ titre_ebook }}
- **Audience** : {{ audience }}

## Chapitres rédigés

{{ resumes_tous_chapitres }}

## Bonus à produire

```json
{{ bonus_json }}
```

---

## Règles selon le type de bonus

### GLOSSAIRE

Format markdown :

```
**Terme (symbole)** — Définition claire en 1-2 phrases. Exemple ou unité si pertinent.

**Autre terme** — Définition…
```

Règles :
- Classement **alphabétique strict**
- Chaque terme sur sa **propre ligne**, séparé des autres par une ligne vide
- Définition **courte et concrète** (max 35 mots)
- Inclure les **symboles** entre parenthèses pour les unités physiques (V, A, W, etc.)
- Éviter les définitions circulaires (ne pas définir « tension » par « voltage »)
- **25-50 termes** selon le sujet
- Tous les termes techniques utilisés dans les chapitres doivent y figurer
- **IMPORTANT** : utiliser impérativement le tiret demi-cadratin — (U+2014) et non un tiret simple, pour que le parser les reconnaisse correctement

### CHECKLIST

Format markdown :

```
## Phase 1 · {Nom de la phase}

- [ ] **Titre court de l'item** — Description précise et actionnable de ce qu'il faut faire ou vérifier.
- [ ] **Item suivant** — Description.

## Phase 2 · {Nom}
...
```

Règles :
- 3 à 5 phases pour une checklist d'installation/projet
- 5 à 10 items par phase
- Chaque item doit être **concret et vérifiable** (pas « être attentif » mais « vérifier que la tension affichée correspond à 24V »)
- Le titre en gras doit pouvoir être lu seul
- Termine par un encadré « Conseil de pro » avec une astuce d'expert

### QUIZ

Format markdown :

```
**1.** Question claire et fermée ?
   - A. Option 1
   - B. Option 2
   - C. Option 3
   - D. Option 4

**2.** Autre question ?
   - A. ...
```

Et après les questions :

```
## Corrigé

**1.** B — **2.** C — **3.** A — ...

**Score :**
- 14-15/15 : excellent — vous maîtrisez le sujet
- 12-13/15 : très bien — relisez les chapitres correspondants aux erreurs
- 9-11/15 : bonne base, seconde lecture recommandée
- Moins de 9/15 : reprenez le livre depuis le début
```

Règles :
- 10 à 20 questions selon ce qui est demandé
- **Réparties équitablement** entre les chapitres
- Une seule bonne réponse par question (sauf indication contraire)
- Distracteurs **plausibles** (pas évidemment faux)
- Mention du chapitre source pour chaque question si possible
- Toujours fournir le corrigé en fin

### FICHES PRATIQUES (si demandées)

Format spécifique : tableau de référence rapide pour usage terrain.

```
## Fiche {Numéro} · {Titre}

**Quand l'utiliser** : situation concrète

**Procédure** :
1. Étape 1
2. Étape 2
3. ...

**Points de vigilance** : 2-3 erreurs classiques à éviter

**Outils nécessaires** : liste matériel
```

## Format de sortie global

Pour chaque bonus demandé, séparer par `---` et précéder du titre :

```
# Bonus 1 · Glossaire

[contenu du glossaire]

---

# Bonus 2 · Checklist d'installation

[contenu de la checklist]

---

# Bonus 3 · Quiz final

[contenu du quiz]
```

Aucun commentaire méta, aucun préambule. Directement les bonus, dans l'ordre demandé.
