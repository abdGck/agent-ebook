"""
Yeelen Agent — Interface Streamlit
===================================
Deux modes :
  1. Générer un nouvel ebook à partir d'un sujet
  2. Reformater un ebook existant (PDF / EPUB / DOCX / TXT)

Lancement local :
  streamlit run streamlit_app.py
"""

import os
import sys
import json
import time
import threading
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Ajouter le dossier racine au path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from generator import (
    BookGenerator, BookSpec, GenerationProgress,
    EbookReformatter, extract_text_from_file
)

# ============================================================
#   CONFIG STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Agent Ebook",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour le style Yeelen
st.markdown("""
<style>
  /* Police et couleurs Yeelen */
  @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;500;600&family=Poppins:wght@300;400;500;600&display=swap');

  .main { background: #FAFAF7; }

  h1, h2, h3 { font-family: 'Lora', serif; color: #0A2540; }

  .yeelen-header {
    background: #0A2540;
    color: white;
    padding: 20px 30px;
    border-radius: 10px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .yeelen-title {
    font-family: 'Lora', serif;
    font-size: 28px;
    font-weight: 600;
    margin: 0;
  }
  .yeelen-subtitle {
    font-family: 'Poppins', sans-serif;
    font-size: 13px;
    opacity: 0.7;
    margin: 0;
  }
  .status-live {
    background: #2ec4a0; color: white;
    padding: 4px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 600;
  }
  .status-demo {
    background: #E8A33D; color: white;
    padding: 4px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 600;
  }
  .plan-box {
    background: white;
    border: 1px solid #e0e0e0;
    border-left: 4px solid #E8A33D;
    border-radius: 8px;
    padding: 16px;
    margin: 8px 0;
  }
  .chapter-tag {
    background: #0A2540;
    color: white;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-family: 'Poppins', sans-serif;
    font-weight: 500;
  }
  .cost-badge {
    background: #f0f0f0;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    color: #555;
  }
  div[data-testid="stProgress"] > div {
    background-color: #E8A33D !important;
  }
</style>
""", unsafe_allow_html=True)


# ============================================================
#   EN-TÊTE
# ============================================================

api_key = os.getenv("ANTHROPIC_API_KEY", "")
has_api = bool(api_key)

col_title, col_status = st.columns([5, 1])
with col_title:
    st.markdown("""
    <div class="yeelen-header">
      <div>☀️</div>
      <div>
        <div class="yeelen-title">📚 Agent Ebook</div>
        <div class="yeelen-subtitle">Génère et reformate vos ebooks automatiquement</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_status:
    st.markdown("<br>", unsafe_allow_html=True)
    if has_api:
        st.success("🟢 Mode Live · Clé API active")
    else:
        st.warning("🟡 Mode Démo · Pas de clé API")


# ============================================================
#   ONGLETS
# ============================================================

tab1, tab2 = st.tabs(["✨ Générer un nouvel ebook", "📂 Reformater un ebook existant"])


# ============================================================
#   UTILITAIRES SESSION STATE
# ============================================================

def init_state():
    defaults = {
        "gen_plan": None,
        "gen_chapters": [],
        "gen_bonus": "",
        "gen_files": {},
        "gen_step": "idle",
        "gen_error": "",
        "gen_cost": 0.0,
        "rf_plan": None,
        "rf_chapters": [],
        "rf_bonus": "",
        "rf_files": {},
        "rf_step": "idle",
        "rf_error": "",
        "rf_cost": 0.0,
        "rf_extracted_text": "",
        "rf_filename": "",
        "rf_word_count": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


def make_spec(data: dict) -> BookSpec:
    initiales = (data.get("auteur", "AG") or "AG")[:2].upper()
    return BookSpec(
        sujet=data.get("sujet", ""),
        audience=data.get("audience", "Grand public motivé"),
        pages_visees=int(data.get("pages", 30)),
        ton=data.get("ton", "Vulgarisé, chaleureux, ancrage Afrique"),
        charte=data.get("charte", "solaire"),
        langue="français",
        notes=data.get("notes", ""),
        auteur=data.get("auteur", "Abdoulaye Gackou"),
        auteur_role=data.get("auteur_role", "Ingénieur en énergie solaire photovoltaïque"),
        auteur_initiales=initiales,
        volume_label=data.get("volume_label", "Volume 01"),
        edition="Édition 2026",
    )


# ============================================================
#   ONGLET 1 — GÉNÉRER UN NOUVEL EBOOK
# ============================================================

with tab1:
    st.markdown("### 📝 Paramètres de l'ebook")

    with st.form("form_generate"):
        col1, col2 = st.columns(2)

        with col1:
            sujet = st.text_area(
                "Sujet de l'ebook *",
                placeholder="Ex: L'énergie solaire en site isolé en Afrique",
                height=100
            )
            audience = st.selectbox("Audience cible", [
                "Grand public débutant",
                "Grand public motivé",
                "Public technique non spécialiste",
                "Agriculteurs et praticiens",
                "Étudiants ou apprenants",
            ], index=1)
            pages = st.slider("Nombre de pages visées", 15, 80, 30, step=5)

        with col2:
            ton = st.text_input(
                "Ton éditorial",
                value="Vulgarisé, chaleureux, ancrage Afrique"
            )
            charte = st.selectbox("Charte graphique", [
                ("solaire", "☀️ Solaire — Navy + Amber"),
                ("agriculture", "🌿 Agriculture — Vert + Ocre"),
                ("premium", "💎 Premium — Marine + Cuivre"),
                ("pedago", "📚 Pédago — Terracotta + Crème"),
            ], format_func=lambda x: x[1])
            auteur = st.text_input("Nom de l'auteur", value="Abdoulaye Gackou")
            auteur_role = st.text_input(
                "Rôle / titre",
                value="Ingénieur en énergie solaire photovoltaïque"
            )

        notes = st.text_area(
            "Notes ou directives supplémentaires (optionnel)",
            placeholder="Ex: insister sur la rentabilité, inclure des données Mali 2024...",
            height=70
        )

        submitted = st.form_submit_button(
            "🚀 Générer le plan",
            type="primary",
            use_container_width=True
        )

    # ── Génération du plan ──
    if submitted:
        if not sujet.strip():
            st.error("Le sujet est obligatoire.")
        else:
            st.session_state.gen_step = "plan"
            st.session_state.gen_plan = None
            st.session_state.gen_chapters = []
            st.session_state.gen_files = {}
            st.session_state.gen_error = ""

            spec_data = {
                "sujet": sujet, "audience": audience,
                "pages": pages, "ton": ton,
                "charte": charte[0] if isinstance(charte, tuple) else charte,
                "auteur": auteur, "auteur_role": auteur_role, "notes": notes,
                "volume_label": "Volume 01",
            }
            spec = make_spec(spec_data)
            demo_mode = not has_api

            with st.spinner("Génération du plan structuré (Opus)... ~30 secondes"):
                try:
                    gen = BookGenerator(spec, demo_mode=demo_mode)
                    plan = gen.generate_plan()
                    st.session_state.gen_plan = plan
                    st.session_state.gen_cost = gen.client.total_cost_usd
                    st.session_state["_gen_obj"] = gen
                    st.session_state.gen_step = "plan_ready"
                except Exception as e:
                    st.session_state.gen_error = str(e)
                    st.session_state.gen_step = "error"
            st.rerun()

    # ── Affichage du plan ──
    if st.session_state.gen_step in ("plan_ready", "writing", "done") and st.session_state.gen_plan:
        plan = st.session_state.gen_plan
        st.markdown("---")
        st.markdown(f"### 📋 Plan détecté : *{plan.get('titre', '')}*")
        st.caption(plan.get("sous_titre", ""))

        for partie in plan.get("parties", []):
            st.markdown(f"**{partie.get('titre', '')}**")
            for chap in partie.get("chapitres", []):
                sections = " · ".join(s.get("titre", "") for s in chap.get("sections", []))
                st.markdown(f"""
                <div class="plan-box">
                  <span class="chapter-tag">Ch. {chap.get('numero', '?'):02d}</span>
                  &nbsp; <strong>{chap.get('titre', '')}</strong><br>
                  <small style="color:#888;">{sections}</small>
                </div>
                """, unsafe_allow_html=True)

        if st.session_state.gen_step == "plan_ready":
            if st.button("✅ Valider le plan et rédiger l'ebook", type="primary", use_container_width=True):
                st.session_state.gen_step = "writing"
                gen = st.session_state.get("_gen_obj")
                if not gen:
                    st.error("Session expirée. Recommence depuis le début.")
                    st.stop()

                progress_bar = st.progress(0)
                status_text = st.empty()
                chap_total = sum(len(p.get("chapitres", [])) for p in plan.get("parties", []))

                # Rédaction chapitre par chapitre
                try:
                    chapters_md = []
                    chapter_summaries = []
                    from generator import PromptLibrary
                    system = PromptLibrary.load("system")

                    for partie in plan.get("parties", []):
                        for chap in partie.get("chapitres", []):
                            n = len(chapters_md) + 1
                            status_text.info(f"✍️ Rédaction chapitre {n}/{chap_total} : {chap['titre']}")
                            progress_bar.progress(int((n - 1) / chap_total * 70))

                            resumes = "\n".join(chapter_summaries) or "(premier chapitre)"
                            user = PromptLibrary.render("chapter",
                                titre_ebook=plan.get("titre", ""),
                                sous_titre=plan.get("sous_titre", ""),
                                audience=gen.spec.audience,
                                ton=gen.spec.ton,
                                chapitre_json=json.dumps(chap, ensure_ascii=False, indent=2),
                                resumes_chapitres_precedents=resumes
                            )
                            md = gen.client.call(
                                model="claude-sonnet-4-6",
                                system=system, user=user, max_tokens=16000
                            )
                            chapters_md.append(md)
                            chapter_summaries.append(f"Chapitre {chap['numero']} : {chap['titre']}")

                    gen.progress.chapters_md = chapters_md
                    st.session_state.gen_chapters = chapters_md

                    # Bonus
                    status_text.info("📎 Génération des bonus...")
                    progress_bar.progress(80)
                    gen.generate_bonus()
                    st.session_state.gen_bonus = gen.progress.bonus_md

                    # Export
                    status_text.info("🖨️ Export PDF / DOCX / EPUB...")
                    progress_bar.progress(90)
                    files = gen.render_outputs()
                    st.session_state.gen_files = files
                    st.session_state.gen_cost = gen.client.total_cost_usd
                    st.session_state.gen_step = "done"
                    progress_bar.progress(100)
                    status_text.success("✅ Ebook généré avec succès !")

                except Exception as e:
                    st.session_state.gen_error = str(e)
                    st.session_state.gen_step = "error"
                st.rerun()

    # ── Téléchargements ──
    if st.session_state.gen_step == "done" and st.session_state.gen_files:
        st.success("🎉 Ebook généré avec succès !")
        files = st.session_state.gen_files

        col_dl1, col_dl2, col_dl3 = st.columns(3)
        for col, ftype, label, icon in [
            (col_dl1, "pdf", "Télécharger PDF", "📄"),
            (col_dl2, "docx", "Télécharger DOCX", "📝"),
            (col_dl3, "epub", "Télécharger EPUB", "📱"),
        ]:
            with col:
                path = Path(files.get(ftype, ""))
                if path.exists():
                    with open(path, "rb") as f:
                        st.download_button(
                            label=f"{icon} {label}",
                            data=f.read(),
                            file_name=path.name,
                            mime="application/octet-stream",
                            use_container_width=True,
                        )

        if st.session_state.gen_cost > 0:
            st.caption(f"💰 Coût API estimé : ${st.session_state.gen_cost:.3f}")

        if st.button("🔄 Générer un autre ebook", use_container_width=True):
            for k in ["gen_plan", "gen_chapters", "gen_bonus", "gen_files",
                      "gen_step", "gen_error", "gen_cost", "_gen_obj"]:
                st.session_state[k] = None if "plan" in k or "obj" in k else (
                    [] if "chapters" in k else ({} if "files" in k else ("" if "step" not in k else "idle"))
                )
            st.rerun()

    # ── Erreur ──
    if st.session_state.gen_step == "error":
        st.error(f"❌ Erreur : {st.session_state.gen_error}")
        if st.button("Recommencer"):
            st.session_state.gen_step = "idle"
            st.rerun()


# ============================================================
#   ONGLET 2 — REFORMATER UN EBOOK EXISTANT
# ============================================================

with tab2:
    st.markdown("### 📂 Reformater un ebook existant")
    st.markdown(
        "Uploadez votre ebook (PDF, EPUB, DOCX ou TXT). "
        "L'agent extrait le contenu, Claude restructure chaque chapitre "
        "dans le style éditorial Yeelen et vous téléchargez le PDF reformaté."
    )

    if not has_api:
        st.warning(
            "⚠️ **Mode démo actif** — Sans clé API, le contenu sera générique. "
            "Ajoutez `ANTHROPIC_API_KEY` dans votre fichier `.env` pour reformater réellement votre ebook."
        )

    # ── Upload ──
    if st.session_state.rf_step == "idle":
        uploaded_file = st.file_uploader(
            "Glissez votre ebook ici",
            type=["pdf", "epub", "docx", "txt", "md"],
            help="Format PDF recommandé · Taille max 50 Mo"
        )

        if uploaded_file:
            with st.spinner(f"Extraction du texte depuis {uploaded_file.name}..."):
                try:
                    suffix = Path(uploaded_file.name).suffix.lower()
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                    tmp.write(uploaded_file.read())
                    tmp.close()
                    extracted = extract_text_from_file(Path(tmp.name))
                    os.unlink(tmp.name)

                    st.session_state.rf_extracted_text = extracted
                    st.session_state.rf_filename = uploaded_file.name
                    st.session_state.rf_word_count = len(extracted.split())
                    st.session_state.rf_step = "uploaded"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur d'extraction : {e}")

    # ── Fichier uploadé — afficher aperçu + paramètres ──
    if st.session_state.rf_step in ("uploaded", "plan_ready", "writing", "done"):
        if st.session_state.rf_step == "uploaded":
            st.success(
                f"✅ **{st.session_state.rf_filename}** — "
                f"{st.session_state.rf_word_count:,} mots extraits"
            )
            with st.expander("Aperçu du texte extrait"):
                st.text(st.session_state.rf_extracted_text[:600] + "...")

        # ── Paramètres ──
        if st.session_state.rf_step == "uploaded":
            st.markdown("#### ⚙️ Paramètres de mise en forme")
            with st.form("form_reformat"):
                col1, col2 = st.columns(2)
                with col1:
                    rf_charte = st.selectbox("Charte graphique", [
                        ("solaire", "☀️ Solaire — Navy + Amber"),
                        ("agriculture", "🌿 Agriculture — Vert + Ocre"),
                        ("premium", "💎 Premium — Marine + Cuivre"),
                        ("pedago", "📚 Pédago — Terracotta + Crème"),
                    ], format_func=lambda x: x[1])
                    rf_audience = st.selectbox("Audience cible", [
                        "Grand public débutant",
                        "Grand public motivé",
                        "Public technique non spécialiste",
                        "Agriculteurs et praticiens",
                    ], index=1)
                    rf_ton = st.text_input("Ton éditorial", value="Vulgarisé, chaleureux, ancrage Afrique")

                with col2:
                    rf_auteur = st.text_input("Nom de l'auteur", value="Abdoulaye Gackou")
                    rf_role = st.text_input(
                        "Rôle / titre",
                        value="Ingénieur en énergie solaire photovoltaïque"
                    )
                    rf_volume = st.text_input("Label volume", value="Volume 02")

                rf_submitted = st.form_submit_button(
                    "🔍 Analyser et générer le plan",
                    type="primary",
                    use_container_width=True
                )

            if rf_submitted:
                spec_data = {
                    "sujet": st.session_state.rf_filename,
                    "audience": rf_audience,
                    "pages": 30,
                    "ton": rf_ton,
                    "charte": rf_charte[0] if isinstance(rf_charte, tuple) else rf_charte,
                    "auteur": rf_auteur,
                    "auteur_role": rf_role,
                    "volume_label": rf_volume,
                    "notes": "",
                }
                spec = make_spec(spec_data)
                demo_mode = not has_api

                with st.spinner("Analyse de la structure de l'ebook (Opus)... ~30-60 secondes"):
                    try:
                        reformatter = EbookReformatter(
                            spec=spec,
                            extracted_text=st.session_state.rf_extracted_text,
                            demo_mode=demo_mode
                        )
                        plan = reformatter.generate_plan()
                        st.session_state.rf_plan = plan
                        st.session_state.rf_cost = reformatter.client.total_cost_usd
                        st.session_state["_rf_obj"] = reformatter
                        st.session_state.rf_step = "plan_ready"
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                st.rerun()

        # ── Plan reformatage ──
        if st.session_state.rf_step in ("plan_ready", "writing", "done") and st.session_state.rf_plan:
            plan = st.session_state.rf_plan
            st.markdown("---")
            st.markdown(f"### 📋 Structure détectée : *{plan.get('titre', '')}*")
            st.caption(plan.get("sous_titre", ""))

            for partie in plan.get("parties", []):
                st.markdown(f"**{partie.get('titre', '')}**")
                for chap in partie.get("chapitres", []):
                    sections = " · ".join(s.get("titre", "") for s in chap.get("sections", []))
                    st.markdown(f"""
                    <div class="plan-box">
                      <span class="chapter-tag">Ch. {chap.get('numero', '?'):02d}</span>
                      &nbsp; <strong>{chap.get('titre', '')}</strong><br>
                      <small style="color:#888;">{sections}</small>
                    </div>
                    """, unsafe_allow_html=True)

            if st.session_state.rf_step == "plan_ready":
                col_ok, col_cancel = st.columns([3, 1])
                with col_ok:
                    if st.button("✅ Valider et reformater", type="primary", use_container_width=True):
                        st.session_state.rf_step = "writing"
                        reformatter = st.session_state.get("_rf_obj")
                        if not reformatter:
                            st.error("Session expirée. Recommence depuis le début.")
                            st.stop()

                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        chap_total = sum(len(p.get("chapitres", [])) for p in plan.get("parties", []))

                        try:
                            chapters_md = []
                            chapter_summaries = []
                            from generator import PromptLibrary
                            system = PromptLibrary.load("system")

                            all_chaps = [
                                (partie, chap)
                                for partie in plan.get("parties", [])
                                for chap in partie.get("chapitres", [])
                            ]

                            for i, (partie, chap) in enumerate(all_chaps):
                                n = i + 1
                                status_text.info(f"✍️ Reformatage chapitre {n}/{chap_total} : {chap['titre']}")
                                progress_bar.progress(int((n - 1) / chap_total * 70))

                                chapitre_text = reformatter._extract_chapter_text(chap, i, len(all_chaps))
                                resumes = "\n".join(chapter_summaries) or "(premier chapitre)"

                                user = PromptLibrary.render("reformat_chapter",
                                    titre_ebook=plan.get("titre", ""),
                                    audience=reformatter.spec.audience,
                                    ton=reformatter.spec.ton,
                                    chapitre_json=json.dumps(chap, ensure_ascii=False, indent=2),
                                    texte_chapitre=chapitre_text,
                                    resumes_chapitres_precedents=resumes,
                                    numero_chapitre=chap.get("numero", n)
                                )
                                md = reformatter.client.call(
                                    model="claude-sonnet-4-6",
                                    system=system, user=user, max_tokens=16000
                                )
                                chapters_md.append(md)
                                chapter_summaries.append(f"Chapitre {chap.get('numero', n)} : {chap['titre']}")

                            reformatter.progress.chapters_md = chapters_md
                            st.session_state.rf_chapters = chapters_md

                            status_text.info("📎 Génération des bonus...")
                            progress_bar.progress(80)
                            reformatter.generate_bonus()
                            st.session_state.rf_bonus = reformatter.progress.bonus_md

                            status_text.info("🖨️ Export PDF / DOCX / EPUB...")
                            progress_bar.progress(90)
                            files = reformatter.render_outputs()
                            st.session_state.rf_files = files
                            st.session_state.rf_cost = reformatter.client.total_cost_usd
                            st.session_state.rf_step = "done"
                            progress_bar.progress(100)
                            status_text.success("✅ Reformatage terminé !")

                        except Exception as e:
                            st.session_state.rf_error = str(e)
                            st.session_state.rf_step = "error"
                        st.rerun()

                with col_cancel:
                    if st.button("↩️ Recommencer", use_container_width=True):
                        for k in ["rf_plan", "rf_step", "rf_extracted_text",
                                  "rf_filename", "rf_word_count", "_rf_obj"]:
                            if "step" in k:
                                st.session_state[k] = "idle"
                            else:
                                st.session_state[k] = None if "plan" in k or "obj" in k else ""
                        st.rerun()

        # ── Téléchargements reformatage ──
        if st.session_state.rf_step == "done" and st.session_state.rf_files:
            st.success("🎉 Ebook reformaté avec succès !")
            files = st.session_state.rf_files

            col_dl1, col_dl2, col_dl3 = st.columns(3)
            for col, ftype, label, icon in [
                (col_dl1, "pdf", "Télécharger PDF", "📄"),
                (col_dl2, "docx", "Télécharger DOCX", "📝"),
                (col_dl3, "epub", "Télécharger EPUB", "📱"),
            ]:
                with col:
                    path = Path(files.get(ftype, ""))
                    if path.exists():
                        with open(path, "rb") as f:
                            st.download_button(
                                label=f"{icon} {label}",
                                data=f.read(),
                                file_name=path.name,
                                mime="application/octet-stream",
                                use_container_width=True,
                            )

            if st.session_state.rf_cost > 0:
                st.caption(f"💰 Coût API estimé : ${st.session_state.rf_cost:.3f}")

            if st.button("🔄 Reformater un autre ebook", use_container_width=True):
                for k in list(st.session_state.keys()):
                    if k.startswith("rf_") or k == "_rf_obj":
                        del st.session_state[k]
                st.rerun()

        # ── Erreur reformatage ──
        if st.session_state.rf_step == "error":
            st.error(f"❌ Erreur : {st.session_state.rf_error}")
            if st.button("Recommencer depuis le début"):
                for k in list(st.session_state.keys()):
                    if k.startswith("rf_") or k == "_rf_obj":
                        del st.session_state[k]
                st.rerun()
