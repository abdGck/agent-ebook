"""
Agent Ebook — Interface Streamlit v2
=====================================
Deux modes :
  1. Générer un nouvel ebook à partir d'un sujet
  2. Reformater un ebook existant (PDF / EPUB / DOCX / TXT)
"""

import os
import sys
import json
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from generator import (
    BookGenerator, BookSpec, GenerationProgress,
    EbookReformatter, extract_text_from_file, PromptLibrary
)

# ============================================================
#   CONFIG
# ============================================================

st.set_page_config(
    page_title="Agent Ebook",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600&family=Poppins:wght@300;400;500;600&display=swap');
.main { background: #FAFAF7; }
h1,h2,h3 { font-family: 'Lora', serif; color: #0A2540; }
.plan-box {
  background: white; border: 1px solid #e0e0e0;
  border-left: 4px solid #E8A33D; border-radius: 8px;
  padding: 14px; margin: 6px 0;
}
.chapter-tag {
  background: #0A2540; color: white;
  padding: 2px 10px; border-radius: 12px;
  font-size: 12px; font-weight: 500;
}
.dl-box {
  background: white; border: 2px solid #E8A33D;
  border-radius: 12px; padding: 20px; text-align: center;
  margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
#   EN-TÊTE
# ============================================================

api_key = os.getenv("ANTHROPIC_API_KEY", "")
has_api = bool(api_key)

st.markdown("# 📚 Agent Ebook")
st.markdown("*Génère et reformate vos ebooks automatiquement dans le style Collection Yeelen*")

if has_api:
    st.success("🟢 Mode Live · Clé API active")
else:
    st.warning("🟡 Mode Démo · Ajoutez ANTHROPIC_API_KEY dans les Secrets Streamlit")

st.markdown("---")

# ============================================================
#   SESSION STATE
# ============================================================

def init():
    defaults = {
        # Génération
        "g_step": "idle",   # idle | plan_ready | done | error
        "g_plan": None,
        "g_files": {},
        "g_cost": 0.0,
        "g_error": "",
        "g_spec_data": {},
        "_g_gen": None,
        # Reformatage
        "r_step": "idle",   # idle | extracted | plan_ready | done | error
        "r_text": "",
        "r_filename": "",
        "r_word_count": 0,
        "r_plan": None,
        "r_files": {},
        "r_cost": 0.0,
        "r_error": "",
        "r_spec_data": {},
        "_r_ref": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()


def make_spec(d: dict) -> BookSpec:
    initiales = (d.get("auteur", "AG") or "AG")[:2].upper()
    return BookSpec(
        sujet=d.get("sujet", ""),
        audience=d.get("audience", "Grand public motivé"),
        pages_visees=int(d.get("pages", 30)),
        ton=d.get("ton", "Vulgarisé, chaleureux, ancrage Afrique"),
        charte=d.get("charte", "solaire"),
        langue="français",
        notes=d.get("notes", ""),
        auteur=d.get("auteur", "Abdoulaye Gackou"),
        auteur_role=d.get("auteur_role", "Ingénieur en énergie solaire photovoltaïque"),
        auteur_initiales=initiales,
        volume_label=d.get("volume_label", "Volume 01"),
        edition="Édition 2026",
    )


def show_plan(plan: dict):
    """Affiche le plan structuré de façon lisible."""
    st.markdown(f"### 📋 *{plan.get('titre', '')}*")
    st.caption(plan.get("sous_titre", ""))
    for partie in plan.get("parties", []):
        st.markdown(f"**{partie.get('titre', '')}**")
        for chap in partie.get("chapitres", []):
            sections = " · ".join(s.get("titre", "") for s in chap.get("sections", []))
            num = chap.get("numero", "?")
            titre = chap.get("titre", "")
            st.markdown(f"""
            <div class="plan-box">
              <span class="chapter-tag">Ch. {str(num).zfill(2)}</span>
              &nbsp; <strong>{titre}</strong><br>
              <small style="color:#888;">{sections}</small>
            </div>
            """, unsafe_allow_html=True)


def show_downloads(files: dict, cost: float, job_id: str):
    """Affiche les boutons de téléchargement."""
    st.success("🎉 Terminé ! Téléchargez vos fichiers ci-dessous.")
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    for col, ftype, label, icon in [
        (col1, "pdf",  "PDF",  "📄"),
        (col2, "docx", "DOCX", "📝"),
        (col3, "epub", "EPUB", "📱"),
    ]:
        with col:
            path = Path(files.get(ftype, ""))
            if path.exists():
                data = path.read_bytes()
                st.markdown(f'<div class="dl-box"><b>{icon} {label}</b></div>', unsafe_allow_html=True)
                st.download_button(
                    label=f"⬇️ Télécharger {label}",
                    data=data,
                    file_name=path.name,
                    mime="application/octet-stream",
                    key=f"dl_{job_id}_{ftype}",
                    use_container_width=True,
                )
            else:
                with col:
                    st.caption(f"{label} non disponible")

    if cost > 0:
        st.caption(f"💰 Coût API estimé : ${cost:.3f}")


def run_reformat_chapters(reformatter, plan):
    """Lance le reformatage complet chapitre par chapitre avec barre de progression."""
    all_chaps = [
        (partie, chap)
        for partie in plan.get("parties", [])
        for chap in partie.get("chapitres", [])
    ]
    total = len(all_chaps)
    chapters_md = []
    chapter_summaries = []

    system = PromptLibrary.load("system")
    progress_bar = st.progress(0)
    status = st.empty()

    for i, (partie, chap) in enumerate(all_chaps):
        n = i + 1
        status.info(f"✍️ Reformatage chapitre {n}/{total} : **{chap['titre']}**")
        progress_bar.progress(int((n - 1) / total * 75))

        chapitre_text = reformatter._extract_chapter_text(chap, i, total)
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

    status.info("📎 Génération des bonus...")
    progress_bar.progress(80)
    reformatter.generate_bonus()

    status.info("🖨️ Export PDF / DOCX / EPUB...")
    progress_bar.progress(92)
    files = reformatter.render_outputs()

    progress_bar.progress(100)
    status.empty()
    return files, reformatter.client.total_cost_usd


# ============================================================
#   ONGLETS
# ============================================================

tab1, tab2 = st.tabs(["✨ Générer un nouvel ebook", "📂 Reformater un ebook existant"])


# ============================================================
#   TAB 1 — GÉNÉRER
# ============================================================

with tab1:

    # ── ÉTAPE 0 : Formulaire (toujours visible sauf si done) ──
    if st.session_state.g_step in ("idle", "error"):
        st.markdown("### 📝 Paramètres de l'ebook")
        with st.form("form_gen"):
            col1, col2 = st.columns(2)
            with col1:
                sujet = st.text_area("Sujet *", placeholder="Ex: L'énergie solaire en site isolé en Afrique", height=90)
                audience = st.selectbox("Audience", ["Grand public débutant", "Grand public motivé",
                    "Public technique", "Agriculteurs et praticiens", "Étudiants"])
                pages = st.slider("Pages visées", 15, 80, 30, 5)
            with col2:
                ton = st.text_input("Ton éditorial", value="Vulgarisé, chaleureux, ancrage Afrique")
                charte = st.selectbox("Charte graphique", [
                    "solaire — Navy + Amber", "agriculture — Vert + Ocre",
                    "premium — Marine + Cuivre", "pedago — Terracotta + Crème"])
                auteur = st.text_input("Auteur", value="Abdoulaye Gackou")
                auteur_role = st.text_input("Rôle", value="Ingénieur en énergie solaire photovoltaïque")
            notes = st.text_area("Notes / directives (optionnel)", height=60)
            go = st.form_submit_button("🚀 Générer le plan", type="primary", use_container_width=True)

        if go:
            if not sujet.strip():
                st.error("Le sujet est obligatoire.")
            else:
                st.session_state.g_spec_data = {
                    "sujet": sujet, "audience": audience, "pages": pages,
                    "ton": ton, "charte": charte.split(" — ")[0],
                    "auteur": auteur, "auteur_role": auteur_role,
                    "notes": notes, "volume_label": "Volume 01",
                }
                with st.spinner("Génération du plan (Opus)... ~30 secondes"):
                    try:
                        spec = make_spec(st.session_state.g_spec_data)
                        gen = BookGenerator(spec, demo_mode=not has_api)
                        plan = gen.generate_plan()
                        st.session_state.g_plan = plan
                        st.session_state.g_cost = gen.client.total_cost_usd
                        st.session_state._g_gen = gen
                        st.session_state.g_step = "plan_ready"
                        st.session_state.g_error = ""
                    except Exception as e:
                        st.session_state.g_error = str(e)
                        st.session_state.g_step = "error"
                st.rerun()

        if st.session_state.g_step == "error":
            st.error(f"❌ {st.session_state.g_error}")

    # ── ÉTAPE 1 : Plan prêt — valider ──
    if st.session_state.g_step == "plan_ready" and st.session_state.g_plan:
        show_plan(st.session_state.g_plan)
        col_ok, col_reset = st.columns([3, 1])
        with col_ok:
            if st.button("✅ Valider et rédiger l'ebook", type="primary", use_container_width=True):
                gen = st.session_state._g_gen
                plan = st.session_state.g_plan
                all_chaps = [(p, c) for p in plan.get("parties", []) for c in p.get("chapitres", [])]
                total = len(all_chaps)
                chapters_md = []
                chapter_summaries = []
                system = PromptLibrary.load("system")
                bar = st.progress(0)
                status = st.empty()
                try:
                    for i, (partie, chap) in enumerate(all_chaps):
                        n = i + 1
                        status.info(f"✍️ Chapitre {n}/{total} : {chap['titre']}")
                        bar.progress(int((n-1)/total*75))
                        resumes = "\n".join(chapter_summaries) or "(premier chapitre)"
                        user = PromptLibrary.render("chapter",
                            titre_ebook=plan.get("titre",""),
                            sous_titre=plan.get("sous_titre",""),
                            audience=gen.spec.audience, ton=gen.spec.ton,
                            chapitre_json=json.dumps(chap, ensure_ascii=False, indent=2),
                            resumes_chapitres_precedents=resumes)
                        md = gen.client.call("claude-sonnet-4-6", system, user, 16000)
                        chapters_md.append(md)
                        chapter_summaries.append(f"Ch {chap['numero']} : {chap['titre']}")
                    gen.progress.chapters_md = chapters_md
                    status.info("📎 Bonus..."); bar.progress(82)
                    gen.generate_bonus()
                    status.info("🖨️ Export PDF/DOCX/EPUB..."); bar.progress(93)
                    files = gen.render_outputs()
                    st.session_state.g_files = files
                    st.session_state.g_cost = gen.client.total_cost_usd
                    st.session_state.g_step = "done"
                    bar.progress(100); status.empty()
                except Exception as e:
                    st.session_state.g_error = str(e)
                    st.session_state.g_step = "error"
                st.rerun()
        with col_reset:
            if st.button("↩️ Recommencer", use_container_width=True):
                st.session_state.g_step = "idle"
                st.session_state.g_plan = None
                st.rerun()

    # ── ÉTAPE 2 : Téléchargement ──
    if st.session_state.g_step == "done":
        show_downloads(st.session_state.g_files, st.session_state.g_cost, "gen")
        if st.button("🔄 Générer un autre ebook", use_container_width=True):
            st.session_state.g_step = "idle"
            st.session_state.g_plan = None
            st.session_state.g_files = {}
            st.rerun()


# ============================================================
#   TAB 2 — REFORMATER
# ============================================================

with tab2:
    st.markdown("### 📂 Reformater un ebook existant")
    st.markdown("Uploadez votre ebook · L'agent extrait le contenu et le restructure dans le style Yeelen.")

    if not has_api:
        st.warning("⚠️ Mode démo — Sans clé API le résultat sera générique.")

    # ── ÉTAPE 0 : Upload ──
    if st.session_state.r_step == "idle":
        uploaded = st.file_uploader(
            "Glissez votre ebook ici",
            type=["pdf","epub","docx","txt","md"],
            help="PDF recommandé · Max 50 Mo"
        )
        if uploaded:
            with st.spinner(f"Extraction du texte depuis {uploaded.name}..."):
                try:
                    suffix = Path(uploaded.name).suffix.lower()
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                    tmp.write(uploaded.read()); tmp.close()
                    text = extract_text_from_file(Path(tmp.name))
                    os.unlink(tmp.name)
                    st.session_state.r_text = text
                    st.session_state.r_filename = uploaded.name
                    st.session_state.r_word_count = len(text.split())
                    st.session_state.r_step = "extracted"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur extraction : {e}")

    # ── ÉTAPE 1 : Fichier extrait — paramètres ──
    if st.session_state.r_step == "extracted":
        st.success(f"✅ **{st.session_state.r_filename}** — {st.session_state.r_word_count:,} mots extraits")
        with st.expander("Aperçu du texte extrait"):
            st.text(st.session_state.r_text[:500] + "...")

        st.markdown("#### ⚙️ Paramètres de mise en forme")
        with st.form("form_rf"):
            col1, col2 = st.columns(2)
            with col1:
                rf_charte = st.selectbox("Charte graphique", [
                    "solaire — Navy + Amber", "agriculture — Vert + Ocre",
                    "premium — Marine + Cuivre", "pedago — Terracotta + Crème"])
                rf_audience = st.selectbox("Audience", ["Grand public débutant",
                    "Grand public motivé", "Public technique", "Agriculteurs"])
                rf_ton = st.text_input("Ton", value="Vulgarisé, chaleureux, ancrage Afrique")
            with col2:
                rf_auteur = st.text_input("Auteur", value="Abdoulaye Gackou")
                rf_role = st.text_input("Rôle", value="Ingénieur en énergie solaire photovoltaïque")
                rf_volume = st.text_input("Label volume", value="Volume 02")
            rf_go = st.form_submit_button("🔍 Analyser et générer le plan", type="primary", use_container_width=True)

        if rf_go:
            st.session_state.r_spec_data = {
                "sujet": st.session_state.r_filename,
                "audience": rf_audience, "pages": 30, "ton": rf_ton,
                "charte": rf_charte.split(" — ")[0],
                "auteur": rf_auteur, "auteur_role": rf_role,
                "volume_label": rf_volume, "notes": "",
            }
            with st.spinner("Analyse de la structure (Opus)... ~30-60 secondes"):
                try:
                    spec = make_spec(st.session_state.r_spec_data)
                    ref = EbookReformatter(spec=spec,
                        extracted_text=st.session_state.r_text,
                        demo_mode=not has_api)
                    plan = ref.generate_plan()
                    st.session_state.r_plan = plan
                    st.session_state.r_cost = ref.client.total_cost_usd
                    st.session_state._r_ref = ref
                    st.session_state.r_step = "plan_ready"
                    st.session_state.r_error = ""
                except Exception as e:
                    st.session_state.r_error = str(e)
                    st.session_state.r_step = "error"
            st.rerun()

    # ── ÉTAPE 2 : Plan prêt — valider ──
    if st.session_state.r_step == "plan_ready" and st.session_state.r_plan:
        show_plan(st.session_state.r_plan)
        col_ok, col_reset = st.columns([3, 1])
        with col_ok:
            if st.button("✅ Valider et reformater", type="primary", use_container_width=True, key="btn_rf_validate"):
                ref = st.session_state._r_ref
                plan = st.session_state.r_plan
                try:
                    files, cost = run_reformat_chapters(ref, plan)
                    st.session_state.r_files = files
                    st.session_state.r_cost = cost
                    st.session_state.r_step = "done"
                    st.session_state.r_error = ""
                except Exception as e:
                    st.session_state.r_error = str(e)
                    st.session_state.r_step = "error"
                st.rerun()
        with col_reset:
            if st.button("↩️ Recommencer", use_container_width=True, key="btn_rf_reset1"):
                st.session_state.r_step = "idle"
                st.session_state.r_plan = None
                st.session_state.r_text = ""
                st.rerun()

    # ── ÉTAPE 3 : TÉLÉCHARGEMENT ──
    if st.session_state.r_step == "done":
        show_downloads(st.session_state.r_files, st.session_state.r_cost, "rf")
        if st.button("🔄 Reformater un autre ebook", use_container_width=True, key="btn_rf_restart"):
            st.session_state.r_step = "idle"
            st.session_state.r_plan = None
            st.session_state.r_files = {}
            st.session_state.r_text = ""
            st.rerun()

    # ── ERREUR ──
    if st.session_state.r_step == "error":
        st.error(f"❌ {st.session_state.r_error}")
        if st.button("Recommencer depuis le début", key="btn_rf_err"):
            st.session_state.r_step = "idle"
            st.session_state.r_plan = None
            st.session_state.r_text = ""
            st.session_state.r_error = ""
            st.rerun()