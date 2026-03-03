// ─────────────────────────────────────────────
// MODAL HELPERS
// ─────────────────────────────────────────────

function openModal(id) {
  document.getElementById(id).classList.add("active");
  document.body.style.overflow = "hidden";
}

function closeModal(id) {
  document.getElementById(id).classList.remove("active");
  document.body.style.overflow = "";
}

// Close modal when clicking the dark overlay
document.querySelectorAll(".modal-overlay").forEach(overlay => {
  overlay.addEventListener("click", function (e) {
    if (e.target === this) {
      closeModal(this.id);
    }
  });
});

// Close modals with Escape key
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    document.querySelectorAll(".modal-overlay.active").forEach(m => {
      closeModal(m.id);
    });
  }
});

// ─────────────────────────────────────────────
// UPDATE MODAL
// ─────────────────────────────────────────────

function openUpdate(id, name, total, attended) {
  document.getElementById("updateSubjectName").textContent = name;
  document.getElementById("updateTotal").value    = total;
  document.getElementById("updateAttended").value = attended;
  document.getElementById("updateForm").action    = `/update/${id}`;
  openModal("updateModal");
}

// ─────────────────────────────────────────────
// PREDICT MODAL
// ─────────────────────────────────────────────

let _predictData = {};

function openPredict(id, name, attended, total) {
  _predictData = { attended, total };
  document.getElementById("predictSubjectName").textContent = name;
  document.getElementById("extraTotal").value   = "";
  document.getElementById("extraAttend").value  = "";
  const result = document.getElementById("predictResult");
  result.classList.add("hidden");
  result.className = "predict-result hidden";
  openModal("predictModal");
}

async function runPredict() {
  const extraTotal  = parseInt(document.getElementById("extraTotal").value);
  const extraAttend = parseInt(document.getElementById("extraAttend").value);

  if (isNaN(extraTotal) || isNaN(extraAttend)) {
    alert("Please enter valid numbers for both fields.");
    return;
  }

  if (extraAttend > extraTotal) {
    alert("Classes to attend cannot exceed total future classes.");
    return;
  }

  const result = document.getElementById("predictResult");
  result.className = "predict-result";
  result.innerHTML = `<p style="color:var(--muted)">Calculating...</p>`;
  result.classList.remove("hidden");

  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        attended:     _predictData.attended,
        total:        _predictData.total,
        extra_total:  extraTotal,
        extra_attend: extraAttend,
      }),
    });

    const data = await response.json();

    if (data.error) {
      result.innerHTML = `<p style="color:var(--danger)">${data.error}</p>`;
      return;
    }

    const statusLabel = {
      safe:    "✔ Attendance will be SAFE",
      warning: "🔶 Approaching the limit",
      danger:  "⚠ Will be BELOW 75% — AT RISK",
    }[data.status];

    result.className = `predict-result res--${data.status}`;
    result.innerHTML = `
      <p class="p-pct">${data.predicted_pct}%</p>
      <p class="p-label">${statusLabel}</p>
    `;
  } catch (err) {
    result.innerHTML = `<p style="color:var(--danger)">Network error. Please try again.</p>`;
  }
}

// ─────────────────────────────────────────────
// AUTO-DISMISS FLASH MESSAGES
// ─────────────────────────────────────────────

document.querySelectorAll(".flash").forEach(flash => {
  setTimeout(() => {
    flash.style.transition = "opacity 0.5s ease";
    flash.style.opacity = "0";
    setTimeout(() => flash.remove(), 500);
  }, 4000);
});