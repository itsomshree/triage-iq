const REFRESH_INTERVAL_MS = 30_000;

const els = {
    updatedAt: document.getElementById("updated-at"),
    refreshBtn: document.getElementById("refresh-btn"),
    themeToggle: document.getElementById("theme-toggle"),
    statAuto: document.getElementById("stat-auto"),
    statEscalate: document.getElementById("stat-escalate"),
    statFlag: document.getElementById("stat-flag"),
    statConfidence: document.getElementById("stat-confidence"),
    statLatency: document.getElementById("stat-latency"),
    categoryChart: document.getElementById("category-chart"),
    urgencyChart: document.getElementById("urgency-chart"),
    routingChart: document.getElementById("routing-chart"),
    ticketsBody: document.getElementById("tickets-body"),
    ticketModal: document.getElementById("ticket-modal"),
    modalBody: document.getElementById("modal-body"),
    modalClose: document.getElementById("modal-close"),
};

const ACTION_LABELS = {
    auto_answer: "Auto-answered",
    escalate: "Escalated",
    flag_for_review: "Flagged for review",
};

const PIE_SEGMENTS = [
    { key: "auto_answer_count", label: "Auto-answer", colorVar: "--auto" },
    { key: "escalate_count", label: "Escalate", colorVar: "--escalate" },
    { key: "flag_for_review_count", label: "Flag for review", colorVar: "--flag" },
];

const STAGE_LABELS = {
    classification: "Classified",
    routing: "Routed",
    rag_answer: "Answered from knowledge base",
    routing_override: "Routing overridden",
    escalation: "Escalated",
    pipeline_error: "Pipeline error",
};

async function fetchJSON(path) {
    const response = await fetch(path);
    if (!response.ok) {
        throw new Error(`${path} returned ${response.status}`);
    }
    return response.json();
}

function formatConfidence(value) {
    return value === null || value === undefined ? "—" : value.toFixed(2);
}

function formatLatency(ms) {
    if (ms === null || ms === undefined) return "—";
    return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;
}

function formatTimestamp(iso) {
    if (!iso) return "—";
    const date = new Date(iso);
    return date.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function renderStats(summary) {
    els.statAuto.textContent = summary.auto_answer_count;
    els.statEscalate.textContent = summary.escalate_count;
    els.statFlag.textContent = summary.flag_for_review_count;
    els.statConfidence.textContent = formatConfidence(summary.avg_confidence);
    els.statLatency.textContent = formatLatency(summary.avg_latency_ms);
}

function renderRoutingPie(container, summary) {
    const total = PIE_SEGMENTS.reduce(
        (sum, seg) => sum + (summary[seg.key] || 0),
        0
    );

    if (!total) {
        container.innerHTML =
            '<p class="bar-empty">Nothing routed yet — this fills in as tickets come through.</p>';
        return;
    }

    const svgNS = "http://www.w3.org/2000/svg";
    const size = 100;
    const center = size / 2;
    const radius = 38;
    const strokeWidth = 16;
    const circumference = 2 * Math.PI * radius;
    const reduceMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
    svg.classList.add("donut-svg");

    const group = document.createElementNS(svgNS, "g");
    group.setAttribute("transform", `rotate(-90 ${center} ${center})`);
    svg.appendChild(group);

    let cursorLen = 0;
    const arcs = PIE_SEGMENTS.map((seg, index) => {
        const value = summary[seg.key] || 0;
        const segLen = (value / total) * circumference;
        const startDeg = (cursorLen / circumference) * 360;
        cursorLen += segLen;

        const circle = document.createElementNS(svgNS, "circle");
        circle.setAttribute("cx", center);
        circle.setAttribute("cy", center);
        circle.setAttribute("r", radius);
        circle.setAttribute("fill", "none");
        circle.setAttribute("stroke", `var(${seg.colorVar})`);
        circle.setAttribute("stroke-width", strokeWidth);
        circle.setAttribute("transform", `rotate(${startDeg} ${center} ${center})`);
        circle.style.strokeDasharray = `${segLen} ${circumference}`;
        circle.style.strokeDashoffset = reduceMotion ? "0" : String(segLen);

        group.appendChild(circle);
        return { circle, delayMs: index * 450 };
    });

    const wrapper = document.createElement("div");
    wrapper.className = "donut";
    wrapper.appendChild(svg);

    const hole = document.createElement("div");
    hole.className = "donut-hole";
    hole.innerHTML = `<span class="donut-total">${total}</span><span class="donut-caption">tickets</span>`;
    wrapper.appendChild(hole);

    const legend = document.createElement("div");
    legend.className = "pie-legend";
    legend.innerHTML = PIE_SEGMENTS.map((seg) => {
        const value = summary[seg.key] || 0;
        const pct = Math.round((value / total) * 100);
        return `
      <div class="pie-legend-row">
        <span class="pie-legend-dot" style="background:var(${seg.colorVar})"></span>
        <span class="pie-legend-label">${seg.label}</span>
        <span class="pie-legend-value">${value} · ${pct}%</span>
      </div>
    `;
    }).join("");

    container.innerHTML = "";
    container.appendChild(wrapper);
    container.appendChild(legend);

    if (reduceMotion) return;

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            arcs.forEach(({ circle, delayMs }) => {
                circle.style.transition = `stroke-dashoffset 0.5s ease-out ${delayMs}ms`;
                circle.style.strokeDashoffset = "0";
            });
        });
    });
}

function renderBarChart(container, rows, labelKey) {
    if (!rows.length) {
        container.innerHTML =
            '<p class="bar-empty">Nothing routed yet — this fills in as tickets come through.</p>';
        return;
    }

    const max = Math.max(...rows.map((r) => r.count));

    container.innerHTML = rows
        .map((row) => {
            const label = row[labelKey].replace(/_/g, " ");
            const widthPct = max > 0 ? Math.max((row.count / max) * 100, 4) : 0;
            const fillClass =
                labelKey === "urgency"
                    ? `urgency-${String(row.urgency).toLowerCase()}`
                    : "";

            return `
        <div class="bar-row">
          <span class="bar-label">${label}</span>
          <span class="bar-track">
            <span class="bar-fill ${fillClass}" style="width:${widthPct}%"></span>
          </span>
          <span class="bar-count">${row.count}</span>
        </div>
      `;
        })
        .join("");
}

function renderTickets(tickets) {
    if (!tickets.length) {
        els.ticketsBody.innerHTML =
            '<tr><td colspan="6" class="empty-row">No tickets processed yet. Submit one to POST /tickets to see it here.</td></tr>';
        return;
    }

    els.ticketsBody.innerHTML = tickets
        .map((t) => {
            const rowClass = t.action ? `row-${t.action}` : "";
            const urgencyClass = t.urgency ? `urgency-${t.urgency}` : "";
            const actionLabel = t.action ? ACTION_LABELS[t.action] ?? t.action : "";

            return `
        <tr class="${rowClass} ticket-row" data-ticket-id="${t.ticket_id}" title="${actionLabel}">
          <td class="mono">${t.ticket_id}</td>
          <td class="subject-cell">${escapeHtml(t.subject)}</td>
          <td>${t.category ? t.category.replace(/_/g, " ") : "—"}</td>
          <td><span class="urgency-tag ${urgencyClass}">${t.urgency ?? "—"}</span></td>
          <td class="mono">${formatConfidence(t.confidence)}</td>
          <td class="mono">${formatTimestamp(t.created_at)}</td>
        </tr>
      `;
        })
        .join("");
}

function renderTimelineStep(log) {
    return `
    <div class="timeline-step step-${log.stage}">
      <span class="timeline-dot"></span>
      <p class="timeline-stage">${STAGE_LABELS[log.stage] ?? log.stage}</p>
      <p class="timeline-message">${escapeHtml(log.message)}</p>
      ${log.latency_ms !== null && log.latency_ms !== undefined
            ? `<p class="timeline-latency">${formatLatency(log.latency_ms)}</p>`
            : ""
        }
    </div>
  `;
}

function renderTicketModal(ticket, logs) {
    const { classification, routing_decision: routing, rag_answer: rag, escalation } =
        ticket;

    const badges = [];
    if (routing) {
        badges.push(
            `<span class="modal-badge badge-${routing.action}">${ACTION_LABELS[routing.action] ?? routing.action
            }</span>`
        );
    }
    if (classification) {
        badges.push(
            `<span class="modal-badge badge-urgency-${classification.urgency}">${classification.urgency}</span>`
        );
        badges.push(
            `<span class="modal-badge">${classification.category.replace(/_/g, " ")}</span>`
        );
    }

    const sections = [];

    if (classification) {
        sections.push(`
      <div class="modal-section">
        <h3>Classification</h3>
        <p>${escapeHtml(classification.summary)}</p>
        <p class="modal-sources">Confidence ${formatConfidence(classification.confidence)}</p>
      </div>
    `);
    }

    if (routing) {
        sections.push(`
      <div class="modal-section">
        <h3>Routing decision</h3>
        <p>${escapeHtml(routing.reasoning)}</p>
      </div>
    `);
    }

    if (rag) {
        sections.push(`
      <div class="modal-section">
        <h3>Answer ${rag.grounded ? "(grounded)" : "(not grounded)"}</h3>
        <p>${escapeHtml(rag.answer)}</p>
        ${rag.source_documents.length
                ? `<p class="modal-sources">Sources: ${rag.source_documents
                    .map(escapeHtml)
                    .join(", ")}</p>`
                : ""
            }
      </div>
    `);
    }

    if (escalation) {
        sections.push(`
      <div class="modal-section">
        <h3>Escalation</h3>
        <p>Assigned to <strong>${escapeHtml(escalation.assigned_team)}</strong>,
           priority ${escapeHtml(escalation.priority)}.</p>
      </div>
    `);
    }

    sections.push(`
    <div class="modal-section">
      <h3>Pipeline trace</h3>
      ${logs.length
            ? `<div class="timeline">${logs.map(renderTimelineStep).join("")}</div>`
            : `<p>No pipeline logs recorded for this ticket.</p>`
        }
    </div>
  `);

    els.modalBody.innerHTML = `
    <p class="modal-eyebrow">${escapeHtml(ticket.ticket_id)}</p>
    <h2 class="modal-subject">${escapeHtml(ticket.subject)}</h2>
    <p class="modal-body-text">${escapeHtml(ticket.body)}</p>
    <div class="modal-badges">${badges.join("")}</div>
    ${sections.join("")}
  `;
}

async function openTicketModal(ticketId) {
    els.ticketModal.hidden = false;
    document.body.style.overflow = "hidden";
    els.modalBody.innerHTML = '<p class="modal-loading">Loading…</p>';

    try {
        const [ticket, logs] = await Promise.all([
            fetchJSON(`/tickets/${encodeURIComponent(ticketId)}`),
            fetchJSON(`/tickets/${encodeURIComponent(ticketId)}/logs`),
        ]);
        renderTicketModal(ticket, logs);
    } catch (err) {
        els.modalBody.innerHTML =
            '<p class="modal-error">Couldn\'t load this ticket.</p>';
        console.error(err);
    }
}

function closeTicketModal() {
    els.ticketModal.hidden = true;
    document.body.style.overflow = "";
}

async function loadDashboard() {
    els.refreshBtn.disabled = true;
    els.refreshBtn.classList.add("is-loading");
    els.updatedAt.classList.add("updating");

    try {
        const [summary, categories, urgencies, tickets] = await Promise.all([
            fetchJSON("/dashboard/summary"),
            fetchJSON("/dashboard/category-breakdown"),
            fetchJSON("/dashboard/urgency-breakdown"),
            fetchJSON("/dashboard/recent-tickets?limit=25"),
        ]);

        renderStats(summary);
        renderRoutingPie(els.routingChart, summary);
        renderBarChart(els.categoryChart, categories, "category");
        renderBarChart(els.urgencyChart, urgencies, "urgency");
        renderTickets(tickets);

        els.updatedAt.textContent = `Updated ${new Date().toLocaleTimeString()}`;
    } catch (err) {
        els.updatedAt.textContent = "Couldn't reach the API — check it's running.";
        console.error(err);
    } finally {
        els.refreshBtn.disabled = false;
        els.refreshBtn.classList.remove("is-loading");
        els.updatedAt.classList.remove("updating");
    }
}

// --- Theme -------------------------------------------------------------
function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
    els.themeToggle.textContent = theme === "dark" ? "☀" : "☾";
}

els.themeToggle.textContent =
    document.documentElement.getAttribute("data-theme") === "dark" ? "☀" : "☾";

els.themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    applyTheme(current === "dark" ? "light" : "dark");
});

els.refreshBtn.addEventListener("click", loadDashboard);

els.ticketsBody.addEventListener("click", (event) => {
    const row = event.target.closest("tr[data-ticket-id]");
    if (row) openTicketModal(row.dataset.ticketId);
});

els.modalClose.addEventListener("click", closeTicketModal);

els.ticketModal.addEventListener("click", (event) => {
    if (event.target === els.ticketModal) closeTicketModal();
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !els.ticketModal.hidden) closeTicketModal();
});

loadDashboard();
setInterval(loadDashboard, REFRESH_INTERVAL_MS);