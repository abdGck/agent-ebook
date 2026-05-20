"""
Yeelen Agent — Moteur de génération d'ebooks
=============================================

Architecture :
- Opus génère le plan structuré (haute qualité de raisonnement)
- Sonnet rédige les chapitres et bonus (gros volume, qualité éditoriale)
- Assemblage HTML avec charte choisie
- Export PDF (Playwright/Chromium) + DOCX (Pandoc) + EPUB (Pandoc)

Modes :
- Mode démo : utilise du contenu d'exemple, pas d'API requise
- Mode live : utilise l'API Anthropic via la clé en variable d'environnement
"""

import os
import re
import json
import time
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime

# Anthropic SDK (optionnel : seulement requis en mode live)
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Pour le rendu HTML→PDF
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


HERE = Path(__file__).parent
PROMPTS_DIR = HERE / "prompts"
TEMPLATES_DIR = HERE / "templates"
CHARTERS_DIR = HERE / "charters"
OUTPUT_DIR = HERE / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
#   STRUCTURES DE DONNÉES
# ============================================================

@dataclass
class BookSpec:
    """Paramètres d'entrée pour la génération d'un ebook."""
    sujet: str
    audience: str  # ex: "Grand public débutant"
    pages_visees: int  # ex: 30
    ton: str  # ex: "Vulgarisé, chaleureux, ancrage Afrique"
    charte: str  # "solaire" | "agriculture" | "premium" | "pedago"
    langue: str = "français"
    notes: str = ""  # notes optionnelles de l'utilisateur
    auteur: str = "Abdoulaye Gackou"
    auteur_role: str = "Ingénieur en énergie solaire photovoltaïque"
    auteur_initiales: str = "AG"
    volume_label: str = "Volume 01"
    edition: str = "Édition 2026"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GenerationProgress:
    """Suivi de la progression d'une génération."""
    step: str = "init"  # init | plan | plan_validated | writing | rendering | done | error
    message: str = ""
    chapter_progress: int = 0
    chapter_total: int = 0
    plan: Optional[dict] = None
    chapters_md: List[str] = field(default_factory=list)
    bonus_md: str = ""
    final_files: Dict[str, str] = field(default_factory=dict)  # {pdf: path, docx: path, epub: path}
    error: str = ""
    cost_usd_estimate: float = 0.0


# ============================================================
#   CHARGEUR DE PROMPTS
# ============================================================

class PromptLibrary:
    @staticmethod
    def load(name: str) -> str:
        path = PROMPTS_DIR / f"{name}.md"
        return path.read_text(encoding="utf-8")

    @staticmethod
    def render(name: str, **kwargs) -> str:
        template = PromptLibrary.load(name)
        for key, value in kwargs.items():
            template = template.replace(f"{{{{ {key} }}}}", str(value))
        return template


# ============================================================
#   CLIENT API CLAUDE (avec fallback démo)
# ============================================================

class ClaudeClient:
    """Wrapper du client Anthropic, avec mode démo si pas de clé."""

    PRICES = {
        # Approximate USD per 1M tokens (vérifier avec docs.claude.com)
        "claude-opus-4-7":   {"input": 15.0, "output": 75.0},
        "claude-sonnet-4-6": {"input": 3.0,  "output": 15.0},
        "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
    }

    def __init__(self, api_key: Optional[str] = None, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.total_cost_usd = 0.0
        if not demo_mode:
            if not ANTHROPIC_AVAILABLE:
                raise RuntimeError(
                    "Le package 'anthropic' n'est pas installé. "
                    "Installe-le avec : pip install anthropic"
                )
            api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "Aucune clé API trouvée. "
                    "Définis ANTHROPIC_API_KEY ou utilise le mode démo."
                )
            self.client = Anthropic(api_key=api_key)

    def call(self, model: str, system: str, user: str, max_tokens: int = 4096) -> str:
        """Appel à l'API Claude (ou simulation en mode démo)."""
        if self.demo_mode:
            return self._demo_response(model, user)

        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}]
        )

        # Suivi des coûts
        usage = response.usage
        if model in self.PRICES:
            p = self.PRICES[model]
            cost = (usage.input_tokens * p["input"] + usage.output_tokens * p["output"]) / 1_000_000
            self.total_cost_usd += cost

        # Concatène le contenu
        out = ""
        for block in response.content:
            if hasattr(block, "text"):
                out += block.text
        return out

    def _demo_response(self, model: str, user_prompt: str) -> str:
        """Renvoie un contenu d'exemple selon le type de prompt détecté."""
        prompt_lower = user_prompt.lower()

        # ── MODE REFORMATAGE : extraire le vrai titre depuis le texte uploadé ──
        if "texte de l'ebook à analyser" in prompt_lower or "reformater" in prompt_lower:
            if "JSON" in user_prompt and "plan" in prompt_lower:
                return self._demo_reformat_plan(user_prompt)

        # ── MODE GÉNÉRATION CLASSIQUE ──
        if "JSON" in user_prompt and "plan" in prompt_lower:
            return DEMO_PLAN_JSON
        elif "reformater" in prompt_lower and ("chapitre" in prompt_lower or "section" in prompt_lower):
            return DEMO_CHAPTER_MD
        elif "rédige" in prompt_lower and "chapitre" in prompt_lower:
            return DEMO_CHAPTER_MD
        elif "bonus" in prompt_lower or "glossaire" in prompt_lower:
            return DEMO_BONUS_MD
        return "Contenu démo générique."

    def _demo_reformat_plan(self, user_prompt: str) -> str:
        """
        En mode démo + reformatage : génère un plan JSON minimal
        en extrayant le vrai titre depuis le texte uploadé.
        Évite de retourner le plan irrigation qui n'a rien à voir.
        """
        import re as _re

        # Tenter d'extraire un titre depuis le texte brut dans le prompt
        # Le prompt contient le texte entre ```\n...\n```
        title_guess = "Ebook reformaté"
        sous_titre_guess = "Contenu restructuré dans le style Collection Yeelen"

        # Chercher le contenu entre les balises ```
        match = _re.search(r'```\s*\n(.*?)\n```', user_prompt, _re.DOTALL)
        if match:
            raw_text = match.group(1)[:1000]
            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            # Prendre la première ligne non-vide significative (> 10 chars) comme titre
            for line in lines[:8]:
                if len(line) > 10 and not line.startswith(('http', '#', '©', 'www')):
                    # Nettoyer les artefacts PDF courants
                    cleaned = _re.sub(r'\s{2,}', ' ', line).strip()
                    if 10 < len(cleaned) < 120:
                        title_guess = cleaned
                        break

        # Générer un plan minimaliste mais cohérent avec le vrai titre
        return f'''{{
  "titre": "{title_guess}",
  "sous_titre": "{sous_titre_guess}",
  "deck_couverture": "Un guide pratique reformaté dans le style Collection Yeelen.",
  "preface": {{
    "accroche": "Ce guide a été reformaté automatiquement par le Yeelen Agent.",
    "promesse": "Contenu original conservé, mis en forme dans le style éditorial Yeelen.",
    "audience": "Grand public motivé souhaitant comprendre et agir."
  }},
  "parties": [
    {{
      "numero": 1,
      "titre": "Contenu de l'ebook",
      "chapitres": [
        {{
          "numero": 1,
          "titre": "Introduction et fondamentaux",
          "deck": "Les bases indispensables pour comprendre le sujet.",
          "objectifs_lecteur": [
            "Comprendre les concepts fondamentaux",
            "Identifier les composants clés",
            "Appréhender le contexte africain"
          ],
          "sections": [
            {{
              "numero": "1.1",
              "titre": "Contexte et enjeux",
              "intention": "Poser le problème et justifier l'importance du sujet",
              "encadres_prevus": [
                {{"type": "ANALOGY", "sujet": "Analogie du quotidien"}},
                {{"type": "CALLOUT-TIP", "sujet": "Fait marquant"}}
              ],
              "longueur_estimee_mots": 600
            }},
            {{
              "numero": "1.2",
              "titre": "Principes clés",
              "intention": "Expliquer les mécanismes essentiels",
              "encadres_prevus": [
                {{"type": "CALLOUT-WARNING", "sujet": "Erreur courante"}},
                {{"type": "CALLOUT-KEY", "sujet": "À retenir"}}
              ],
              "longueur_estimee_mots": 600
            }}
          ],
          "encadre_a_retenir": "Les fondamentaux sont la base de toute installation réussie."
        }}
      ]
    }}
  ],
  "bonus": [
    {{"type": "glossaire", "termes_estimes": 20, "description": "Glossaire des termes essentiels"}},
    {{"type": "checklist", "phases": ["Préparation", "Mise en œuvre"], "description": "Checklist pratique"}}
  ],
  "page_finale": {{
    "message_cloture": "À vous de mettre en pratique.",
    "call_to_action": ["Plateforme Yeelen PV", "Abdoulaye Gackou"]
  }},
  "estimation_pages_totales": 30,
  "logique_pedagogique": "Plan généré en mode démo depuis le texte uploadé."
}}'''


# ============================================================
#   GÉNÉRATEUR PRINCIPAL
# ============================================================

class BookGenerator:
    def __init__(self, spec: BookSpec, demo_mode: bool = False, api_key: Optional[str] = None):
        self.spec = spec
        self.demo_mode = demo_mode
        self.client = ClaudeClient(api_key=api_key, demo_mode=demo_mode)
        self.progress = GenerationProgress()

    # ---------- ÉTAPE 1 : GÉNÉRATION DU PLAN ----------

    def generate_plan(self) -> dict:
        self.progress.step = "plan"
        self.progress.message = "Génération du plan structuré (Opus)..."

        system = PromptLibrary.load("system")
        user = PromptLibrary.render("plan",
            sujet=self.spec.sujet,
            audience=self.spec.audience,
            pages=self.spec.pages_visees,
            ton=self.spec.ton,
            langue=self.spec.langue,
            notes=self.spec.notes or "(aucune)"
        )

        raw = self.client.call(
            model="claude-opus-4-7",
            system=system,
            user=user,
            max_tokens=12000
        )

        # Extrait le JSON même s'il y a du blabla autour
        plan_dict = self._extract_json(raw)
        self.progress.plan = plan_dict
        self.progress.cost_usd_estimate = self.client.total_cost_usd
        return plan_dict

    @staticmethod
    def _extract_json(raw: str) -> dict:
        # Tenter parsing direct
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        # Chercher un bloc {...} équilibré
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            return json.loads(match.group(0))
        raise ValueError("Aucun JSON valide trouvé dans la réponse de l'IA.")

    # ---------- ÉTAPE 2 : RÉDACTION DES CHAPITRES ----------

    def generate_chapters(self) -> List[str]:
        plan = self.progress.plan
        if not plan:
            raise RuntimeError("Plan manquant — appelle generate_plan() d'abord.")

        self.progress.step = "writing"
        self.progress.chapter_total = sum(len(p.get("chapitres", [])) for p in plan.get("parties", []))
        self.progress.chapters_md = []

        system = PromptLibrary.load("system")
        chapter_summaries = []

        for partie in plan.get("parties", []):
            for chap in partie.get("chapitres", []):
                self.progress.chapter_progress += 1
                self.progress.message = (
                    f"Rédaction du chapitre {self.progress.chapter_progress}/"
                    f"{self.progress.chapter_total} : {chap['titre']}"
                )
                resumes_text = "\n".join(chapter_summaries) or "(premier chapitre, aucun précédent)"
                user = PromptLibrary.render("chapter",
                    titre_ebook=plan.get("titre", ""),
                    sous_titre=plan.get("sous_titre", ""),
                    audience=self.spec.audience,
                    ton=self.spec.ton,
                    chapitre_json=json.dumps(chap, ensure_ascii=False, indent=2),
                    resumes_chapitres_precedents=resumes_text
                )
                md = self.client.call(
                    model="claude-sonnet-4-6",
                    system=system,
                    user=user,
                    max_tokens=16000
                )
                self.progress.chapters_md.append(md)
                # Petit résumé du chapitre pour anti-doublons
                chapter_summaries.append(
                    f"Chapitre {chap['numero']} : {chap['titre']} — "
                    f"sections : {', '.join(s['titre'] for s in chap.get('sections', []))}"
                )

        self.progress.cost_usd_estimate = self.client.total_cost_usd
        return self.progress.chapters_md

    # ---------- ÉTAPE 3 : BONUS ----------

    def generate_bonus(self) -> str:
        plan = self.progress.plan
        bonus_list = plan.get("bonus", [])
        if not bonus_list:
            return ""

        self.progress.step = "writing_bonus"
        self.progress.message = "Génération des bonus (glossaire, checklist, quiz)..."

        system = PromptLibrary.load("system")
        chapters_summary = "\n".join(
            f"- {c['titre']}" for p in plan.get("parties", []) for c in p.get("chapitres", [])
        )
        user = PromptLibrary.render("bonus",
            titre_ebook=plan.get("titre", ""),
            audience=self.spec.audience,
            resumes_tous_chapitres=chapters_summary,
            bonus_json=json.dumps(bonus_list, ensure_ascii=False, indent=2)
        )
        md = self.client.call(
            model="claude-sonnet-4-6",
            system=system,
            user=user,
            max_tokens=12000
        )
        self.progress.bonus_md = md
        self.progress.cost_usd_estimate = self.client.total_cost_usd
        return md

    # ---------- ÉTAPE 4 : ASSEMBLAGE ET EXPORT ----------

    def render_outputs(self) -> Dict[str, str]:
        """Génère PDF + DOCX + EPUB et retourne les chemins."""
        from layout import build_html, render_pdf, render_docx_epub

        self.progress.step = "rendering"
        self.progress.message = "Assemblage du HTML et export PDF / DOCX / EPUB..."

        # Slug pour les noms de fichiers
        slug = self._slugify(self.progress.plan.get("titre", "ebook"))
        ts = datetime.now().strftime("%Y%m%d-%H%M")
        out_base = OUTPUT_DIR / f"{slug}-{ts}"
        out_base.mkdir(parents=True, exist_ok=True)

        # 1. Build HTML pour PDF
        html_path = out_base / "ebook.html"
        css_path = out_base / "styles.css"
        build_html(
            spec=self.spec,
            plan=self.progress.plan,
            chapters_md=self.progress.chapters_md,
            bonus_md=self.progress.bonus_md,
            html_path=html_path,
            css_path=css_path
        )

        # 2. PDF via Chromium
        pdf_path = out_base / f"{slug}.pdf"
        render_pdf(html_path, pdf_path)

        # 3. Markdown unifié pour DOCX + EPUB
        md_path = out_base / "ebook.md"
        self._write_combined_markdown(md_path)

        docx_path = out_base / f"{slug}.docx"
        epub_path = out_base / f"{slug}.epub"
        render_docx_epub(md_path, docx_path, epub_path,
                         title=self.progress.plan.get("titre", ""),
                         author=self.spec.auteur)

        result = {
            "pdf": str(pdf_path),
            "docx": str(docx_path),
            "epub": str(epub_path),
            "html": str(html_path),
            "markdown": str(md_path),
        }
        self.progress.final_files = result
        self.progress.step = "done"
        self.progress.message = f"Génération terminée. {len(self.progress.chapters_md)} chapitres rédigés."
        return result

    def _write_combined_markdown(self, path: Path):
        """Concatène plan + chapitres + bonus en un seul fichier Markdown propre pour Pandoc."""
        plan = self.progress.plan
        lines = [
            "---",
            f'title: "{plan.get("titre", "")}"',
            f'subtitle: "{plan.get("sous_titre", "")}"',
            f'author: "{self.spec.auteur}"',
            f'date: "{datetime.now().year}"',
            f'language: fr-FR',
            "---",
            "",
            "# " + plan.get("titre", ""),
            "",
            f"*{plan.get('sous_titre', '')}*",
            "",
            "Par **" + self.spec.auteur + "**",
            "",
            "---",
            "",
            "# Préface",
            "",
            plan.get("preface", {}).get("accroche", ""),
            "",
            plan.get("preface", {}).get("promesse", ""),
            "",
            plan.get("preface", {}).get("audience", ""),
            "",
        ]
        # Chapitres
        for i, chap_md in enumerate(self.progress.chapters_md, 1):
            chap_data = self._find_chapter_data(i)
            if chap_data:
                lines.append(f"# Chapitre {chap_data['numero']} — {chap_data['titre']}")
                lines.append("")
                lines.append(f"*{chap_data.get('deck', '')}*")
                lines.append("")
            # Convertir les balises de callouts en markdown standard
            cleaned = self._strip_callout_tags_to_blockquotes(chap_md)
            lines.append(cleaned)
            lines.append("")
            lines.append("---")
            lines.append("")
        # Bonus
        if self.progress.bonus_md:
            lines.append(self._strip_callout_tags_to_blockquotes(self.progress.bonus_md))

        path.write_text("\n".join(lines), encoding="utf-8")

    def _find_chapter_data(self, index: int) -> Optional[dict]:
        i = 0
        for partie in self.progress.plan.get("parties", []):
            for chap in partie.get("chapitres", []):
                i += 1
                if i == index:
                    return chap
        return None

    @staticmethod
    def _strip_callout_tags_to_blockquotes(md: str) -> str:
        """Convertit [CALLOUT-XXX]...[/CALLOUT-XXX] en blockquotes markdown standards pour DOCX/EPUB."""
        patterns = [
            (r'\[CALLOUT-TIP\](.*?)\[/CALLOUT-TIP\]', r'\n> **💡 Le saviez-vous**\n>\1\n'),
            (r'\[CALLOUT-KEY\](.*?)\[/CALLOUT-KEY\]', r'\n> **✓ À retenir**\n>\1\n'),
            (r'\[CALLOUT-WARNING\](.*?)\[/CALLOUT-WARNING\]', r'\n> **⚠ Erreur à éviter**\n>\1\n'),
            (r'\[CALLOUT-CASE\](.*?)\[/CALLOUT-CASE\]', r'\n> **→ Cas pratique**\n>\1\n'),
            (r'\[CALLOUT-DATA\](.*?)\[/CALLOUT-DATA\]', r'\n> **# Chiffres clés**\n>\1\n'),
            (r'\[ANALOGY\](.*?)\[/ANALOGY\]', r'\n> *Analogie*\n>\1\n'),
        ]
        out = md
        for pat, repl in patterns:
            out = re.sub(pat, repl, out, flags=re.DOTALL)
        return out

    @staticmethod
    def _slugify(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[àáâäæ]', 'a', text)
        text = re.sub(r'[éèêë]', 'e', text)
        text = re.sub(r'[íîï]', 'i', text)
        text = re.sub(r'[óôö]', 'o', text)
        text = re.sub(r'[úûü]', 'u', text)
        text = re.sub(r'[ç]', 'c', text)
        text = re.sub(r"[^a-z0-9]+", "-", text)
        return text.strip("-")[:50] or "ebook"


# ============================================================
#   CONTENU DE DÉMO (pour tester sans clé API)
# ============================================================

DEMO_PLAN_JSON = '''{
  "titre": "L'Irrigation Solaire en Maraîchage",
  "sous_titre": "Le guide pour produire mieux, en consommant moins, sous le soleil africain.",
  "deck_couverture": "Comment l'eau, le soleil et le bon dimensionnement transforment un champ en exploitation rentable.",
  "preface": {
    "accroche": "En Afrique, plus de 70% des terres agricoles dépendent encore de la pluie. Pendant ce temps, le soleil offre chaque jour une énergie gratuite que peu d'agriculteurs exploitent.",
    "promesse": "Ce livre vous donne les clés pour concevoir, dimensionner et installer un système d'irrigation solaire adapté à votre exploitation.",
    "audience": "Pour les maraîchers, agriculteurs et techniciens qui veulent passer du diesel coûteux au solaire rentable."
  },
  "parties": [
    {
      "numero": 1,
      "titre": "Comprendre l'irrigation solaire",
      "chapitres": [
        {
          "numero": 1,
          "titre": "Pourquoi le solaire change l'agriculture",
          "deck": "Du diesel polluant à la pompe silencieuse alimentée par le soleil — une révolution discrète qui rentabilise déjà des milliers d'exploitations africaines.",
          "objectifs_lecteur": [
            "Comprendre les avantages économiques et écologiques du solaire en agriculture",
            "Identifier si votre exploitation est éligible",
            "Connaître les ordres de grandeur de coûts et économies"
          ],
          "sections": [
            {
              "numero": "1.1",
              "titre": "Les limites du modèle diesel",
              "intention": "Comprendre pourquoi le pompage diesel est en train de devenir non rentable",
              "encadres_prevus": [
                {"type": "CALLOUT-DATA", "sujet": "Coûts comparés diesel vs solaire au Sahel"},
                {"type": "CALLOUT-WARNING", "sujet": "Les coûts cachés du diesel"}
              ],
              "longueur_estimee_mots": 350
            },
            {
              "numero": "1.2",
              "titre": "Comment fonctionne une pompe solaire",
              "intention": "Expliquer simplement le principe technique",
              "encadres_prevus": [
                {"type": "ANALOGY", "sujet": "Le soleil comme source, la pompe comme cœur"},
                {"type": "CALLOUT-TIP", "sujet": "Le saviez-vous sur les pompes immergées"}
              ],
              "longueur_estimee_mots": 400
            }
          ],
          "encadre_a_retenir": "Le solaire transforme un coût variable (carburant) en investissement rentabilisé sur 4-6 ans."
        }
      ]
    }
  ],
  "bonus": [
    {"type": "glossaire", "termes_estimes": 25, "description": "Termes techniques de l'irrigation solaire"},
    {"type": "checklist", "phases": ["Avant projet", "Installation", "Maintenance"], "description": "Checklist projet"}
  ],
  "page_finale": {
    "message_cloture": "Le soleil ne facture jamais. À vous de récolter.",
    "call_to_action": ["Volume sur le pompage avancé", "Plateforme Yeelen PV", "Contacts"]
  },
  "estimation_pages_totales": 28,
  "logique_pedagogique": "Plan en 1 partie pour un MVP démo. Progression du pourquoi vers le comment, avec ancrage économique africain dès le chapitre 1."
}'''

DEMO_CHAPTER_MD = """## 1.1 Les limites du modèle diesel

Pendant des décennies, le groupe électrogène a été le compagnon obligé des exploitations agricoles éloignées du réseau. Il pompe l'eau, il fait tourner les broyeurs, il alimente les chambres froides. Mais ce compagnon coûte de plus en plus cher — et il pollue.

Le carburant représente aujourd'hui **40 à 60 %** du coût d'exploitation d'une pompe diesel sur sa durée de vie. Au Mali, en 2024, un agriculteur qui pompe 8 heures par jour dépense en moyenne **350 000 FCFA** par mois en gasoil. Sur 10 ans, c'est plus de 40 millions de FCFA — sans compter les pannes, l'entretien, le bruit, la pollution.

[ANALOGY]
La pompe et le coffre-fort
Une pompe diesel, c'est comme un coffre-fort dans lequel vous remettriez de l'argent chaque semaine sans jamais en sortir. Elle vous demande, semaine après semaine, du carburant pour fonctionner. La pompe solaire, à l'inverse, c'est un coffre-fort qui s'auto-alimente : une fois acheté, il ne réclame plus rien — juste un peu d'entretien annuel.
[/ANALOGY]

[CALLOUT-DATA]
Chiffres clés · Diesel vs solaire au Sahel
- 350 000 | FCFA/mois | Coût moyen de carburant pour pompe 5 kW
- 0 | FCFA/mois | Coût d'exploitation d'une pompe solaire équivalente
- 4-6 | ans | Durée de retour sur investissement d'un système solaire
[/CALLOUT-DATA]

[CALLOUT-WARNING]
Erreur à éviter · Les coûts cachés du diesel
On compare souvent diesel et solaire sur le seul prix d'achat — c'est trompeur. Le diesel, c'est aussi : la corvée de carburant, les pannes fréquentes, le bruit insupportable, la pollution locale, et la dépendance aux fluctuations du prix du gasoil. Sur 10 ans, le solaire est en moyenne **3 à 5 fois moins cher**.
[/CALLOUT-WARNING]

## 1.2 Comment fonctionne une pompe solaire

Une pompe solaire, c'est un système simple en apparence : des panneaux qui captent la lumière, un convertisseur qui transforme cette énergie, et une pompe qui aspire l'eau du puits ou du forage pour l'envoyer dans le réseau d'irrigation.

Mais derrière cette simplicité, il y a un savoir-faire — celui de bien dimensionner chaque élément pour qu'il fonctionne en harmonie avec les autres, et avec les besoins réels de l'exploitation.

[CALLOUT-TIP]
Le saviez-vous · Les pompes immergées
Les pompes solaires modernes sont souvent immergées au fond du puits, contrairement aux anciennes pompes de surface. Cette configuration offre **30 à 50 % de meilleur rendement**, élimine les problèmes d'amorçage, et protège le moteur de la chaleur.
[/CALLOUT-TIP]

[CALLOUT-CASE]
Cas pratique · Maraîcher de 1 hectare au Burkina Faso
Mariam exploite 1 hectare d'oignons et de tomates près de Bobo-Dioulasso. Besoin estimé : 30 m³ d'eau par jour pendant 6 mois. Sa pompe solaire : 4 panneaux de 400 Wc (1,6 kWc), une pompe immergée 1,5 kW à 30 m de profondeur. Investissement total : 2,8 millions de FCFA. Économie sur le diesel : 280 000 FCFA par mois. Retour sur investissement : **10 mois**.
[/CALLOUT-CASE]

[CALLOUT-KEY]
À retenir · Chapitre 1
Le solaire transforme la dépendance au carburant en investissement rentabilisé. Sur 10 ans, l'irrigation solaire revient **3 à 5 fois moins cher** qu'au diesel. La clé : un dimensionnement adapté à votre puits, votre culture et vos besoins en eau réels.
[/CALLOUT-KEY]
"""

DEMO_BONUS_MD = """# Bonus 1 · Glossaire

**Ampère (A)** — Unité de mesure de l'intensité du courant électrique.

**Débit (m³/h)** — Quantité d'eau qu'une pompe peut fournir par heure.

**Hauteur manométrique (HMT)** — Différence de hauteur entre la source d'eau et le point de sortie, exprimée en mètres.

**Pompe immergée** — Pompe placée au fond du puits ou du forage, plus efficace qu'une pompe de surface.

**Puissance crête (Wc)** — Puissance maximale d'un panneau solaire en conditions standard.

**Réseau goutte-à-goutte** — Système d'irrigation économe qui distribue l'eau près des racines.

---

# Bonus 2 · Checklist d'installation

## Phase 1 · Avant projet

- [ ] **Mesurer le débit du puits** — déterminer combien de m³/h le puits peut fournir sans s'épuiser.
- [ ] **Calculer le besoin en eau** — m³/jour selon la surface et la culture.
- [ ] **Mesurer la HMT** — différence de hauteur entre niveau d'eau dynamique et point d'arrivée.

## Phase 2 · Installation

- [ ] **Orientation des panneaux** — plein sud (hémisphère nord), inclinaison 15-20°.
- [ ] **Câbles de section adaptée** — pour éviter les pertes en ligne sur les longues distances.

## Phase 3 · Maintenance

- [ ] **Nettoyage trimestriel** des panneaux.
- [ ] **Vidange annuelle** de la pompe immergée si possible.

> **Conseil de pro.** Toujours surdimensionner légèrement (15-20%) le champ solaire. La poussière, le vieillissement et les jours nuageux finiront par grignoter cette marge.
"""


# ============================================================
#   UTILITAIRE EN LIGNE DE COMMANDE (test rapide)
# ============================================================

if __name__ == "__main__":
    print("Yeelen Agent — test démo")
    spec = BookSpec(
        sujet="Irrigation solaire pour le maraîchage en Afrique",
        audience="Maraîchers et agriculteurs francophones",
        pages_visees=30,
        ton="Vulgarisé, ancré Afrique, chaleureux",
        charte="agriculture",
        notes="Insister sur l'aspect rentabilité et retour sur investissement"
    )
    gen = BookGenerator(spec, demo_mode=True)
    print("→ Plan...")
    plan = gen.generate_plan()
    print(f"  Titre : {plan['titre']}")
    print(f"  Estimation : {plan.get('estimation_pages_totales')} pages")
    print("→ Chapitres...")
    chapters = gen.generate_chapters()
    print(f"  {len(chapters)} chapitre(s) rédigé(s)")
    print("→ Bonus...")
    gen.generate_bonus()
    print("→ Export...")
    files = gen.render_outputs()
    print("Fichiers générés :")
    for k, v in files.items():
        print(f"  {k}: {v}")


# ============================================================
#   EXTRACTEUR DE TEXTE (PDF / EPUB / DOCX / TXT)
# ============================================================

def extract_text_from_file(file_path: Path) -> str:
    """
    Extrait le texte brut d'un fichier ebook.
    Supporte : PDF, EPUB, DOCX, TXT, MD.
    """
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(file_path)
    elif suffix == ".epub":
        return _extract_epub(file_path)
    elif suffix in (".docx", ".doc"):
        return _extract_docx(file_path)
    elif suffix in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Format non supporté : {suffix}. Utilise PDF, EPUB, DOCX ou TXT.")


def _extract_pdf(file_path: Path) -> str:
    try:
        import pdfplumber
        pages_text = []
        with pdfplumber.open(str(file_path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages_text.append(t)
        return "\n\n".join(pages_text)
    except ImportError:
        # Fallback pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            return "\n\n".join(
                p.extract_text() for p in reader.pages if p.extract_text()
            )
        except ImportError:
            raise RuntimeError(
                "Aucune lib PDF disponible. "
                "Installe pdfplumber : pip install pdfplumber"
            )


def _extract_epub(file_path: Path) -> str:
    """Extrait le texte d'un EPUB via décompression ZIP + nettoyage HTML."""
    import zipfile
    import html
    from html.parser import HTMLParser

    class _TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text_parts = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "head"):
                self._skip = True
            elif tag in ("h1", "h2", "h3", "h4", "p", "li", "div", "br"):
                self.text_parts.append("\n")

        def handle_endtag(self, tag):
            if tag in ("script", "style", "head"):
                self._skip = False
            if tag in ("h1", "h2", "h3", "h4", "p", "li"):
                self.text_parts.append("\n")

        def handle_data(self, data):
            if not self._skip:
                self.text_parts.append(data)

        def get_text(self):
            return html.unescape("".join(self.text_parts))

    texts = []
    with zipfile.ZipFile(str(file_path), "r") as z:
        # Trier les fichiers HTML par nom (ordre logique)
        html_files = sorted(
            [n for n in z.namelist() if n.endswith((".html", ".xhtml", ".htm"))
             and not n.startswith("__MACOSX")]
        )
        for name in html_files:
            raw = z.read(name).decode("utf-8", errors="replace")
            parser = _TextExtractor()
            parser.feed(raw)
            chunk = parser.get_text().strip()
            if chunk:
                texts.append(chunk)
    return "\n\n".join(texts)


def _extract_docx(file_path: Path) -> str:
    try:
        import docx
        doc = docx.Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        raise RuntimeError(
            "python-docx non installé. "
            "Installe-le : pip install python-docx"
        )


# ============================================================
#   REFORMATEUR D'EBOOK EXISTANT
# ============================================================

class EbookReformatter:
    """
    Reformate un ebook existant dans le style Collection Yeelen.
    Prend le texte extrait d'un fichier et produit PDF + DOCX + EPUB.
    """

    def __init__(self, spec: "BookSpec", extracted_text: str,
                 demo_mode: bool = False, api_key: Optional[str] = None):
        self.spec = spec
        self.extracted_text = extracted_text
        self.client = ClaudeClient(api_key=api_key, demo_mode=demo_mode)
        self.progress = GenerationProgress()
        # Tronquer le texte si trop long (limite contexte)
        self._text_truncated = extracted_text[:80_000]

    def generate_plan(self) -> dict:
        """Phase 1 : Analyser le texte et produire un plan structuré."""
        self.progress.step = "plan"
        self.progress.message = "Analyse de l'ebook et génération du plan (Opus)..."

        system = PromptLibrary.load("system")
        user = PromptLibrary.render("reformat_plan",
            texte_ebook=self._text_truncated
        )
        raw = self.client.call(
            model="claude-opus-4-7",
            system=system,
            user=user,
            max_tokens=12000
        )
        plan = BookGenerator._extract_json(raw)
        self.progress.plan = plan
        self.progress.cost_usd_estimate = self.client.total_cost_usd
        return plan

    def reformat_chapters(self) -> List[str]:
        """Phase 2 : Reformater chaque chapitre dans le style Yeelen."""
        plan = self.progress.plan
        if not plan:
            raise RuntimeError("Plan manquant — appelle generate_plan() d'abord.")

        self.progress.step = "writing"
        all_chapitres = [
            (partie, chap)
            for partie in plan.get("parties", [])
            for chap in partie.get("chapitres", [])
        ]
        self.progress.chapter_total = len(all_chapitres)
        self.progress.chapters_md = []

        system = PromptLibrary.load("system")
        chapter_summaries = []

        for i, (partie, chap) in enumerate(all_chapitres):
            self.progress.chapter_progress = i + 1
            self.progress.message = (
                f"Reformatage du chapitre {i+1}/{len(all_chapitres)} : {chap['titre']}"
            )
            # Extraire la portion du texte correspondant à ce chapitre
            chapitre_text = self._extract_chapter_text(chap, i, len(all_chapitres))
            resumes_text = "\n".join(chapter_summaries) or "(premier chapitre)"

            user = PromptLibrary.render("reformat_chapter",
                titre_ebook=plan.get("titre", ""),
                audience=self.spec.audience,
                ton=self.spec.ton,
                chapitre_json=json.dumps(chap, ensure_ascii=False, indent=2),
                texte_chapitre=chapitre_text,
                resumes_chapitres_precedents=resumes_text,
                numero_chapitre=chap.get("numero", i + 1)
            )
            md = self.client.call(
                model="claude-sonnet-4-6",
                system=system,
                user=user,
                max_tokens=16000
            )
            self.progress.chapters_md.append(md)
            chapter_summaries.append(
                f"Chapitre {chap.get('numero', i+1)} : {chap['titre']}"
            )

        self.progress.cost_usd_estimate = self.client.total_cost_usd
        return self.progress.chapters_md

    def generate_bonus(self) -> str:
        """Phase 3 : Générer le glossaire et checklist depuis le texte existant."""
        plan = self.progress.plan
        bonus_list = plan.get("bonus", [])
        if not bonus_list:
            return ""

        self.progress.step = "writing_bonus"
        self.progress.message = "Génération des bonus..."

        system = PromptLibrary.load("system")
        chapters_summary = "\n".join(
            f"- {c['titre']}"
            for p in plan.get("parties", [])
            for c in p.get("chapitres", [])
        )
        user = PromptLibrary.render("bonus",
            titre_ebook=plan.get("titre", ""),
            audience=self.spec.audience,
            resumes_tous_chapitres=chapters_summary,
            bonus_json=json.dumps(bonus_list, ensure_ascii=False, indent=2)
        )
        md = self.client.call(
            model="claude-sonnet-4-6",
            system=system,
            user=user,
            max_tokens=12000
        )
        self.progress.bonus_md = md
        self.progress.cost_usd_estimate = self.client.total_cost_usd
        return md

    def render_outputs(self) -> Dict[str, str]:
        """Phase 4 : Assembler et exporter PDF + DOCX + EPUB."""
        from layout import build_html, render_pdf, render_docx_epub

        self.progress.step = "rendering"
        self.progress.message = "Assemblage et export PDF / DOCX / EPUB..."

        slug = BookGenerator._slugify(self.progress.plan.get("titre", "ebook"))
        ts = datetime.now().strftime("%Y%m%d-%H%M")
        out_base = OUTPUT_DIR / f"reformat-{slug}-{ts}"
        out_base.mkdir(parents=True, exist_ok=True)

        html_path = out_base / "ebook.html"
        css_path = out_base / "styles.css"
        build_html(
            spec=self.spec,
            plan=self.progress.plan,
            chapters_md=self.progress.chapters_md,
            bonus_md=self.progress.bonus_md,
            html_path=html_path,
            css_path=css_path
        )

        pdf_path = out_base / f"{slug}.pdf"
        render_pdf(html_path, pdf_path)

        md_path = out_base / "ebook.md"
        # Markdown unifié simple pour DOCX/EPUB
        lines = [f"# {self.progress.plan.get('titre', '')}\n"]
        for md in self.progress.chapters_md:
            lines.append(BookGenerator._strip_callout_tags_to_blockquotes(md))
            lines.append("\n---\n")
        if self.progress.bonus_md:
            lines.append(
                BookGenerator._strip_callout_tags_to_blockquotes(self.progress.bonus_md)
            )
        md_path.write_text("\n".join(lines), encoding="utf-8")

        docx_path = out_base / f"{slug}.docx"
        epub_path = out_base / f"{slug}.epub"
        render_docx_epub(md_path, docx_path, epub_path,
                         title=self.progress.plan.get("titre", ""),
                         author=self.spec.auteur)

        result = {
            "pdf": str(pdf_path),
            "docx": str(docx_path),
            "epub": str(epub_path),
            "html": str(html_path),
        }
        self.progress.final_files = result
        self.progress.step = "done"
        self.progress.message = "Reformatage terminé."
        return result

    def _extract_chapter_text(self, chap: dict, index: int, total: int) -> str:
        """
        Extrait approximativement la portion du texte source correspondant au chapitre.
        Stratégie : diviser le texte en `total` parties égales, prendre la partie `index`.
        Si le texte contient des marqueurs de chapitre clairs, les utiliser.
        """
        text = self._text_truncated
        # Chercher le titre du chapitre dans le texte
        titre = chap.get("titre", "")
        idx = text.find(titre)
        if idx != -1:
            # Prendre le texte à partir de ce titre jusqu'au prochain titre de chapitre
            # ou jusqu'à la fin si dernier chapitre
            all_titres = [
                c.get("titre", "")
                for p in self.progress.plan.get("parties", [])
                for c in p.get("chapitres", [])
            ]
            next_title_idx = len(text)
            for next_titre in all_titres[index + 1:]:
                pos = text.find(next_titre, idx + len(titre))
                if pos != -1:
                    next_title_idx = pos
                    break
            return text[idx:next_title_idx][:20_000]
        else:
            # Fallback : division uniforme
            chunk_size = len(text) // total if total > 0 else len(text)
            start = index * chunk_size
            return text[start:start + chunk_size][:20_000]
