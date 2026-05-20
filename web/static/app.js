// =====================================================================
//   YEELEN AGENT — Frontend
//   Pilote le formulaire, le polling, et la review du plan.
// =====================================================================

(function () {
  "use strict";

  // ---------- Helpers DOM ----------
  const $ = (id) => document.getElementById(id);
  const show = (id) => $(id).classList.remove("hidden");
  const hide = (id) => $(id).classList.add("hidden");

  const STEPS = ["step-form", "step-loading-plan", "step-plan-review", "step-writing", "step-done", "step-error"];
  function showStep(stepId) {
    STEPS.forEach((s) => hide(s));
    show(stepId);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ---------- État global ----------
  let currentJobId = null;
  let pollInterval = null;

  // =====================================================================
  //   APERÇU CHARTE GRAPHIQUE — au changement du sélecteur
  // =====================================================================
  const CHARTERS = {
    solaire: {
      name: "Yeelen Solaire",
      desc: "Énergie solaire, photovoltaïque, autoconsommation",
      colors: ["#0A2540", "#E8A33D", "#FAFAF7"],
    },
    agriculture: {
      name: "Yeelen Agriculture",
      desc: "Maraîchage, élevage, irrigation, transformation",
      colors: ["#1F3D2C", "#D97A2C", "#FAF8F2"],
    },
    premium: {
      name: "Yeelen Premium",
      desc: "Études techniques, projets professionnels haut de gamme",
      colors: ["#0F1B2C", "#B87333", "#F8F8F8"],
    },
    pedago: {
      name: "Yeelen Pédagogique",
      desc: "Formations, ateliers, cours pour grand public",
      colors: ["#6B3729", "#F4A261", "#FFF8EE"],
    },
  };

  function updateCharterPreview() {
    const value = $("charte").value;
    const data = CHARTERS[value] || CHARTERS.solaire;
    const preview = $("charter-preview");
    if (!preview) return;
    preview.innerHTML = `
      <div class="charter-preview-name">${data.name}</div>
      <div class="charter-preview-desc">${data.desc}</div>
      <div class="charter-swatches">
        ${data.colors.map((c) => `<span class="charter-swatch" style="background:${c}"></span>`).join("")}
      </div>
    `;
  }

  // =====================================================================
  //   ESTIMATION DE COÛT — au changement du nombre de pages
  // =====================================================================
  function updateCostEstimate() {
    const pages = parseInt($("pages").value, 10) || 30;
    // Estimation : ~600 tokens output par page rédigée (chapitres) + plan + bonus
    // Plan (Opus) : ~3000 tokens out * 75$/M = $0.22
    // Chapitres (Sonnet) : pages * 600 tokens * 15$/M = pages * $0.009
    // Bonus (Sonnet) : ~5000 tokens * 15$/M = $0.075
    const planCost = 0.22;
    const chaptersCost = pages * 0.009;
    const bonusCost = 0.075;
    const total = planCost + chaptersCost + bonusCost;
    const totalEur = total * 0.92; // approximation USD->EUR
    const el = $("cost-est");
    if (el) {
      el.textContent = `Coût estimé : ~${totalEur.toFixed(2)} €  (${total.toFixed(2)} $)`;
    }
  }

  // =====================================================================
  //   SOUMISSION DU FORMULAIRE
  // =====================================================================
  async function submitForm(e) {
    e.preventDefault();
    const btn = $("btn-submit");
    btn.disabled = true;
    btn.textContent = "Démarrage...";

    const payload = {
      sujet: $("sujet").value.trim(),
      audience: $("audience").value.trim(),
      pages: parseInt($("pages").value, 10) || 30,
      ton: $("ton").value.trim(),
      charte: $("charte").value,
      langue: "français",
      notes: $("notes").value.trim(),
      auteur: $("auteur") ? $("auteur").value.trim() : "Abdoulaye Gackou",
      edition: $("edition") ? $("edition").value.trim() : "Édition 2026",
    };

    try {
      const res = await fetch("/api/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Erreur serveur" }));
        throw new Error(err.error || "Erreur de démarrage");
      }
      const data = await res.json();
      currentJobId = data.job_id;
      const demoMode = data.demo_mode;

      $("loading-title").textContent = demoMode
        ? "Génération du plan (mode démo)..."
        : "Génération du plan par Claude Opus...";
      $("loading-message").textContent =
        "Cette étape prend généralement 20 à 40 secondes. On structure le livre, les parties, les chapitres et les bonus.";

      showStep("step-loading-plan");
      startPollingPlan();
    } catch (err) {
      showError(err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = "Lancer la génération";
    }
  }

  // =====================================================================
  //   POLLING — étape PLAN
  // =====================================================================
  function startPollingPlan() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/status/${currentJobId}`);
        const data = await res.json();

        if (data.error && data.step === "error") {
          stopPolling();
          showError(data.error);
          return;
        }

        if (data.message) {
          $("loading-message").textContent = data.message;
        }

        if (data.step === "plan" && data.plan) {
          // Plan disponible → afficher pour validation
          stopPolling();
          renderPlanReview(data.plan, data.cost_usd_estimate);
        }
      } catch (err) {
        console.error("Polling plan error:", err);
      }
    }, 1500);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  // =====================================================================
  //   AFFICHAGE DU PLAN POUR VALIDATION
  // =====================================================================
  function renderPlanReview(plan, costEstimate) {
    const summary = $("plan-summary");
    if (!summary) {
      // Pas de zone — passe directement à la rédaction
      continueGeneration();
      return;
    }

    const totalChapitres = (plan.parties || []).reduce(
      (sum, p) => sum + (p.chapitres || []).length,
      0
    );
    const totalBonus = (plan.bonus || []).length;

    summary.innerHTML = `
      <div class="plan-header">
        <div class="plan-eyebrow">Plan généré · à valider</div>
        <h2 class="plan-title">${escapeHtml(plan.titre || "Sans titre")}</h2>
        <div class="plan-subtitle">${escapeHtml(plan.sous_titre || "")}</div>
      </div>

      <div class="plan-stats">
        <div class="plan-stat">
          <div class="plan-stat-num">${plan.parties ? plan.parties.length : 0}</div>
          <div class="plan-stat-label">Parties</div>
        </div>
        <div class="plan-stat">
          <div class="plan-stat-num">${totalChapitres}</div>
          <div class="plan-stat-label">Chapitres</div>
        </div>
        <div class="plan-stat">
          <div class="plan-stat-num">${totalBonus}</div>
          <div class="plan-stat-label">Bonus</div>
        </div>
        <div class="plan-stat">
          <div class="plan-stat-num">~${(costEstimate || 0).toFixed(2)}$</div>
          <div class="plan-stat-label">Coût plan</div>
        </div>
      </div>

      <div class="plan-parts">
        ${(plan.parties || []).map((partie, pi) => `
          <div class="plan-part">
            <div class="plan-part-title">Partie ${pi + 1} · ${escapeHtml(partie.titre || "")}</div>
            <div class="plan-chapters">
              ${(partie.chapitres || []).map((c, ci) => `
                <div class="plan-chapter">
                  <span class="plan-chapter-num">${String(c.numero || ci + 1).padStart(2, "0")}</span>
                  <div class="plan-chapter-body">
                    <div class="plan-chapter-title">${escapeHtml(c.titre || "")}</div>
                    <div class="plan-chapter-deck">${escapeHtml(c.deck || "")}</div>
                    ${(c.sections || []).length > 0 ? `
                      <div class="plan-chapter-sections">
                        ${(c.sections || []).map((s) => `<span class="plan-section-pill">${escapeHtml(s.titre || "")}</span>`).join("")}
                      </div>
                    ` : ""}
                  </div>
                </div>
              `).join("")}
            </div>
          </div>
        `).join("")}
      </div>

      ${(plan.bonus && plan.bonus.length > 0) ? `
        <div class="plan-bonus">
          <div class="plan-bonus-title">Bonus inclus</div>
          <ul>
            ${plan.bonus.map((b) => `<li>${escapeHtml(typeof b === "string" ? b : (b.titre || JSON.stringify(b)))}</li>`).join("")}
          </ul>
        </div>
      ` : ""}
    `;

    showStep("step-plan-review");
  }

  // =====================================================================
  //   VALIDATION DU PLAN → RÉDACTION
  // =====================================================================
  async function continueGeneration() {
    if (!currentJobId) return;
    try {
      const res = await fetch(`/api/continue/${currentJobId}`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "Erreur de continuation" }));
        throw new Error(err.error || "Erreur de continuation");
      }
      $("writing-title").textContent = "Rédaction des chapitres...";
      $("writing-message").textContent = "Claude Sonnet rédige chaque chapitre selon les règles éditoriales Yeelen.";
      showStep("step-writing");
      startPollingWriting();
    } catch (err) {
      showError(err.message);
    }
  }

  // =====================================================================
  //   POLLING — étape RÉDACTION
  // =====================================================================
  function startPollingWriting() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/status/${currentJobId}`);
        const data = await res.json();

        if (data.error && data.step === "error") {
          stopPolling();
          showError(data.error);
          return;
        }

        if (data.message) {
          $("writing-message").textContent = data.message;
        }

        if (data.chapter_total > 0) {
          const pct = Math.min(
            100,
            Math.round((data.chapter_progress / data.chapter_total) * 100)
          );
          $("progress-fill").style.width = `${pct}%`;
          $("progress-text").textContent = `${data.chapter_progress} / ${data.chapter_total} chapitres`;
        }

        if (data.cost_usd_estimate) {
          $("progress-cost").textContent = `Coût estimé : ${data.cost_usd_estimate.toFixed(2)} $`;
        }

        if (data.step === "done" && data.files && data.files.pdf) {
          stopPolling();
          renderDone(data);
        }
      } catch (err) {
        console.error("Polling writing error:", err);
      }
    }, 2000);
  }

  // =====================================================================
  //   AFFICHAGE FINAL — Téléchargement
  // =====================================================================
  function renderDone(data) {
    $("dl-pdf").href = `/api/download/${currentJobId}/pdf`;
    $("dl-docx").href = `/api/download/${currentJobId}/docx`;
    $("dl-epub").href = `/api/download/${currentJobId}/epub`;

    const stats = $("done-stats");
    if (stats) {
      stats.innerHTML = `
        <div class="done-stat"><strong>${data.chapter_total}</strong> chapitres rédigés</div>
        <div class="done-stat"><strong>${data.cost_usd_estimate.toFixed(2)} $</strong> coût total estimé</div>
      `;
    }

    const cost = $("cost-summary");
    if (cost) {
      cost.textContent = `Coût total estimé pour cette génération : ${data.cost_usd_estimate.toFixed(2)} $ (≈ ${(data.cost_usd_estimate * 0.92).toFixed(2)} €)`;
    }

    showStep("step-done");
  }

  // =====================================================================
  //   ERREURS
  // =====================================================================
  function showError(msg) {
    stopPolling();
    $("error-message").textContent = msg;
    showStep("step-error");
  }

  // =====================================================================
  //   UTILS
  // =====================================================================
  function escapeHtml(str) {
    if (str == null) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // =====================================================================
  //   INIT — Brancher les événements
  // =====================================================================
  document.addEventListener("DOMContentLoaded", () => {
    // Formulaire principal
    const form = $("ebook-form");
    if (form) {
      form.addEventListener("submit", submitForm);
    }

    // Sélecteur de charte
    const charteSelect = $("charte");
    if (charteSelect) {
      charteSelect.addEventListener("change", updateCharterPreview);
      updateCharterPreview();
    }

    // Estimation de coût
    const pagesInput = $("pages");
    if (pagesInput) {
      pagesInput.addEventListener("input", updateCostEstimate);
      updateCostEstimate();
    }

    // Bouton "valider le plan"
    const validateBtn = $("btn-validate-plan");
    if (validateBtn) {
      validateBtn.addEventListener("click", continueGeneration);
    }

    // Bouton "recommencer"
    const restartBtn = $("btn-restart");
    if (restartBtn) {
      restartBtn.addEventListener("click", () => location.reload());
    }
  });
})();
