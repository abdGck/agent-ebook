"""
Yeelen Agent — Interface web Flask v2
====================================

Deux modes :
  1. Générer un nouvel ebook à partir d'un sujet
  2. Reformater un ebook existant (PDF / EPUB / DOCX / TXT)

Lance un mini serveur web local. Ouvre http://localhost:5000 dans ton navigateur.
"""

import os
import sys
import json
import threading
import uuid
import tempfile
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from generator import (
    BookGenerator, BookSpec, GenerationProgress,
    EbookReformatter, extract_text_from_file
)

app = Flask(__name__,
            template_folder=str(HERE / "templates"),
            static_folder=str(HERE / "static"))

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 Mo max

# Stockage jobs en mémoire
jobs: dict = {}

UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# ============================================================
#   PAGE D'ACCUEIL
# ============================================================

@app.route("/")
def home():
    api_configured = bool(os.getenv("ANTHROPIC_API_KEY"))
    return render_template("index.html", api_configured=api_configured)


# ============================================================
#   MODE 1 — GÉNÉRER UN NOUVEL EBOOK
# ============================================================

@app.route("/api/start", methods=["POST"])
def start_generation():
    data = request.json
    spec = _spec_from_data(data)
    demo_mode = bool(data.get("demo_mode", False)) or not os.getenv("ANTHROPIC_API_KEY")

    job_id = str(uuid.uuid4())[:8]
    try:
        gen = BookGenerator(spec, demo_mode=demo_mode)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    jobs[job_id] = {"generator": gen, "type": "generate"}

    def run_plan():
        try:
            gen.generate_plan()
        except Exception as e:
            gen.progress.step = "error"
            gen.progress.error = str(e)

    threading.Thread(target=run_plan, daemon=True).start()
    return jsonify({"job_id": job_id, "demo_mode": demo_mode})


@app.route("/api/edit-plan/<job_id>", methods=["POST"])
def edit_plan(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job introuvable"}), 404
    new_plan = request.json.get("plan")
    if not new_plan:
        return jsonify({"error": "Plan manquant"}), 400
    job["generator"].progress.plan = new_plan
    return jsonify({"ok": True})


@app.route("/api/continue/<job_id>", methods=["POST"])
def continue_generation(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job introuvable"}), 404
    gen = job["generator"]

    def run_full():
        try:
            gen.generate_chapters()
            gen.generate_bonus()
            gen.render_outputs()
        except Exception as e:
            import traceback
            gen.progress.step = "error"
            gen.progress.error = f"{e}\n\n{traceback.format_exc()}"

    threading.Thread(target=run_full, daemon=True).start()
    return jsonify({"ok": True})


# ============================================================
#   MODE 2 — REFORMATER UN EBOOK EXISTANT
# ============================================================

@app.route("/api/upload-extract", methods=["POST"])
def upload_extract():
    """
    Étape 1 du reformatage : reçoit le fichier, extrait le texte,
    retourne un aperçu + le job_id.
    """
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Nom de fichier vide"}), 400

    # Sauvegarde temporaire
    suffix = Path(f.filename).suffix.lower()
    allowed = {".pdf", ".epub", ".docx", ".txt", ".md"}
    if suffix not in allowed:
        return jsonify({
            "error": f"Format non supporté : {suffix}. Utilise PDF, EPUB, DOCX ou TXT."
        }), 400

    tmp_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    f.save(str(tmp_path))

    # Extraction du texte
    try:
        extracted = extract_text_from_file(tmp_path)
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        return jsonify({"error": f"Impossible d'extraire le texte : {e}"}), 400

    if len(extracted.strip()) < 200:
        tmp_path.unlink(missing_ok=True)
        return jsonify({"error": "Texte extrait trop court (moins de 200 caractères). Le fichier est peut-être protégé ou vide."}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "type": "reformat",
        "extracted_text": extracted,
        "file_path": str(tmp_path),
        "filename": f.filename,
    }

    # Aperçu (premiers 500 caractères)
    preview = extracted[:500].replace("\n", " ").strip()
    word_count = len(extracted.split())

    return jsonify({
        "job_id": job_id,
        "filename": f.filename,
        "word_count": word_count,
        "preview": preview,
    })


@app.route("/api/reformat-start/<job_id>", methods=["POST"])
def reformat_start(job_id):
    """
    Étape 2 : lance l'analyse du texte et génère le plan.
    """
    job = jobs.get(job_id)
    if not job or job.get("type") != "reformat":
        return jsonify({"error": "Job introuvable ou mauvais type"}), 404

    data = request.json or {}
    spec = _spec_from_data(data)
    has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    demo_mode = bool(data.get("demo_mode", False)) or not has_api_key

    reformatter = EbookReformatter(
        spec=spec,
        extracted_text=job["extracted_text"],
        demo_mode=demo_mode
    )
    job["generator"] = reformatter
    job["demo_mode"] = demo_mode

    def run_plan():
        try:
            reformatter.generate_plan()
        except Exception as e:
            reformatter.progress.step = "error"
            reformatter.progress.error = str(e)

    threading.Thread(target=run_plan, daemon=True).start()
    return jsonify({"ok": True, "demo_mode": demo_mode, "has_api_key": has_api_key})


@app.route("/api/reformat-continue/<job_id>", methods=["POST"])
def reformat_continue(job_id):
    """
    Étape 3 : reformate les chapitres + bonus + export.
    """
    job = jobs.get(job_id)
    if not job or job.get("type") != "reformat":
        return jsonify({"error": "Job introuvable"}), 404

    # Mise à jour éventuelle du plan par l'utilisateur
    new_plan = (request.json or {}).get("plan")
    reformatter = job["generator"]
    if new_plan:
        reformatter.progress.plan = new_plan

    def run_full():
        try:
            reformatter.reformat_chapters()
            reformatter.generate_bonus()
            reformatter.render_outputs()
        except Exception as e:
            import traceback
            reformatter.progress.step = "error"
            reformatter.progress.error = f"{e}\n\n{traceback.format_exc()}"

    threading.Thread(target=run_full, daemon=True).start()
    return jsonify({"ok": True})


# ============================================================
#   ROUTES COMMUNES
# ============================================================

@app.route("/api/status/<job_id>")
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job introuvable"}), 404
    gen = job.get("generator")
    if not gen:
        return jsonify({"step": "init", "message": "En attente de démarrage..."}), 200
    p = gen.progress
    return jsonify({
        "step": p.step,
        "message": p.message,
        "chapter_progress": p.chapter_progress,
        "chapter_total": p.chapter_total,
        "plan": p.plan,
        "error": p.error,
        "cost_usd_estimate": round(p.cost_usd_estimate, 3),
        "files": p.final_files,
    })


@app.route("/api/download/<job_id>/<file_type>")
def download(job_id, file_type):
    job = jobs.get(job_id)
    if not job:
        return "Job introuvable", 404
    gen = job.get("generator")
    if not gen:
        return "Génération non démarrée", 404
    files = gen.progress.final_files
    if file_type not in files:
        return f"Type inconnu : {file_type}", 404
    path = Path(files[file_type])
    if not path.exists():
        return "Fichier introuvable", 404
    return send_file(str(path), as_attachment=True, download_name=path.name)


# ============================================================
#   UTILITAIRE
# ============================================================

def _spec_from_data(data: dict) -> BookSpec:
    return BookSpec(
        sujet=data.get("sujet", "").strip(),
        audience=data.get("audience", "Grand public motivé").strip(),
        pages_visees=int(data.get("pages", 30)),
        ton=data.get("ton", "Vulgarisé, chaleureux, ancrage Afrique").strip(),
        charte=data.get("charte", "solaire").strip(),
        langue=data.get("langue", "français").strip(),
        notes=data.get("notes", "").strip(),
        auteur=data.get("auteur", "Abdoulaye Gackou").strip(),
        auteur_role=data.get("auteur_role", "Ingénieur en énergie solaire photovoltaïque").strip(),
        auteur_initiales=data.get("auteur_initiales", "AG").strip()[:2],
        volume_label=data.get("volume_label", "Volume 01").strip(),
        edition=data.get("edition", "Édition 2026").strip(),
    )


# ============================================================
#   LANCEMENT
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Yeelen Agent — Interface Web v2")
    print("=" * 60)
    print("  ➤ Ouvre dans ton navigateur : http://localhost:5000")
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("  ⚠  Aucune clé ANTHROPIC_API_KEY → mode démo activé")
    else:
        print("  ✓ Clé API détectée → mode live disponible")
    print("=" * 60 + "\n")
    app.run(debug=False, port=5000, host="127.0.0.1")
