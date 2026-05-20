"""
Yeelen Agent — Module de mise en page v2
=======================================

CHANGELOG v2 :
  - _render_content_pages : scinde le contenu par section H2 (une div.page par section)
  - _render_bonus_pages   : scinde les bonus par '# Bonus N', glossaire structuré
  - _render_glossary_html : rendu proper avec .glossary-entry + lettres + 2 colonnes
  - _render_analogy       : bold/italic appliqués à l'intérieur
  - _render_callout       : bold/italic appliqués au corps
  - _markdown_to_html     : '---' → <hr>, checklist [ ] reconnue
  - _convert_md_tables    : inline markdown dans les cellules
"""

import re
import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).parent
TEMPLATES_DIR = HERE / "templates"
CHARTERS_DIR = HERE / "charters"


# ============================================================
#   ASSEMBLAGE HTML
# ============================================================

def build_html(spec, plan: dict, chapters_md: List[str], bonus_md: str,
               html_path: Path, css_path: Path):

    base_css = (TEMPLATES_DIR / "_base.css").read_text(encoding="utf-8")
    charter_path = CHARTERS_DIR / f"{spec.charte}.css"
    if not charter_path.exists():
        charter_path = CHARTERS_DIR / "solaire.css"
    charter_css = charter_path.read_text(encoding="utf-8")
    css_path.write_text(charter_css + "\n\n" + base_css, encoding="utf-8")

    pages = []

    pages.append(_render_cover(spec, plan))
    pages.append(_render_author_page(spec, plan))
    pages.append(_render_preface_page(spec, plan))
    pages.append(_render_toc_page(spec, plan))

    current_page = 5
    chap_index = 0
    for partie in plan.get("parties", []):
        for chap in partie.get("chapitres", []):
            chap_index += 1
            pages.append(_render_chapter_opener(chap, partie))
            current_page += 1
            content_md = chapters_md[chap_index - 1]
            content_html = _markdown_to_html(content_md)
            section_pages = _render_content_pages(chap, partie, content_html, current_page)
            pages.extend(section_pages)
            current_page += len(section_pages)

    if bonus_md:
        pages.append(_render_part_divider(
            label="Section bonus", big_letter="B",
            title="Ressources pour aller plus loin.",
            deck="Glossaire, checklist et autres bonus pratiques pour transformer la lecture en action."
        ))
        current_page += 1
        bonus_pages = _render_bonus_pages(bonus_md, current_page)
        pages.extend(bonus_pages)
        current_page += len(bonus_pages)

    pages.append(_render_end_page(spec, plan, current_page))

    full_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>{_esc(plan.get('titre', 'Ebook'))}</title>
<link rel="stylesheet" href="{css_path.name}">
</head>
<body>
{''.join(pages)}
</body>
</html>"""
    html_path.write_text(full_html, encoding="utf-8")


# ============================================================
#   UTILITAIRES
# ============================================================

def _esc(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _inline_md(text: str) -> str:
    """Applique gras et italique sans echapper (le texte peut déjà contenir du HTML safe)."""
    out = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    out = re.sub(r'(?<![a-zA-Z*])\*([^*\n]+?)\*(?![a-zA-Z*])', r'<em>\1</em>', out)
    return out


# ============================================================
#   PAGES STRUCTURELLES
# ============================================================

def _render_cover(spec, plan: dict) -> str:
    return f"""
<div class="cover">
  <div class="cover-bg"></div><div class="cover-grid"></div><div class="cover-shape"></div>
  <div class="cover-content">
    <div class="cover-top"><span class="cover-top-line"></span>Collection Yeelen</div>
    <div class="cover-title-block">
      <div class="cover-volume">{_esc(spec.volume_label)} · {_esc(spec.edition)}</div>
      <h1 class="cover-title">{_esc(plan.get('titre', ''))}</h1>
      <div class="cover-subtitle">{_esc(plan.get('sous_titre', ''))}</div>
    </div>
    <div class="cover-bottom">
      <div class="cover-author">
        <div class="cover-author-name">{_esc(spec.auteur)}</div>
        <div class="cover-author-role">{_esc(spec.auteur_role)}</div>
      </div>
      <div class="cover-brand">
        <div class="cover-brand-name">YEELEN</div>
        <div class="cover-brand-tag">PV · Solar · SD</div>
      </div>
    </div>
  </div>
</div>"""


def _render_author_page(spec, plan: dict) -> str:
    accroche = plan.get("preface", {}).get("accroche", "")
    return f"""
<div class="page author-page">
  <div class="page-header">
    <span><span class="brand">Yeelen</span> · Collection</span>
    <span>{_esc(plan.get('titre', ''))}</span>
  </div>
  <div class="author-eyebrow">À propos du livre · L'auteur</div>
  <h1 class="author-title">Bienvenue dans la Collection Yeelen.</h1>
  <div class="author-grid">
    <div class="author-photo">{_esc(spec.auteur_initiales)}</div>
    <div class="author-bio">
      <p class="lead">{_esc(accroche)}</p>
      <p>Je suis {_esc(spec.auteur)}, {_esc(spec.auteur_role)}, fondateur de Yeelen Solar et de RE Consulting, et président de l'association Yeelen for Sustainable Development.</p>
      <p>Au fil des années, j'ai conduit des projets d'électrification au Mali et dans plusieurs pays d'Afrique, formé des centaines de personnes et accompagné des institutions internationales dans leurs études de faisabilité.</p>
      <p>Cet ouvrage s'inscrit dans la même mission : rendre accessible ce qui est souvent réservé aux experts.</p>
      <div class="author-credits">
        <div><div class="credit-num">10+</div><div class="credit-label">Années d'expérience terrain</div></div>
        <div><div class="credit-num">300+</div><div class="credit-label">Personnes formées au solaire</div></div>
        <div><div class="credit-num">15+</div><div class="credit-label">Projets internationaux livrés</div></div>
      </div>
      <div class="author-socials">
        <div class="social-pill"><strong>Yeelen PV</strong> · Plateforme en ligne</div>
        <div class="social-pill"><strong>LinkedIn</strong> · Abdoulaye Gackou</div>
        <div class="social-pill"><strong>Instagram</strong> · @abdgackou</div>
      </div>
    </div>
  </div>
  <div class="page-footer">
    <span>Collection Yeelen · {_esc(spec.volume_label)}</span>
    <span class="pagenum">02</span>
  </div>
</div>"""


def _render_preface_page(spec, plan: dict) -> str:
    pref = plan.get("preface", {})
    accroche = pref.get("accroche", "")
    promesse = pref.get("promesse", "")
    audience = pref.get("audience", "")
    return f"""
<div class="page content-page">
  <div class="page-header">
    <span><span class="brand">Yeelen</span> · Préface</span>
    <span>{_esc(plan.get('titre', ''))}</span>
  </div>
  <h2 class="dropcap">¶&nbsp; Pourquoi ce livre existe</h2>
  <p class="dropcap">{_esc(accroche)}</p>
  <p>{_esc(promesse)}</p>
  <h3>À qui s'adresse ce livre ?</h3>
  <p>{_esc(audience)}</p>
  <div class="callout callout-key" style="margin-top:8mm;">
    <div class="callout-label"><span class="callout-icon">✓</span>Comment lire ce livre</div>
    <div class="callout-body"><p>Vous pouvez le lire de bout en bout ou consulter chaque chapitre indépendamment. Les <strong>encadrés colorés</strong> rythment la lecture : les blocs verts résument les points clés, les rouges signalent les pièges, les bleus illustrent par des cas concrets. Les bonus en fin d'ouvrage sont conçus pour être imprimés et utilisés sur le terrain.</p></div>
  </div>
  <div style="margin-top:14mm;text-align:right;font-family:'Lora',serif;font-style:italic;color:var(--ink-soft);">
    <div>{_esc(spec.auteur)}</div>
    <div style="font-size:10pt;margin-top:1mm;">{_esc(spec.edition)}</div>
  </div>
  <div class="page-footer">
    <span>Collection Yeelen · {_esc(spec.volume_label)}</span>
    <span class="pagenum">03</span>
  </div>
</div>"""


def _render_toc_page(spec, plan: dict) -> str:
    bonus = plan.get("bonus", [])
    parties = plan.get("parties", [])
    nb_chap = sum(len(p.get("chapitres", [])) for p in parties)

    toc_rows = []
    page_est = 5
    for partie in parties:
        toc_rows.append(f'<div class="toc-section-divider">{_esc(partie["titre"])}</div>')
        for chap in partie.get("chapitres", []):
            subs = " · ".join(s["titre"] for s in chap.get("sections", []))
            toc_rows.append(f"""
<div class="toc-chapter">
  <div class="toc-num">{chap['numero']:02d}</div>
  <div class="toc-titles">
    <div class="toc-chap-title">{_esc(chap['titre'])}</div>
    <div class="toc-chap-sub">{_esc(subs)}</div>
  </div>
  <div class="toc-page-num">{page_est:02d}</div>
</div>""")
            page_est += 4

    if bonus:
        toc_rows.append('<div class="toc-section-divider">Bonus · Ressources pour aller plus loin</div>')
        for i, b in enumerate(bonus, 1):
            label = b.get("type", "bonus").capitalize()
            desc = b.get("description", "")
            toc_rows.append(f"""
<div class="toc-chapter">
  <div class="toc-num" style="font-size:14pt;">B{i}</div>
  <div class="toc-titles">
    <div class="toc-chap-title">{_esc(label)}</div>
    <div class="toc-chap-sub">{_esc(desc)}</div>
  </div>
  <div class="toc-page-num">{page_est:02d}</div>
</div>""")
            page_est += 2

    return f"""
<div class="page toc-page">
  <div class="page-header">
    <span><span class="brand">Yeelen</span> · Sommaire</span>
    <span>{_esc(plan.get('titre', ''))}</span>
  </div>
  <div class="toc-eyebrow">Sommaire · {nb_chap} chapitres · {len(bonus)} bonus</div>
  <h1 class="toc-title">Table des matières</h1>
  <p class="toc-intro">Chaque chapitre suit la même progression : théorie simple, illustration concrète, encadrés pédagogiques, puis fiche pratique en fin de section.</p>
  {''.join(toc_rows)}
  <div class="page-footer">
    <span>Collection Yeelen · {_esc(spec.volume_label)}</span>
    <span class="pagenum">04</span>
  </div>
</div>"""


def _render_chapter_opener(chap: dict, partie: dict) -> str:
    objectifs = chap.get("objectifs_lecteur", [])
    objectifs_html = "".join(f"<li>{_esc(o)}</li>" for o in objectifs)
    return f"""
<div class="page chapter-opener">
  <div class="chapter-opener-top">
    <div class="chapter-opener-eyebrow">Chapitre {chap['numero']:02d} · {_esc(partie['titre'])}</div>
    <div class="chapter-opener-num">{chap['numero']:02d}</div>
    <h1 class="chapter-opener-title">{_esc(chap['titre'])}.</h1>
    <div class="chapter-opener-rule"></div>
    <div class="chapter-opener-deck">{_esc(chap.get('deck', ''))}</div>
  </div>
  <div class="chapter-opener-bottom">
    <h3>Au programme de ce chapitre</h3>
    <ul>{objectifs_html}</ul>
  </div>
</div>"""


def _render_content_pages(chap: dict, partie: dict, content_html: str, start_page: int) -> list:
    """
    v2 — Scinde le contenu par section H2.
    Une div.page par section → plus de débordement caché.
    """
    raw_sections = re.split(r'(?=<h2)', content_html)
    sections = [s.strip() for s in raw_sections if s.strip()]

    result = []
    for i, section_html in enumerate(sections):
        page_num = start_page + i
        result.append(f"""
<div class="page content-page">
  <div class="page-header">
    <span><span class="brand">Ch.{chap['numero']:02d} · {_esc(partie['titre'][:35])}</span></span>
    <span>{_esc(chap['titre'][:45])}</span>
  </div>
  {section_html}
  <div class="page-footer">
    <span>Collection Yeelen · Volume 01</span>
    <span class="pagenum">{page_num:02d}</span>
  </div>
</div>""")

    if not result:
        result.append(f"""
<div class="page content-page">
  <div class="page-header">
    <span><span class="brand">Ch.{chap['numero']:02d} · {_esc(partie['titre'][:35])}</span></span>
    <span>{_esc(chap['titre'][:45])}</span>
  </div>
  {content_html}
  <div class="page-footer">
    <span>Collection Yeelen · Volume 01</span>
    <span class="pagenum">{start_page:02d}</span>
  </div>
</div>""")

    return result


def _render_part_divider(label: str, big_letter: str, title: str, deck: str) -> str:
    return f"""
<div class="page part-divider">
  <div class="part-eyebrow">{_esc(label)}</div>
  <div class="part-num">{_esc(big_letter)}</div>
  <h1 class="part-title">{_esc(title)}</h1>
  <div class="part-deck">{_esc(deck)}</div>
</div>"""


def _render_bonus_pages(bonus_md: str, start_page: int) -> list:
    """
    v2 — Scinde par '# Bonus N' et applique un rendu spécifique par type.
    Glossaire → _render_glossary_html (deux colonnes, lettres, entrées propres).
    """
    raw_sections = re.split(r'(?=^# Bonus)', bonus_md.strip(), flags=re.MULTILINE)
    sections = [s.strip() for s in raw_sections if s.strip() and s.strip() != '---']

    result = []
    for i, section_md in enumerate(sections):
        page_num = start_page + i
        lines = section_md.split('\n', 1)
        first_line = lines[0].strip().lstrip('#').strip()
        rest_md = lines[1].strip() if len(lines) > 1 else ''

        section_lower = first_line.lower()
        if 'glossaire' in section_lower or 'glossary' in section_lower:
            content_html = _render_glossary_html(rest_md)
            header_right = 'Glossaire illustré'
        elif 'checklist' in section_lower:
            content_html = _markdown_to_html(rest_md)
            header_right = 'Checklist pratique'
        elif 'quiz' in section_lower:
            content_html = _markdown_to_html(rest_md)
            header_right = 'Quiz final'
        else:
            content_html = _markdown_to_html(rest_md)
            header_right = first_line

        result.append(f"""
<div class="page content-page">
  <div class="page-header">
    <span><span class="brand">Bonus</span> · Ressources</span>
    <span>{_esc(header_right)}</span>
  </div>
  <h2>{_esc(first_line)}</h2>
  {content_html}
  <div class="page-footer">
    <span>Collection Yeelen · Volume 01</span>
    <span class="pagenum">{page_num:02d}</span>
  </div>
</div>""")

    if not result:
        result.append(f"""
<div class="page content-page">
  <div class="page-header">
    <span><span class="brand">Bonus</span> · Ressources</span>
    <span>Pour aller plus loin</span>
  </div>
  {_markdown_to_html(bonus_md)}
  <div class="page-footer">
    <span>Collection Yeelen · Volume 01</span>
    <span class="pagenum">{start_page:02d}</span>
  </div>
</div>""")

    return result


def _render_end_page(spec, plan: dict, page_num: int) -> str:
    closure = plan.get("page_finale", {}).get("message_cloture", "À vous de jouer.")
    return f"""
<div class="page end-page">
  <div class="page-header">
    <span><span class="brand">Yeelen</span> · Pour aller plus loin</span>
    <span>Mot de la fin</span>
  </div>
  <div class="end-ornament">· · ·</div>
  <div class="end-message">{_esc(closure)}</div>
  <div style="margin-top:10mm;font-family:'Lora',serif;font-style:italic;color:var(--ink-soft);font-size:12pt;max-width:130mm;line-height:1.5;">
    Vous avez parcouru les fondamentaux. Pour aller plus loin, plusieurs options s'offrent à vous.
  </div>
  <div style="margin-top:10mm;padding-top:6mm;border-top:0.5px solid var(--line);width:140mm;">
    <div style="font-family:'Poppins',sans-serif;font-size:9pt;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:3mm;">Restons en contact</div>
    <div style="display:flex;flex-wrap:wrap;gap:3mm;justify-content:center;">
      <div class="social-pill"><strong>yeelen-pv.com</strong> · Plateforme</div>
      <div class="social-pill"><strong>LinkedIn</strong> · Abdoulaye Gackou</div>
      <div class="social-pill"><strong>Instagram</strong> · @abdgackou</div>
    </div>
  </div>
  <div class="end-signature" style="margin-top:12mm;">Merci · Yeelen Collection · {_esc(spec.edition)}</div>
  <div class="page-footer">
    <span>Collection Yeelen · {_esc(spec.volume_label)}</span>
    <span class="pagenum">{page_num:02d}</span>
  </div>
</div>"""


# ============================================================
#   CONVERSION MARKDOWN → HTML
# ============================================================

def _markdown_to_html(md: str) -> str:
    html = md

    # Callouts (DOTALL)
    html = re.sub(r'\[CALLOUT-TIP\]\s*(.*?)\s*\[/CALLOUT-TIP\]',
                  lambda m: _render_callout("tip", "Le saviez-vous", "i", m.group(1)),
                  html, flags=re.DOTALL)
    html = re.sub(r'\[CALLOUT-KEY\]\s*(.*?)\s*\[/CALLOUT-KEY\]',
                  lambda m: _render_callout("key", "À retenir", "✓", m.group(1)),
                  html, flags=re.DOTALL)
    html = re.sub(r'\[CALLOUT-WARNING\]\s*(.*?)\s*\[/CALLOUT-WARNING\]',
                  lambda m: _render_callout("warning", "Erreur à éviter", "!", m.group(1)),
                  html, flags=re.DOTALL)
    html = re.sub(r'\[CALLOUT-CASE\]\s*(.*?)\s*\[/CALLOUT-CASE\]',
                  lambda m: _render_callout("case", "Cas pratique", "→", m.group(1)),
                  html, flags=re.DOTALL)
    html = re.sub(r'\[CALLOUT-DATA\]\s*(.*?)\s*\[/CALLOUT-DATA\]',
                  lambda m: _render_data_callout(m.group(1)),
                  html, flags=re.DOTALL)
    html = re.sub(r'\[ANALOGY\]\s*(.*?)\s*\[/ANALOGY\]',
                  lambda m: _render_analogy(m.group(1)),
                  html, flags=re.DOTALL)

    # Titres
    html = re.sub(r'^## ([\d.]+)\s+(.+?)$',
                  lambda m: f'<h2><span class="h2-num">{m.group(1)}</span> {m.group(2)}</h2>',
                  html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)

    # Bold / italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'(?<![a-zA-Z*])\*([^*\n]+?)\*(?![a-zA-Z*])', r'<em>\1</em>', html)

    # Séparateur --- → visuel
    html = re.sub(r'^\s*---\s*$', '<div class="bonus-sep"></div>', html, flags=re.MULTILINE)

    html = _convert_md_tables(html)
    html = _convert_md_lists(html)
    html = _wrap_paragraphs(html)

    return html


def _render_glossary_html(md: str) -> str:
    """
    v2 — Rendu structuré du glossaire.
    Détecte **Terme** — définition, groupe par lettre, affiche en 2 colonnes.
    """
    lines = md.split('\n')
    entries_html = []
    current_letter = None

    for line in lines:
        line_s = line.strip()
        if not line_s or line_s.startswith('#') or line_s == '---':
            continue
        # Détecter **Terme** — définition (tiret demi-cadratin ou tiret ordinaire)
        m = re.match(r'\*\*(.+?)\*\*\s*[—–-]\s*(.+)', line_s)
        if m:
            term = m.group(1).strip()
            defn = m.group(2).strip()
            first_letter = term[0].upper() if term else '?'
            if first_letter != current_letter:
                current_letter = first_letter
                entries_html.append(f'<div class="glossary-letter">{first_letter}</div>')
            defn_html = _inline_md(defn)
            entries_html.append(f'''<div class="glossary-entry">
  <div class="glossary-term">{_esc(term)}</div>
  <div class="glossary-def">{defn_html}</div>
</div>''')
        elif line_s:
            entries_html.append(f'<p style="column-span:all;">{_inline_md(line_s)}</p>')

    return f'<div class="two-col">{"".join(entries_html)}</div>'


def _render_callout(klass: str, label: str, icon: str, body: str) -> str:
    parts = body.strip().split("\n", 1)
    if len(parts) == 2 and "·" in parts[0]:
        title = parts[0].strip()
        rest = parts[1].strip()
        full_label = f'{label} · {title.split("·", 1)[1].strip()}'
    else:
        rest = body.strip()
        full_label = label
    # v2 : inline markdown dans le corps
    rest_html = _inline_md(rest)
    body_html = "<p>" + rest_html.replace("\n\n", "</p><p>").replace("\n", " ") + "</p>"
    return f'''
<div class="callout callout-{klass}">
  <div class="callout-label"><span class="callout-icon">{icon}</span>{_esc(full_label)}</div>
  <div class="callout-body">{body_html}</div>
</div>'''


def _render_data_callout(body: str) -> str:
    parts = body.strip().split("\n", 1)
    title = parts[0].strip() if parts else "Chiffres clés"
    rest = parts[1] if len(parts) > 1 else ""
    cells = []
    for line in rest.strip().split("\n"):
        line = line.strip().lstrip("-").strip()
        if not line:
            continue
        bits = [b.strip() for b in line.split("|")]
        if len(bits) >= 3:
            val, unit, label = bits[0], bits[1], bits[2]
            cells.append(f'''<div class="data-cell">
          <div class="data-cell-num">{_esc(val)}<span class="unit">{_esc(unit)}</span></div>
          <div class="data-cell-label">{_esc(label)}</div>
        </div>''')
    full_label = f"Chiffres clés · {title.split('·', 1)[1].strip() if '·' in title else title}"
    return f'''
<div class="callout callout-data">
  <div class="callout-label"><span class="callout-icon">#</span>{_esc(full_label)}</div>
  <div class="callout-body"><div class="data-grid">{''.join(cells)}</div></div>
</div>'''


def _render_analogy(body: str) -> str:
    """v2 — inline markdown appliqué au texte de l'analogie."""
    parts = body.strip().split("\n", 1)
    marker = parts[0].strip() if parts else "Analogie"
    text = parts[1].strip() if len(parts) > 1 else body.strip()
    return f'''
<div class="analogy">
  <div class="analogy-marker">{_esc(marker)}</div>
  <div class="analogy-content">{_inline_md(text)}</div>
</div>'''


def _convert_md_tables(html: str) -> str:
    lines = html.split("\n")
    out = []
    i = 0
    while i < len(lines):
        if "|" in lines[i] and i + 1 < len(lines) and re.match(r'^\s*\|?[\s\-:|]+\|?\s*$', lines[i+1]):
            header_cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and "|" in lines[i]:
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(row)
                i += 1
            t = '<table class="clean"><thead><tr>'
            t += "".join(f"<th>{_esc(c)}</th>" for c in header_cells)
            t += "</tr></thead><tbody>"
            for row in rows:
                t += "<tr>" + "".join(f"<td>{_inline_md(c)}</td>" for c in row) + "</tr>"
            t += "</tbody></table>"
            out.append(t)
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def _convert_md_lists(html: str) -> str:
    lines = html.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Checklist - [ ] : vérifier uniquement que la ligne commence par le marqueur,
        # pas par une balise HTML (fix v2 : le bold à l'intérieur ne doit pas bloquer)
        if re.match(r'^\s*-\s+\[[ x]\]\s+', line) and not stripped.startswith('<'):
            items = []
            while i < len(lines) and re.match(r'^\s*-\s+\[[ x]\]\s+', lines[i]):
                item_text = re.sub(r'^\s*-\s+\[[ x]\]\s+', '', lines[i])
                items.append(item_text)
                i += 1
            items_html = "".join(
                f'<div class="checklist-item"><div class="checklist-checkbox"></div>'
                f'<div class="checklist-text">{_inline_md(it)}</div></div>'
                for it in items
            )
            out.append(f'<div>{items_html}</div>')
            continue
        # Liste à puces : idem, ne bloquer que si la ligne COMMENCE par <
        if re.match(r'^\s*[-•·]\s+', line) and not stripped.startswith('<'):
            items = []
            while i < len(lines) and re.match(r'^\s*[-•·]\s+', lines[i]) and not lines[i].strip().startswith('<'):
                items.append(re.sub(r'^\s*[-•·]\s+', '', lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{_inline_md(li)}</li>" for li in items) + "</ul>")
            continue
        # Liste numérotée
        if re.match(r'^\s*\d+\.\s+', line) and not stripped.startswith('<'):
            items = []
            while i < len(lines) and re.match(r'^\s*\d+\.\s+', lines[i]) and not lines[i].strip().startswith('<'):
                items.append(re.sub(r'^\s*\d+\.\s+', '', lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{_inline_md(li)}</li>" for li in items) + "</ol>")
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def _wrap_paragraphs(html: str) -> str:
    blocks = re.split(r'\n\s*\n', html)
    out_blocks = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if b.startswith("<"):
            out_blocks.append(b)
        else:
            out_blocks.append(f"<p>{b}</p>")
    return "\n\n".join(out_blocks)


# ============================================================
#   EXPORT PDF VIA CHROMIUM
# ============================================================

def render_pdf(html_path: Path, pdf_path: Path):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("Playwright non installé : pip install playwright")

    import os, glob, subprocess as sp

    # Chercher Chromium dans tous les endroits possibles
    patterns = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
        os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    chrome_path = None
    for p in patterns:
        if "*" in p:
            found = glob.glob(p)
            if found:
                chrome_path = found[0]
                break
        elif os.path.exists(p):
            chrome_path = p
            break

    # Si toujours pas trouvé, installer via playwright
    if not chrome_path:
        sp.run(["playwright", "install", "chromium", "--with-deps"],
               capture_output=True, timeout=180)
        for p in patterns:
            if "*" in p:
                found = glob.glob(p)
                if found:
                    chrome_path = found[0]
                    break

    with sync_playwright() as pw:
        opts = {"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        if chrome_path and os.path.exists(chrome_path):
            opts["executable_path"] = chrome_path
        browser = pw.chromium.launch(**opts)
        page = browser.new_page()
        page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
        page.emulate_media(media="print")
        page.pdf(path=str(pdf_path), format="A4", print_background=True,
                 margin={"top":"0","bottom":"0","left":"0","right":"0"},
                 prefer_css_page_size=True)
        browser.close()


# ============================================================
#   EXPORT DOCX & EPUB VIA PANDOC
# ============================================================

def render_docx_epub(md_path: Path, docx_path: Path, epub_path: Path,
                     title: str = "Ebook", author: str = ""):
    if not shutil.which("pandoc"):
        docx_path.write_bytes(b"")
        epub_path.write_bytes(b"")
        return

    meta = f"---\ntitle: \"{title}\"\nauthor: \"{author}\"\nlang: fr\n---\n\n"
    md_meta_path = md_path.with_suffix(".meta.md")
    md_meta_path.write_text(meta + md_path.read_text(encoding="utf-8"), encoding="utf-8")

    try:
        subprocess.run(["pandoc", str(md_meta_path), "-o", str(docx_path), "--standalone"],
                       check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠ DOCX : {e.stderr.decode()}")

    epub_css = TEMPLATES_DIR / "epub.css"
    epub_args = ["pandoc", str(md_meta_path), "-o", str(epub_path), "--standalone"]
    if epub_css.exists():
        epub_args += ["--css", str(epub_css)]
    try:
        subprocess.run(epub_args, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠ EPUB : {e.stderr.decode()}")

    md_meta_path.unlink(missing_ok=True)
