const form = document.querySelector("#screen-form");
const results = document.querySelector("#results");
const summary = document.querySelector("#summary");
const status = document.querySelector("#status");

function tags(values, missing = false) {
  return (values || []).map(value => `<span class="skill ${missing ? "missing" : ""}">${value}</span>`).join("");
}
function render(items) {
  summary.innerHTML = `<div class="col-md-4"><div class="card p-3"><strong>${items.length}</strong><span>Processed</span></div></div><div class="col-md-4"><div class="card p-3"><strong>${items.filter(x => x.parsing_status === "success").length}</strong><span>Parsed successfully</span></div></div><div class="col-md-4"><div class="card p-3"><strong>${items.filter(x => (x.limitations_or_warnings || []).length).length}</strong><span>Flagged for review</span></div></div>`;
  results.innerHTML = `<table class="table align-middle"><thead><tr><th>Rank</th><th>Candidate</th><th>Score</th><th>Parsing</th><th>Matched skills</th><th>Missing skills</th><th>Review</th></tr></thead><tbody>${items.map((x, i) => `<tr><td>${i + 1}</td><td><a href="/api/candidates/${x.candidate_id}">${x.candidate_id}</a></td><td class="score">${x.final_score ?? "Incomplete"}</td><td>${x.parsing_status}</td><td>${tags(x.matched_skills)}</td><td>${tags(x.missing_skills, true)}</td><td><strong>${x.review_decision || "Pending"}</strong><div class="review-actions mt-2"><button class="btn btn-sm btn-success review-btn" data-id="${x.candidate_id}" data-decision="shortlist">Shortlist</button><button class="btn btn-sm btn-outline-danger review-btn" data-id="${x.candidate_id}" data-decision="reject">Reject</button><button class="btn btn-sm btn-outline-secondary review-btn" data-id="${x.candidate_id}" data-decision="needs-review">Needs review</button></div></td></tr>`).join("")}</tbody></table>`;
}
form.addEventListener("submit", async event => {
  event.preventDefault();
  status.textContent = "Processing...";
  const response = await fetch("/api/screen", { method: "POST", body: new FormData(form) });
  const payload = await response.json();
  if (!response.ok) { status.textContent = payload.error || "Processing failed."; return; }
  status.textContent = "Completed.";
  render(payload.candidates);
});

results.addEventListener("click", async event => {
  const button = event.target.closest(".review-btn");
  if (!button) return;
  const decision = button.dataset.decision;
  const notes = window.prompt(
    decision === "needs-review"
      ? "Optional reviewer note:"
      : "Enter a reviewer note explaining this decision (required):",
    ""
  );
  if (notes === null) return;
  if (decision !== "needs-review" && !notes.trim()) {
    status.textContent = "A reviewer note is required for shortlist or reject.";
    return;
  }
  button.disabled = true;
  const response = await fetch(`/api/candidates/${button.dataset.id}/review`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({decision, notes: notes.trim()})
  });
  const payload = await response.json();
  button.disabled = false;
  if (!response.ok) {
    status.textContent = payload.error || "Review could not be saved.";
    return;
  }
  const current = await fetch("/api/candidates");
  const listing = await current.json();
  status.textContent = `Review saved: ${decision}.`;
  render(listing.candidates);
});
