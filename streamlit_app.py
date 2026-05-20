"""
Agent Ebook — Interface Streamlit v3
=====================================
Navigation par sidebar (plus stable que st.tabs pour les opérations longues).
"""

import os, sys, json, tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from generator import (
    BookGenerator, BookSpec,
    EbookReformatter, extract_text_from_file, PromptLibrary
)

# ── CONFIG ──────────────────────────────────────────────────
st.set_page_config(page_title="Agent Ebook", page_icon="📚", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600&family=Poppins:wght@400;500;600&display=swap');
h1,h2,h3{font-family:'Lora',serif;color:#0A2540}
.plan-box{background:white;border:1px solid #ddd;border-left:4px solid #E8A33D;
  border-radius:8px;padding:12px;margin:5px 0}
.chap-num{background:#0A2540;color:white;padding:2px 10px;
  border-radius:12px;font-size:12px;font-weight:600}
.dl-card{background:#f8f9fa;border:2px solid #E8A33D;border-radius:12px;
  padding:18px;text-align:center;margin:6px 0}
</style>
""", unsafe_allow_html=True)

# ── CLÉS API ────────────────────────────────────────────────
has_api = bool(os.getenv("ANTHROPIC_API_KEY", ""))

# ── SESSION STATE ───────────────────────────────────────────
DEFAULTS = {
    "mode": "generate",          # "generate" | "reformat"
    # Génération
    "g_step": "form",            # form | plan_ready | running | done | error
    "g_plan": None,
    "g_files": {},
    "g_cost": 0.0,
    "g_error": "",
    "_g_gen": None,
    # Reformatage
    "r_step": "upload",          # upload | extracted | plan_ready | running | done | error
    "r_text": "",
    "r_filename": "",
    "r_words": 0,
    "r_plan": None,
    "r_spec": {},
    "r_files": {},
    "r_cost": 0.0,
    "r_error": "",
    "_r_ref": None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── HELPERS ──────────────────────────────────────────────────

def make_spec(d):
    return BookSpec(
        sujet=d.get("sujet",""), audience=d.get("audience","Grand public motivé"),
        pages_visees=int(d.get("pages",30)),
        ton=d.get("ton","Vulgarisé, chaleureux, ancrage Afrique"),
        charte=d.get("charte","solaire"), langue="français",
        notes=d.get("notes",""),
        auteur=d.get("auteur","Abdoulaye Gackou"),
        auteur_role=d.get("auteur_role","Ingénieur en énergie solaire photovoltaïque"),
        auteur_initiales=(d.get("auteur","AG")[:2] or "AG").upper(),
        volume_label=d.get("volume_label","Volume 01"),
        edition="Édition 2026",
    )

def show_plan(plan):
    st.markdown(f"### 📋 *{plan.get('titre','')}*")
    st.caption(plan.get("sous_titre",""))
    for p in plan.get("parties",[]):
        st.markdown(f"**{p.get('titre','')}**")
        for c in p.get("chapitres",[]):
            secs = " · ".join(s.get("titre","") for s in c.get("sections",[]))
            st.markdown(
                f'<div class="plan-box">'
                f'<span class="chap-num">Ch. {str(c.get("numero","?")).zfill(2)}</span>'
                f' &nbsp;<strong>{c.get("titre","")}</strong><br>'
                f'<small style="color:#888">{secs}</small></div>',
                unsafe_allow_html=True)

def show_downloads(files, cost, prefix):
    """Affiche toujours les boutons de téléchargement."""
    st.markdown("---")
    st.success("🎉 Terminé ! Téléchargez vos fichiers ci-dessous.")
    st.markdown("### ⬇️ Télécharger")
    c1, c2, c3 = st.columns(3)
    for col, ftype, label, icon in [
        (c1,"pdf","PDF","📄"), (c2,"docx","Word","📝"), (c3,"epub","EPUB","📱")
    ]:
        path = Path(files.get(ftype,""))
        with col:
            st.markdown(f'<div class="dl-card"><b>{icon} {label}</b></div>', unsafe_allow_html=True)
            if path.exists():
                st.download_button(
                    label=f"⬇️ {label}",
                    data=path.read_bytes(),
                    file_name=path.name,
                    mime="application/octet-stream",
                    key=f"{prefix}_dl_{ftype}",
                    use_container_width=True,
                )
            else:
                st.caption("Non disponible")
    if cost > 0:
        st.caption(f"💰 Coût API estimé : ${cost:.3f}")

def run_reformatage(ref, plan):
    """Reformate les chapitres un par un en sauvegardant chaque résultat."""
    all_chaps = [(p,c) for p in plan.get("parties",[]) for c in p.get("chapitres",[])]
    total = len(all_chaps)
    system = PromptLibrary.load("system")

    # Initialiser le buffer de chapitres si pas encore fait
    if "r_chapters_done" not in st.session_state:
        st.session_state.r_chapters_done = []
    if "r_summaries" not in st.session_state:
        st.session_state.r_summaries = []

    already_done = len(st.session_state.r_chapters_done)
    bar  = st.progress(int(already_done / total * 72))
    info = st.empty()

    # Reprendre depuis le dernier chapitre sauvegardé
    for i, (partie, chap) in enumerate(all_chaps):
        if i < already_done:
            continue  # déjà traité, on saute

        n = i + 1
        info.info(f"✍️ Chapitre {n}/{total} : **{chap['titre']}**")
        bar.progress(int((n-1)/total*72))

        chapitre_text = ref._extract_chapter_text(chap, i, total)
        resumes = "\n".join(st.session_state.r_summaries) or "(premier chapitre)"

        user = PromptLibrary.render("reformat_chapter",
            titre_ebook=plan.get("titre",""),
            audience=ref.spec.audience, ton=ref.spec.ton,
            chapitre_json=json.dumps(chap, ensure_ascii=False, indent=2),
            texte_chapitre=chapitre_text,
            resumes_chapitres_precedents=resumes,
            numero_chapitre=chap.get("numero", n))

        md = ref.client.call("claude-sonnet-4-6", system, user, 16000)

        # Sauvegarder immédiatement dans session_state
        st.session_state.r_chapters_done.append(md)
        st.session_state.r_summaries.append(f"Ch {chap.get('numero',n)} : {chap['titre']}")

    # Tous les chapitres sont faits
    ref.progress.chapters_md = st.session_state.r_chapters_done

    info.info("📎 Génération des bonus...")
    bar.progress(82)
    ref.generate_bonus()

    info.info("🖨️ Export PDF / DOCX / EPUB...")
    bar.progress(93)
    files = ref.render_outputs()

    bar.progress(100)
    info.empty()

    # Nettoyer le buffer temporaire
    del st.session_state.r_chapters_done
    del st.session_state.r_summaries

    return files, ref.client.total_cost_usd

def run_generation(gen, plan):
    """Rédige les chapitres un par un en sauvegardant chaque résultat."""
    all_chaps = [(p,c) for p in plan.get("parties",[]) for c in p.get("chapitres",[])]
    total = len(all_chaps)
    system = PromptLibrary.load("system")

    if "g_chapters_done" not in st.session_state:
        st.session_state.g_chapters_done = []
    if "g_summaries" not in st.session_state:
        st.session_state.g_summaries = []

    already_done = len(st.session_state.g_chapters_done)
    bar  = st.progress(int(already_done / total * 72))
    info = st.empty()

    for i, (partie, chap) in enumerate(all_chaps):
        if i < already_done:
            continue

        n = i + 1
        info.info(f"✍️ Chapitre {n}/{total} : **{chap['titre']}**")
        bar.progress(int((n-1)/total*72))

        resumes = "\n".join(st.session_state.g_summaries) or "(premier chapitre)"
        user = PromptLibrary.render("chapter",
            titre_ebook=plan.get("titre",""), sous_titre=plan.get("sous_titre",""),
            audience=gen.spec.audience, ton=gen.spec.ton,
            chapitre_json=json.dumps(chap, ensure_ascii=False, indent=2),
            resumes_chapitres_precedents=resumes)

        md = gen.client.call("claude-sonnet-4-6", system, user, 16000)

        # Sauvegarder immédiatement
        st.session_state.g_chapters_done.append(md)
        st.session_state.g_summaries.append(f"Ch {chap.get('numero',n)} : {chap['titre']}")

    gen.progress.chapters_md = st.session_state.g_chapters_done

    info.info("📎 Bonus..."); bar.progress(82)
    gen.generate_bonus()
    info.info("🖨️ Export PDF..."); bar.progress(93)
    files = gen.render_outputs()
    bar.progress(100); info.empty()

    del st.session_state.g_chapters_done
    del st.session_state.g_summaries

    return files, gen.client.total_cost_usd

# ── SIDEBAR ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📚 Agent Ebook")
    st.markdown("---")
    if has_api:
        st.success("🟢 Mode Live")
    else:
        st.warning("🟡 Mode Démo")
    st.markdown("---")
    st.markdown("### Navigation")
    mode = st.radio(
        "Que voulez-vous faire ?",
        options=["generate","reformat"],
        format_func=lambda x: "✨ Générer un ebook" if x=="generate" else "📂 Reformater un ebook",
        key="mode",
        label_visibility="collapsed",
    )
    st.markdown("---")
    if st.button("🔄 Tout recommencer", use_container_width=True):
        for k,v in DEFAULTS.items():
            st.session_state[k] = v
        st.rerun()

# ── TITRE PRINCIPAL ──────────────────────────────────────────
st.markdown("# 📚 Agent Ebook")
if mode == "generate":
    st.markdown("### ✨ Générer un nouvel ebook")
else:
    st.markdown("### 📂 Reformater un ebook existant")
st.markdown("---")

# ════════════════════════════════════════════════════════════
#   MODE GÉNÉRATION
# ════════════════════════════════════════════════════════════
if mode == "generate":

    step = st.session_state.g_step

    # ── Formulaire ──
    if step == "form":
        with st.form("f_gen"):
            c1, c2 = st.columns(2)
            with c1:
                sujet    = st.text_area("Sujet *", height=90,
                    placeholder="Ex: L'énergie solaire en site isolé en Afrique")
                audience = st.selectbox("Audience", ["Grand public débutant",
                    "Grand public motivé","Public technique","Agriculteurs"])
                pages    = st.slider("Pages visées", 15, 80, 30, 5)
            with c2:
                ton          = st.text_input("Ton", value="Vulgarisé, chaleureux, ancrage Afrique")
                charte_label = st.selectbox("Charte", ["solaire — Navy + Amber",
                    "agriculture — Vert + Ocre","premium — Marine + Cuivre","pedago — Terracotta + Crème"])
                auteur       = st.text_input("Auteur", value="Abdoulaye Gackou")
                auteur_role  = st.text_input("Rôle", value="Ingénieur en énergie solaire photovoltaïque")
            notes = st.text_area("Directives supplémentaires (optionnel)", height=60)
            go = st.form_submit_button("🚀 Générer le plan", type="primary", use_container_width=True)

        if go:
            if not sujet.strip():
                st.error("Le sujet est obligatoire.")
            else:
                with st.spinner("Génération du plan (Opus)... ~30 secondes"):
                    try:
                        spec = make_spec({"sujet":sujet,"audience":audience,"pages":pages,
                            "ton":ton,"charte":charte_label.split(" — ")[0],
                            "auteur":auteur,"auteur_role":auteur_role,
                            "notes":notes,"volume_label":"Volume 01"})
                        gen = BookGenerator(spec, demo_mode=not has_api)
                        plan = gen.generate_plan()
                        st.session_state.g_plan  = plan
                        st.session_state.g_cost  = gen.client.total_cost_usd
                        st.session_state._g_gen  = gen
                        st.session_state.g_step  = "plan_ready"
                        st.session_state.g_error = ""
                    except Exception as e:
                        st.session_state.g_error = str(e)
                        st.session_state.g_step  = "error"
                st.rerun()

    # ── Plan prêt ──
    if step == "plan_ready":
        show_plan(st.session_state.g_plan)
        c1, c2 = st.columns([4,1])
        with c1:
            valider = st.button("✅ Valider et rédiger l'ebook", type="primary",
                use_container_width=True, key="g_valider")
        with c2:
            if st.button("↩️ Nouveau plan", use_container_width=True, key="g_reset_plan"):
                st.session_state.g_step = "form"
                st.session_state.g_plan = None
                st.rerun()
        if valider:
            try:
                files, cost = run_generation(st.session_state._g_gen, st.session_state.g_plan)
                st.session_state.g_files = files
                st.session_state.g_cost  = cost
                st.session_state.g_step  = "done"
                st.session_state.g_error = ""
            except Exception as e:
                st.session_state.g_error = str(e)
                st.session_state.g_step  = "error"
            st.rerun()

    # ── Terminé — téléchargements ──
    if step == "done":
        show_downloads(st.session_state.g_files, st.session_state.g_cost, "gen")
        if st.button("🔄 Générer un autre ebook", use_container_width=True, key="g_restart"):
            st.session_state.g_step  = "form"
            st.session_state.g_plan  = None
            st.session_state.g_files = {}
            st.rerun()

    # ── Erreur ──
    if step == "error":
        st.error(f"❌ {st.session_state.g_error}")
        if st.button("Recommencer", key="g_err_reset"):
            st.session_state.g_step  = "form"
            st.session_state.g_error = ""
            st.rerun()


# ════════════════════════════════════════════════════════════
#   MODE REFORMATAGE
# ════════════════════════════════════════════════════════════
if mode == "reformat":

    step = st.session_state.r_step

    if not has_api:
        st.warning("⚠️ Mode démo — Sans clé API le résultat sera générique.")

    # ── Upload ──
    if step == "upload":
        uploaded = st.file_uploader("Glissez votre ebook ici",
            type=["pdf","epub","docx","txt","md"], help="PDF recommandé · Max 50 Mo")
        if uploaded:
            with st.spinner(f"Extraction du texte depuis **{uploaded.name}**..."):
                try:
                    suffix = Path(uploaded.name).suffix.lower()
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                    tmp.write(uploaded.read()); tmp.close()
                    text = extract_text_from_file(Path(tmp.name))
                    os.unlink(tmp.name)
                    st.session_state.r_text     = text
                    st.session_state.r_filename = uploaded.name
                    st.session_state.r_words    = len(text.split())
                    st.session_state.r_step     = "extracted"
                    st.session_state.r_error    = ""
                except Exception as e:
                    st.error(f"Erreur extraction : {e}")
            st.rerun()

    # ── Fichier extrait — paramètres ──
    if step == "extracted":
        st.success(f"✅ **{st.session_state.r_filename}** — {st.session_state.r_words:,} mots extraits")
        with st.expander("Aperçu du texte extrait"):
            st.text(st.session_state.r_text[:500] + "...")

        st.markdown("#### ⚙️ Paramètres de mise en forme")
        with st.form("f_rf_params"):
            c1, c2 = st.columns(2)
            with c1:
                rf_charte   = st.selectbox("Charte", ["solaire — Navy + Amber",
                    "agriculture — Vert + Ocre","premium — Marine + Cuivre","pedago — Terracotta + Crème"])
                rf_audience = st.selectbox("Audience", ["Grand public débutant",
                    "Grand public motivé","Public technique","Agriculteurs"], index=1)
                rf_ton      = st.text_input("Ton", value="Vulgarisé, chaleureux, ancrage Afrique")
            with c2:
                rf_auteur  = st.text_input("Auteur", value="Abdoulaye Gackou")
                rf_role    = st.text_input("Rôle", value="Ingénieur en énergie solaire photovoltaïque")
                rf_volume  = st.text_input("Label volume", value="Volume 02")
            rf_go = st.form_submit_button("🔍 Analyser et générer le plan",
                type="primary", use_container_width=True)

        if rf_go:
            spec_data = {"sujet": st.session_state.r_filename,
                "audience":rf_audience, "pages":30, "ton":rf_ton,
                "charte":rf_charte.split(" — ")[0],
                "auteur":rf_auteur, "auteur_role":rf_role,
                "volume_label":rf_volume, "notes":""}
            with st.spinner("Analyse de la structure (Opus)... ~30-60 secondes"):
                try:
                    spec = make_spec(spec_data)
                    ref  = EbookReformatter(spec=spec,
                        extracted_text=st.session_state.r_text,
                        demo_mode=not has_api)
                    plan = ref.generate_plan()
                    st.session_state.r_plan  = plan
                    st.session_state.r_cost  = ref.client.total_cost_usd
                    st.session_state._r_ref  = ref
                    st.session_state.r_step  = "plan_ready"
                    st.session_state.r_error = ""
                except Exception as e:
                    st.session_state.r_error = str(e)
                    st.session_state.r_step  = "error"
            st.rerun()

    # ── Plan prêt ──
    if step == "plan_ready":
        show_plan(st.session_state.r_plan)
        c1, c2 = st.columns([4,1])
        with c1:
            valider = st.button("✅ Valider et reformater",
                type="primary", use_container_width=True, key="r_valider")
        with c2:
            if st.button("↩️ Recommencer", use_container_width=True, key="r_reset_plan"):
                st.session_state.r_step = "upload"
                st.session_state.r_plan = None
                st.session_state.r_text = ""
                st.rerun()
        if valider:
            try:
                files, cost = run_reformatage(
                    st.session_state._r_ref,
                    st.session_state.r_plan)
                st.session_state.r_files = files
                st.session_state.r_cost  = cost
                st.session_state.r_step  = "done"
                st.session_state.r_error = ""
            except Exception as e:
                st.session_state.r_error = str(e)
                st.session_state.r_step  = "error"
            st.rerun()

    # ── TERMINÉ — TÉLÉCHARGEMENTS ──
    if step == "done":
        show_downloads(st.session_state.r_files, st.session_state.r_cost, "rf")
        if st.button("🔄 Reformater un autre ebook", use_container_width=True, key="r_restart"):
            st.session_state.r_step = "upload"
            st.session_state.r_plan = None
            st.session_state.r_files= {}
            st.session_state.r_text = ""
            st.rerun()

    # ── Erreur ──
    if step == "error":
        st.error(f"❌ {st.session_state.r_error}")
        if st.button("Recommencer depuis le début", key="r_err_reset"):
            st.session_state.r_step  = "upload"
            st.session_state.r_plan  = None
            st.session_state.r_text  = ""
            st.session_state.r_error = ""
            st.rerun()
