const state = { all: [], filtered: [], track: "All collections", query: "", sort: "order", visible: 12, reader: null, preview: null };
const $ = (selector) => document.querySelector(selector);
const API_BASE = (window.ARCHIVE_API_URL || "").replace(/\/$/, "");
const api = (url, options) => fetch(`${API_BASE}${url}`, options).then(async (response) => {
  const contentType = response.headers.get("content-type") || "";
  const body = await response.text();
  let result;
  if (contentType.includes("application/json")) {
    try {
      result = JSON.parse(body);
    } catch {
      throw new Error("The backend returned invalid JSON.");
    }
  } else {
    throw new Error(
      API_BASE
        ? "The configured Python backend returned an unexpected response."
        : "The Python backend is not connected to this Vercel deployment. Start website.py locally or configure ARCHIVE_API_URL."
    );
  }
  if (!response.ok) throw new Error(result.error || "Request failed");
  return result;
});

async function init() {
  if ($("#results")) {
    try {
      state.all = await api("/api/catalog");
    } catch (error) {
      state.all = [];
      $("#results").innerHTML = `<div class="empty">${escapeHtml(error.message)}<br /><small>Connect this frontend to the Python API to load your transcript library.</small></div>`;
    }
    renderTracks(); render();
    $("#search").addEventListener("input", (event) => { state.query = event.target.value.trim().toLowerCase(); state.visible = 12; render(); });
    $("#sort").addEventListener("change", (event) => { state.sort = event.target.value; render(); });
    $("#load-more").addEventListener("click", () => { state.visible += 12; render(); });
  }
  if ($("#download-form")) {
    $("#download-form").addEventListener("submit", startDownload);
    $("#preview-button").addEventListener("click", previewPlaylist);
    $("#select-all").addEventListener("click", () => document.querySelectorAll("#video-list input").forEach((box) => { box.checked = true; }));
  }
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k" && $("#search")) { event.preventDefault(); $("#search").focus(); }
    if (event.key === "Escape") closeReader();
  });
  document.querySelectorAll("[data-close-reader]").forEach((element) => element.addEventListener("click", closeReader));
  setupReaderTools();
}

async function previewPlaylist() {
  const button = $("#preview-button"); button.disabled = true; button.textContent = "Loading preview…";
  try {
    state.preview = await api("/api/preview", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ playlist_url: $("#playlist-url").value }) });
    $("#playlist-preview").hidden = false;
    $("#preview-meta").textContent = `${state.preview.title} · ${state.preview.count} videos${state.preview.channel ? ` · ${state.preview.channel}` : ""}`;
    $("#video-list").innerHTML = state.preview.videos.map((video) => `<label class="video-option"><input type="checkbox" checked value="${escapeHtml(video.id)}"><span>${String(video.index).padStart(2, "0")}. ${escapeHtml(video.title)}</span><small>${video.duration ? formatDuration(video.duration) : ""}</small></label>`).join("");
  } catch (error) { showStatus(error.message, "error"); }
  button.disabled = false; button.innerHTML = "Preview playlist <span>→</span>";
}

async function startDownload(event) {
  event.preventDefault();
  const status = $("#download-status"); status.hidden = false; status.className = "download-status active"; status.innerHTML = "<span class=\"spinner\"></span> Adding job to the worker queue…";
  const selectedIds = new Set([...document.querySelectorAll("#video-list input:checked")].map((input) => input.value));
  const selected = state.preview ? state.preview.videos.filter((video) => selectedIds.has(video.id)) : [];
  if (state.preview && !selected.length) { showStatus("Select at least one video.", "error"); return; }
  try {
    const result = await api("/api/download", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({
      playlist_url: $("#playlist-url").value, languages: $("#languages").value, transcript_type: $("#transcript-type").value,
      videos: selected, settings: { output_folder: $("#output-folder").value, caption_format: $("#caption-format").value, filename_format: $("#filename-format").value, duplicate_handling: $("#duplicate-handling").value, playlist_title: state.preview?.title }
    })});
    pollDownload(result.id);
  } catch (error) { showStatus(`${error.message} Start the Python backend or configure the API URL for this deployment.`, "error"); }
}

async function pollDownload(id) {
  const status = $("#download-status");
  try {
    const result = await api(`/api/download/status/${id}`);
    const percent = result.total ? Math.min(100, Math.round((result.current / result.total) * 100)) : 0;
    const failures = result.failures || [];
    status.innerHTML = `<div class="progress-heading"><strong>${escapeHtml(statusLabel(result.status))}</strong><span>${result.current || 0} / ${result.total || "—"} videos</span></div><div class="progress-track"><i style="width:${percent}%"></i></div><span class="progress-title">${escapeHtml(result.title || "Preparing playlist")}</span>${failures.length ? `<div class="job-failures"><b>${failures.length} failed</b> ${failures.map((failure) => `<span>${escapeHtml(failure.title)}: ${escapeHtml(failure.error)}</span>`).join("")}<button type="button" data-retry="${id}">Retry failed videos</button></div>` : ""}<button type="button" class="cancel-job" data-cancel="${id}">${result.status === "cancelling" ? "Cancelling…" : "Cancel download"}</button>`;
    status.className = `download-status ${result.status === "error" ? "error" : result.status.startsWith("complete") ? "complete" : "active"}`;
    $(`[data-cancel="${id}"]`)?.addEventListener("click", () => api(`/api/download/${id}/cancel`, {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"}));
    $(`[data-retry="${id}"]`)?.addEventListener("click", () => { api(`/api/download/${id}/retry`, {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"}).then(() => pollDownload(id)); });
    if (!["complete", "complete_with_errors", "error", "cancelled"].includes(result.status)) window.setTimeout(() => pollDownload(id), 1000);
    else if (result.status.startsWith("complete")) { state.all = await api("/api/catalog"); if ($("#results")) { renderTracks(); render(); } }
  } catch (error) { showStatus(error.message, "error"); }
}

function statusLabel(status) { return ({queued: "Queued", downloading: "Downloading", cancelling: "Cancelling", complete: "Download complete", complete_with_errors: "Complete with failures", cancelled: "Download cancelled", error: "Download failed"})[status] || status; }
function showStatus(message, kind) { const status = $("#download-status"); status.hidden = false; status.className = `download-status ${kind}`; status.textContent = message; }
function formatDuration(seconds) { const minutes = Math.floor(seconds / 60); return `${minutes}:${String(seconds % 60).padStart(2, "0")}`; }

function renderTracks() {
  const counts = state.all.reduce((result, item) => { result[item.track] = (result[item.track] || 0) + 1; return result; }, {});
  const tracks = ["All collections", ...Object.keys(counts).sort()];
  $("#tracks").innerHTML = tracks.map((track) => `<div class="track ${track === state.track ? "active" : ""}" data-track="${escapeHtml(track)}"><span>${escapeHtml(track)}</span><span class="track-count">${track === "All collections" ? state.all.length : counts[track]}</span></div>`).join("");
  document.querySelectorAll(".track").forEach((element) => element.addEventListener("click", () => { state.track = element.dataset.track; state.visible = 12; renderTracks(); render(); }));
}
function render() {
  state.filtered = state.all.filter((item) => { const matchesTrack = state.track === "All collections" || item.track === state.track; const haystack = `${item.title} ${item.track} ${item.preview}`.toLowerCase(); return matchesTrack && (!state.query || haystack.includes(state.query)); });
  if (state.sort === "az") state.filtered.sort((a, b) => a.title.localeCompare(b.title));
  if (state.sort === "length") state.filtered.sort((a, b) => b.words - a.words);
  const shown = state.filtered.slice(0, state.visible);
  $("#results-title").textContent = state.query ? `Results for “${state.query}”` : state.track;
  $("#stats").innerHTML = `<span><strong>${state.all.length}</strong> transcripts</span><span><strong>${new Set(state.all.map((item) => item.track)).size}</strong> collections</span><span><strong>${Math.round(state.all.reduce((sum, item) => sum + item.words, 0) / 1000)}k</strong> words indexed</span>`;
  $("#results").innerHTML = shown.length ? shown.map(cardTemplate).join("") : '<div class="empty">No transcripts match that search.</div>';
  document.querySelectorAll(".card").forEach((card) => card.addEventListener("click", () => openReader(card.dataset.id)));
  $("#load-more").hidden = shown.length >= state.filtered.length;
}
function cardTemplate(item, index) { return `<article class="card" data-id="${encodeURIComponent(item.id)}"><div class="card-number">${String(index + 1).padStart(2, "0")}</div><div><h3 class="card-title">${escapeHtml(item.title)}</h3><div class="card-track">${escapeHtml(item.track)} · ${item.words.toLocaleString()} words</div><div class="card-preview">${escapeHtml(item.preview)}</div></div><div class="card-length">${Math.max(1, Math.round(item.words / 150))} min read</div></article>`; }

async function openReader(encodedId) {
  const data = await api(`/api/transcript/${encodeURIComponent(decodeURIComponent(encodedId))}`);
  state.reader = data; $("#reader-meta").textContent = data.track; $("#reader-title").textContent = data.title;
  $("#reader-reading-time").textContent = `${Math.max(1, Math.ceil(data.content.trim().split(/\s+/).length / 200))} min read`;
  renderReaderContent(data.content); buildToc(data.content);
  $("#reader").classList.add("open"); $("#reader").setAttribute("aria-hidden", "false"); document.body.style.overflow = "hidden";
}
function renderReaderContent(content) {
  const query = ($("#reader-search")?.value || "").trim();
  const parts = readerSections(content);
  $("#reader-content").innerHTML = parts.map((part, index) => `<p id="paragraph-${index}">${highlight(escapeHtml(part), query)}</p>`).join("");
}
function highlight(value, query) { if (!query) return value; return value.replace(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"), "<mark>$1</mark>"); }
function readerSections(content) {
  const paragraphs = content.split(/\n{2,}/).filter(Boolean);
  if (paragraphs.length > 1 || content.length < 700) return paragraphs;
  const sentences = content.match(/.*?[.!?](?:\s+|$)/g) || [content];
  const sections = [];
  for (let index = 0; index < sentences.length; index += 5) sections.push(sentences.slice(index, index + 5).join("").trim());
  return sections.filter(Boolean);
}
function buildToc(content) { const paragraphs = readerSections(content); $("#reader-toc").innerHTML = paragraphs.length > 1 ? paragraphs.map((part, index) => `<a href="#paragraph-${index}">${escapeHtml(part.slice(0, 60))}</a>`).join("") : ""; }
function setupReaderTools() {
  $("#reader-search")?.addEventListener("input", () => state.reader && renderReaderContent(state.reader.content));
  $("#reader-toc-toggle")?.addEventListener("click", () => { $("#reader-toc").hidden = !$("#reader-toc").hidden; });
  $("#reader-smaller")?.addEventListener("click", () => adjustFont(-1));
  $("#reader-larger")?.addEventListener("click", () => adjustFont(1));
  $("#reader-theme")?.addEventListener("click", () => $("#reader").classList.toggle("reader-light"));
  $("#reader-copy")?.addEventListener("click", async () => { if (state.reader) { await navigator.clipboard.writeText(state.reader.content); $("#reader-copy").textContent = "Copied"; } });
  $("#reader-download")?.addEventListener("click", () => { if (!state.reader) return; const blob = new Blob([state.reader.content], {type: "text/plain"}); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = `${state.reader.title}.txt`; link.click(); URL.revokeObjectURL(link.href); });
}
function adjustFont(delta) { const content = $("#reader-content"); const size = parseFloat(getComputedStyle(content).fontSize) + delta; content.style.fontSize = `${Math.max(12, Math.min(30, size))}px`; }
function closeReader() { $("#reader")?.classList.remove("open"); $("#reader")?.setAttribute("aria-hidden", "true"); document.body.style.overflow = ""; }
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[character])); }
init();
