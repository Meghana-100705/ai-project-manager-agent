const API_BASE = "https://ai-project-manager-agent.onrender.com";


/* =========================
   ELEMENTS
========================= */

const healthStatus =
  document.getElementById("healthStatus");

const runBtn =
  document.getElementById("runBtn");

const downloadBtn =
  document.getElementById("downloadBtn");

const copyBtn =
  document.getElementById("copyBtn");

const outputEl =
  document.getElementById("output");

const errorBox =
  document.getElementById("errorBox");

const metaEl =
  document.getElementById("meta");


let lastJson = null;


/* =========================
   ERROR HANDLING
========================= */

function showError(message) {

  errorBox.style.display = "block";

  errorBox.textContent = message;

}


function clearError() {

  errorBox.style.display = "none";

  errorBox.textContent = "";

}


/* =========================
   BACKEND HEALTH
========================= */

async function checkHealth() {

  try {

    const response =
      await fetch(`${API_BASE}/health`);

    if (!response.ok) {

      throw new Error();

    }

    const data =
      await response.json();

    if (data.status === "ok") {

      healthStatus.textContent =
        "Backend: online ✅";

    } else {

      healthStatus.textContent =
        "Backend: unknown";

    }

  } catch {

    healthStatus.textContent =
      "Backend: offline ❌";

  }

}


/* =========================
   DOWNLOAD JSON
========================= */

function downloadJsonFile(
  object,
  filename = "pm_agent_output.json"
) {

  const blob = new Blob(
    [
      JSON.stringify(object, null, 2)
    ],
    {
      type: "application/json"
    }
  );

  const url =
    URL.createObjectURL(blob);

  const anchor =
    document.createElement("a");

  anchor.href = url;

  anchor.download = filename;

  document.body.appendChild(anchor);

  anchor.click();

  anchor.remove();

  URL.revokeObjectURL(url);

}


/* =========================
   ESCAPE HTML
========================= */

function escapeHtml(value) {

  if (value === null ||
      value === undefined) {

    return "";

  }

  return String(value)

    .replaceAll("&", "&amp;")

    .replaceAll("<", "&lt;")

    .replaceAll(">", "&gt;")

    .replaceAll('"', "&quot;")

    .replaceAll("'", "&#039;");

}


/* =========================
   PRIORITY BADGE
========================= */

function priorityBadge(priority) {

  const value =
    String(priority || "unknown")
      .toLowerCase();

  let className = "badge-medium";

  if (value === "high") {

    className = "badge-high";

  }

  if (value === "low") {

    className = "badge-low";

  }

  return `
    <span class="badge ${className}">
      ${escapeHtml(value.toUpperCase())}
    </span>
  `;

}


/* =========================
   RENDER OVERVIEW
========================= */

function renderOverview(results) {

  const tickets =
    Array.isArray(results.generated_tickets)
      ? results.generated_tickets
      : [];


  const totalTickets =
    tickets.length;


  const totalPoints =
    tickets.reduce(
      (sum, ticket) =>
        sum +
        Number(
          ticket.estimated_story_points || 0
        ),
      0
    );


  const highPriority =
    tickets.filter(
      ticket =>
        String(ticket.priority)
          .toLowerCase() === "high"
    ).length;


  const teams =
    new Set(
      tickets
        .map(ticket => ticket.assigned_team)
        .filter(Boolean)
    );


  document.getElementById(
    "totalTickets"
  ).textContent = totalTickets;


  document.getElementById(
    "totalPoints"
  ).textContent = totalPoints;


  document.getElementById(
    "highPriority"
  ).textContent = highPriority;


  document.getElementById(
    "teamCount"
  ).textContent = teams.size;


  document.getElementById(
    "ticketCountLabel"
  ).textContent =
    `${totalTickets} ticket${totalTickets === 1 ? "" : "s"}`;

}


/* =========================
   TEAM ASSIGNMENT
========================= */

function renderTeams(tickets) {

  const container =
    document.getElementById(
      "teamAssignment"
    );


  const counts = {};


  tickets.forEach(ticket => {

    const team =
      ticket.assigned_team ||
      "Unassigned";

    counts[team] =
      (counts[team] || 0) + 1;

  });


  const teams =
    Object.entries(counts);


  if (!teams.length) {

    container.innerHTML =
      `<div class="empty">
        No team assignments available.
      </div>`;

    return;

  }


  container.innerHTML =
    teams.map(
      ([team, count]) => `

        <div class="team-item">

          <div class="team-name">
            ${escapeHtml(team)}
          </div>

          <div class="team-count">
            ${count}
            ticket${count === 1 ? "" : "s"}
          </div>

        </div>

      `
    ).join("");

}


/* =========================
   GENERATED TICKETS
========================= */

function renderTickets(tickets) {

  const tbody =
    document.getElementById(
      "ticketsTable"
    );


  if (!tickets.length) {

    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="empty">
          No tickets generated.
        </td>
      </tr>
    `;

    return;

  }


  tbody.innerHTML =
    tickets.map(
      (ticket, index) => {

        const dependencies =
          Array.isArray(ticket.dependencies)
            ? ticket.dependencies
            : [];


        return `

          <tr
            onclick="showTicketDetails(${index})"
          >

            <td>
              <span class="ticket-id">
                ${escapeHtml(ticket.ticket_id)}
              </span>
            </td>


            <td>
              ${escapeHtml(ticket.title)}
            </td>


            <td>
              ${escapeHtml(ticket.issue_type || "-")}
            </td>


            <td>
              <strong>
                ${escapeHtml(
                  ticket.estimated_story_points ?? "-"
                )}
              </strong>
            </td>


            <td>
              ${escapeHtml(
                ticket.assigned_team || "Unassigned"
              )}
            </td>


            <td>
              ${priorityBadge(ticket.priority)}
            </td>


            <td>
              ${
                dependencies.length
                  ? dependencies.map(
                      dep =>
                        `<span class="ticket-id">
                          ${escapeHtml(dep)}
                        </span>`
                    ).join(", ")
                  : "None"
              }
            </td>

          </tr>

        `;

      }
    ).join("");

}


/* =========================
   TICKET DETAILS
========================= */

let currentTickets = [];


function showTicketDetails(index) {

  const ticket =
    currentTickets[index];


  if (!ticket) return;


  const criteria =
    Array.isArray(ticket.acceptance_criteria)
      ? ticket.acceptance_criteria
      : [];


  const labels =
    Array.isArray(ticket.labels)
      ? ticket.labels
      : [];


  const dependencies =
    Array.isArray(ticket.dependencies)
      ? ticket.dependencies
      : [];


  document.getElementById(
    "ticketDetails"
  ).innerHTML = `

    <div class="ticket-detail">

      <div class="detail-title">

        ${escapeHtml(ticket.ticket_id)}
        —
        ${escapeHtml(ticket.title)}

      </div>


      <div class="detail-description">

        ${escapeHtml(ticket.description || "")}

      </div>


      <div style="margin-top:12px">

        ${priorityBadge(ticket.priority)}

        &nbsp;

        <span class="badge badge-low">
          ${escapeHtml(
            ticket.assigned_team || "Unassigned"
          )}
        </span>

        &nbsp;

        <span class="badge badge-medium">
          ${escapeHtml(
            ticket.estimated_story_points ?? "-"
          )} points
        </span>

      </div>


      ${
        labels.length
          ? `
            <div style="margin-top:12px">
              <div class="criteria-title">
                Labels
              </div>

              ${labels.map(
                label =>
                  `<span class="badge badge-low">
                    ${escapeHtml(label)}
                  </span>`
              ).join(" ")}
            </div>
          `
          : ""
      }


      <div class="criteria">

        <div class="criteria-title">
          Acceptance Criteria
        </div>

        ${
          criteria.length
            ? criteria.map(
                item =>
                  `<div>
                    ${escapeHtml(item)}
                  </div>`
              ).join("")
            : `<div>
                No acceptance criteria available.
              </div>`
        }

      </div>


      <div class="criteria">

        <div class="criteria-title">
          Dependencies
        </div>

        ${
          dependencies.length
            ? dependencies.map(
                dep =>
                  `<div>
                    ${escapeHtml(dep)}
                  </div>`
              ).join("")
            : `<div>
                No dependencies.
              </div>`
        }

      </div>

    </div>

  `;

}


/* =========================
   DEPENDENCIES
========================= */

function renderDependencies(tickets) {

  const container =
    document.getElementById(
      "dependencies"
    );


  const dependencies = [];


  tickets.forEach(ticket => {

    if (
      Array.isArray(ticket.dependencies)
    ) {

      ticket.dependencies.forEach(dep => {

        dependencies.push({

          ticket:
            ticket.ticket_id,

          dependsOn:
            dep

        });

      });

    }

  });


  if (!dependencies.length) {

    container.innerHTML = `
      <div class="empty">
        No dependencies detected.
      </div>
    `;

    return;

  }


  container.innerHTML =
    dependencies.map(
      dependency => `

        <div class="dependency">

          <span class="ticket-id">
            ${escapeHtml(
              dependency.ticket
            )}
          </span>

          <span class="dep-arrow">
            depends on →
          </span>

          <span class="ticket-id">
            ${escapeHtml(
              dependency.dependsOn
            )}
          </span>

        </div>

      `
    ).join("");

}


/* =========================
   BLOCKERS
========================= */

function renderBlockers(results) {

  const container =
    document.getElementById(
      "blockers"
    );


  const blockers =
    Array.isArray(
      results.blockers_detected
    )
      ? results.blockers_detected
      : [];


  if (!blockers.length) {

    container.innerHTML = `
      <div class="empty">
        No blockers detected.
      </div>
    `;

    return;

  }


  /*
    Limit only what is displayed.
    Complete data remains available
    through Download JSON.
  */

  const visible =
    blockers.slice(0, 10);


  container.innerHTML =
    visible.map(
      blocker => `

        <div class="blocker">

          <div class="blocker-title">

            ${escapeHtml(
              blocker.issue_id ||
              blocker.ticket_id ||
              "Issue"
            )}

            ${
              blocker.severity
                ? ` — ${escapeHtml(
                    blocker.severity
                  )}`
                : ""
            }

          </div>


          <div class="blocker-description">

            ${escapeHtml(
              blocker.description ||
              blocker.blocker_type ||
              "Blocker detected"
            )}

          </div>


          ${
            blocker.recommended_action
              ? `
                <div
                  class="blocker-description"
                  style="margin-top:8px"
                >
                  <strong>
                    Recommended:
                  </strong>

                  ${escapeHtml(
                    blocker.recommended_action
                  )}
                </div>
              `
              : ""
          }

        </div>

      `
    ).join("");


  if (blockers.length > 10) {

    container.innerHTML += `

      <div class="small">

        Showing 10 of
        ${blockers.length}
        blockers.
        Download JSON for complete data.

      </div>

    `;

  }

}


/* =========================
   DAILY SUMMARY
========================= */

function renderSummary(results) {

  const container =
    document.getElementById(
      "dailySummary"
    );


  const summary =
    results.daily_summary;


  if (!summary) {

    container.innerHTML = `
      <div class="empty">
        Daily summary not available.
      </div>
    `;

    return;

  }


  if (typeof summary === "string") {

    container.innerHTML = `
      <div class="summary">
        ${escapeHtml(summary)}
      </div>
    `;

    return;

  }


  /*
    If backend returns an object,
    display its important sections.
  */

  const sections = [];


  Object.entries(summary).forEach(
    ([key, value]) => {

      sections.push(`

        <div style="margin-bottom:15px">

          <div class="criteria-title">
            ${escapeHtml(
              key.replaceAll("_", " ")
            )}
          </div>

          <div class="summary">

            ${
              typeof value === "object"
                ? escapeHtml(
                    JSON.stringify(
                      value,
                      null,
                      2
                    )
                  )
                : escapeHtml(value)
            }

          </div>

        </div>

      `);

    }
  );


  container.innerHTML =
    sections.join("");

}


/* =========================
   COMPLETE DASHBOARD
========================= */

function renderDashboard(data) {

  const results =
    data?.results || {};


  const tickets =
    Array.isArray(
      results.generated_tickets
    )
      ? results.generated_tickets
      : [];


  currentTickets = tickets;


  /* Project information */

  document.getElementById(
    "projectTrack"
  ).textContent =
    `${data.team_id || "Project"} · ${
      data.track || "PM Agent"
    }`;


  /* Overview */

  renderOverview(results);


  /* Teams */

  renderTeams(tickets);


  /* Tickets */

  renderTickets(tickets);


  /* Dependencies */

  renderDependencies(tickets);


  /* Blockers */

  renderBlockers(results);


  /* Summary */

  renderSummary(results);


  /* First ticket automatically shown */

  if (tickets.length) {

    showTicketDetails(0);

  } else {

    document.getElementById(
      "ticketDetails"
    ).innerHTML = `
      <div class="empty">
        No generated tickets.
      </div>
    `;

  }

}


/* =========================
   RUN AGENT
========================= */

runBtn.addEventListener(
  "click",
  async () => {

    clearError();


    metaEl.textContent =
      "Running project manager agent...";


    runBtn.disabled = true;

    downloadBtn.disabled = true;

    copyBtn.disabled = true;


    const featureDescription =
      document
        .getElementById("feature")
        .value
        .trim();


    const backlogPath =
      document
        .getElementById("backlogPath")
        .value
        .trim();


    const backlogType =
      document
        .getElementById("backlogType")
        .value;


    if (!featureDescription) {

      showError(
        "Please enter a feature description."
      );

      metaEl.textContent = "";

      runBtn.disabled = false;

      return;

    }


    const payload = {

      feature_description:
        featureDescription,

      backlog_path:
        backlogPath
          ? backlogPath
          : null,

      backlog_type:
        backlogType

    };


    try {

      const start =
        performance.now();


      const response =
        await fetch(
          `${API_BASE}/run`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json"
            },

            body:
              JSON.stringify(payload)

          }
        );


      const text =
        await response.text();


      let data;


      try {

        data =
          JSON.parse(text);

      } catch {

        data = {
          raw: text
        };

      }


      if (!response.ok) {

        showError(
          data?.error ||
          `Backend error HTTP ${response.status}`
        );

        outputEl.textContent =
          JSON.stringify(
            data,
            null,
            2
          );

        return;

      }


      lastJson = data;


      /* Save complete JSON */

      outputEl.textContent =
        JSON.stringify(
          data,
          null,
          2
        );


      /* Render dashboard */

      renderDashboard(data);


      const ms =
        Math.round(
          performance.now() - start
        );


      metaEl.textContent =
        `Analysis completed in ${ms} ms`;


      downloadBtn.disabled = false;

      copyBtn.disabled = false;

    }

    catch (error) {

      showError(
        `Could not reach backend at ${API_BASE}. Is it running?`
      );

    }

    finally {

      runBtn.disabled = false;

    }

  }
);


/* =========================
   DOWNLOAD BUTTON
========================= */

downloadBtn.addEventListener(
  "click",
  () => {

    if (!lastJson) return;

    downloadJsonFile(
      lastJson,
      "pm_agent_output.json"
    );

  }
);


/* =========================
   COPY BUTTON
========================= */

copyBtn.addEventListener(
  "click",
  async () => {

    if (!lastJson) return;


    try {

      await navigator.clipboard.writeText(
        JSON.stringify(
          lastJson,
          null,
          2
        )
      );


      copyBtn.textContent =
        "Copied ✅";


      setTimeout(
        () => {

          copyBtn.textContent =
            "Copy JSON";

        },
        1000
      );

    }

    catch {

      showError(
        "Copy failed. Browser blocked clipboard access."
      );

    }

  }
);


/* =========================
   INITIALIZATION
========================= */

checkHealth();


setInterval(
  checkHealth,
  5000
);