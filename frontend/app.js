const API_BASE =
  "https://ai-project-manager-agent.onrender.com";


const healthStatus =
  document.getElementById("healthStatus");

const runBtn =
  document.getElementById("runBtn");

const downloadBtn =
  document.getElementById("downloadBtn");

const copyBtn =
  document.getElementById("copyBtn");

const errorBox =
  document.getElementById("errorBox");

const metaEl =
  document.getElementById("meta");

const emptyState =
  document.getElementById("emptyState");

const summarySection =
  document.getElementById("summarySection");

const ticketsSection =
  document.getElementById("ticketsSection");

const blockersSection =
  document.getElementById("blockersSection");

const dependenciesSection =
  document.getElementById("dependenciesSection");

const ticketsEl =
  document.getElementById("tickets");

const blockersEl =
  document.getElementById("blockers");

const dependenciesEl =
  document.getElementById("dependencies");

const dailySummaryEl =
  document.getElementById("dailySummary");

const ticketCount =
  document.getElementById("ticketCount");

const blockerCount =
  document.getElementById("blockerCount");

const dependencyCount =
  document.getElementById("dependencyCount");

const storyPoints =
  document.getElementById("storyPoints");

const ticketSectionCount =
  document.getElementById("ticketSectionCount");

const blockerSectionCount =
  document.getElementById("blockerSectionCount");

const dependencySectionCount =
  document.getElementById("dependencySectionCount");


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
   HEALTH CHECK
========================= */

async function checkHealth() {

  try {

    const response =
      await fetch(`${API_BASE}/health`);

    if (!response.ok) {

      throw new Error(
        `HTTP ${response.status}`
      );
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

  } catch (error) {

    healthStatus.textContent =
      "Backend: offline ❌";
  }
}


/* =========================
   DOWNLOAD
========================= */

function downloadJsonFile(
  object,
  filename = "pm_agent_results.json"
) {

  const blob =
    new Blob(
      [
        JSON.stringify(
          object,
          null,
          2
        )
      ],
      {
        type:
          "application/json"
      }
    );

  const url =
    URL.createObjectURL(blob);

  const anchor =
    document.createElement("a");

  anchor.href = url;

  anchor.download =
    filename;

  document.body.appendChild(
    anchor
  );

  anchor.click();

  anchor.remove();

  URL.revokeObjectURL(url);
}


/* =========================
   HELPERS
========================= */

function escapeHTML(value) {

  if (value === null ||
      value === undefined) {

    return "";
  }

  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


function resetResults() {

  emptyState.classList.remove(
    "hidden"
  );

  summarySection.classList.add(
    "hidden"
  );

  ticketsSection.classList.add(
    "hidden"
  );

  blockersSection.classList.add(
    "hidden"
  );

  dependenciesSection.classList.add(
    "hidden"
  );

  ticketsEl.innerHTML = "";

  blockersEl.innerHTML = "";

  dependenciesEl.innerHTML = "";

  dailySummaryEl.textContent = "";

  ticketCount.textContent = "0";

  blockerCount.textContent = "0";

  dependencyCount.textContent = "0";

  storyPoints.textContent = "0";
}


/* =========================
   RENDER TICKETS
========================= */

function renderTickets(tickets) {

  ticketsEl.innerHTML = "";

  if (!Array.isArray(tickets) ||
      tickets.length === 0) {

    ticketsEl.innerHTML =
      `<div class="small">
        No tickets generated.
      </div>`;

    return;
  }


  tickets.forEach(ticket => {

    const priority =
      String(
        ticket.priority || ""
      ).toLowerCase();

    const acceptance =
      Array.isArray(
        ticket.acceptance_criteria
      )
        ? ticket.acceptance_criteria
        : [];


    const dependencies =
      Array.isArray(
        ticket.dependencies
      )
        ? ticket.dependencies
        : [];


    const labels =
      Array.isArray(
        ticket.labels
      )
        ? ticket.labels
        : [];


    const card =
      document.createElement("div");

    card.className =
      "ticket";


    card.innerHTML = `

      <div class="ticket-header">

        <div>

          <div class="ticket-id">
            ${escapeHTML(
              ticket.ticket_id
            )}
          </div>

          <div class="ticket-title">
            ${escapeHTML(
              ticket.title
            )}
          </div>

        </div>

        <span class="badge">
          ${escapeHTML(
            ticket.issue_type || "task"
          )}
        </span>

      </div>


      <div class="ticket-description">
        ${escapeHTML(
          ticket.description
        )}
      </div>


      <div class="ticket-meta">

        <span class="tag">
          📊 ${
            escapeHTML(
              ticket.estimated_story_points ??
              0
            )
          } points
        </span>

        <span class="tag priority-${escapeHTML(priority)}">
          ⚡ ${
            escapeHTML(
              ticket.priority || "normal"
            )
          }
        </span>

        <span class="tag">
          👥 ${
            escapeHTML(
              ticket.assigned_team ||
              "unassigned"
            )
          }
        </span>

        ${
          labels.map(label => `
            <span class="tag">
              #${escapeHTML(label)}
            </span>
          `).join("")
        }

      </div>


      ${
        acceptance.length > 0
          ? `
            <div class="acceptance">

              <div class="acceptance-title">
                Acceptance Criteria
              </div>

              <ul>

                ${
                  acceptance.map(item => `
                    <li>
                      ${escapeHTML(item)}
                    </li>
                  `).join("")
                }

              </ul>

            </div>
          `
          : ""
      }


      ${
        dependencies.length > 0
          ? `
            <div class="acceptance">

              <div class="acceptance-title">
                Dependencies
              </div>

              <div class="small">
                ${dependencies.map(dep =>
                  escapeHTML(dep)
                ).join(", ")}
              </div>

            </div>
          `
          : ""
      }

    `;

    ticketsEl.appendChild(
      card
    );

  });
}


/* =========================
   RENDER BLOCKERS
========================= */

function renderBlockers(blockers) {

  blockersEl.innerHTML = "";

  if (!Array.isArray(blockers) ||
      blockers.length === 0) {

    blockersEl.innerHTML =
      `<div class="small">
        No blockers detected 🎉
      </div>`;

    return;
  }


  blockers.forEach(blocker => {

    const card =
      document.createElement("div");

    card.className =
      "blocker";


    card.innerHTML = `

      <div class="blocker-title">

        ⚠️ ${
          escapeHTML(
            blocker.issue_id ||
            blocker.ticket_id ||
            "Issue"
          )
        }

      </div>

      <div class="blocker-description">

        ${
          escapeHTML(
            blocker.description ||
            blocker.issue_title ||
            blocker.blocker_type ||
            "Blocker detected"
          )
        }

      </div>

      ${
        blocker.recommended_action
          ? `
            <div class="action">
              <strong>Recommended action:</strong>
              ${escapeHTML(
                blocker.recommended_action
              )}
            </div>
          `
          : ""
      }

    `;

    blockersEl.appendChild(
      card
    );

  });
}


/* =========================
   RENDER DEPENDENCIES
========================= */

function renderDependencies(
  dependencies
) {

  dependenciesEl.innerHTML = "";

  if (!Array.isArray(dependencies) ||
      dependencies.length === 0) {

    dependenciesEl.innerHTML =
      `<div class="small">
        No dependencies detected.
      </div>`;

    return;
  }


  dependencies.forEach(dep => {

    const card =
      document.createElement("div");

    card.className =
      "dependency";


    card.innerHTML = `

      <strong>
        ${escapeHTML(
          dep.issue_id ||
          dep.ticket_id ||
          "Issue"
        )}
      </strong>

      ${
        dep.issue_title
          ? `
            <span>
              — ${escapeHTML(
                dep.issue_title
              )}
            </span>
          `
          : ""
      }

      <span class="arrow">
        depends on
      </span>

      <strong>
        ${escapeHTML(
          dep.depends_on_id ||
          dep.depends_on ||
          "another issue"
        )}
      </strong>

      ${
        dep.depends_on_title
          ? `
            <span>
              — ${escapeHTML(
                dep.depends_on_title
              )}
            </span>
          `
          : ""
      }

    `;

    dependenciesEl.appendChild(
      card
    );

  });
}


/* =========================
   RENDER COMPLETE RESULT
========================= */

function renderResults(data) {

  const results =
    data?.results || {};


  const tickets =
    Array.isArray(
      results.generated_tickets
    )
      ? results.generated_tickets
      : [];


  const blockers =
    Array.isArray(
      results.blockers_detected
    )
      ? results.blockers_detected
      : [];


  const dependencies =
    Array.isArray(
      results.dependencies
    )
      ? results.dependencies
      : [];


  const totalPoints =
    tickets.reduce(
      (total, ticket) => {

        const points =
          Number(
            ticket.estimated_story_points
          );

        return total +
          (Number.isFinite(points)
            ? points
            : 0);

      },
      0
    );


  /* COUNTERS */

  ticketCount.textContent =
    tickets.length;

  blockerCount.textContent =
    blockers.length;

  dependencyCount.textContent =
    dependencies.length;

  storyPoints.textContent =
    totalPoints;


  ticketSectionCount.textContent =
    `${tickets.length} tickets`;

  blockerSectionCount.textContent =
    `${blockers.length} blockers`;

  dependencySectionCount.textContent =
    `${dependencies.length} dependencies`;


  /* EMPTY STATE */

  emptyState.classList.add(
    "hidden"
  );


  /* SUMMARY */

  const summary =
    results.daily_summary;


  if (summary) {

    dailySummaryEl.textContent =
      summary;

    summarySection.classList.remove(
      "hidden"
    );

  } else {

    summarySection.classList.add(
      "hidden"
    );
  }


  /* TICKETS */

  renderTickets(tickets);

  ticketsSection.classList.remove(
    "hidden"
  );


  /* BLOCKERS */

  renderBlockers(blockers);

  blockersSection.classList.remove(
    "hidden"
  );


  /* DEPENDENCIES */

  renderDependencies(
    dependencies
  );

  dependenciesSection.classList.remove(
    "hidden"
  );
}


/* =========================
   RUN AGENT
========================= */

runBtn.addEventListener(
  "click",
  async () => {

    clearError();

    resetResults();

    runBtn.disabled = true;

    downloadBtn.disabled = true;

    copyBtn.disabled = true;

    metaEl.textContent =
      "Analyzing feature...";

    lastJson = null;


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
                "application/json",

              "Accept":
                "application/json"
            },

            body:
              JSON.stringify(
                payload
              )
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
          error: text
        };

      }


      if (!response.ok) {

        showError(
          data?.error ||
          data?.detail ||
          `Backend error: HTTP ${response.status}`
        );

        metaEl.textContent = "";

        runBtn.disabled = false;

        return;
      }


      /*

        Your backend currently
        returns errors inside a
        200 response.

        Handle that as well.

      */

      if (data?.error) {

        showError(
          data.error
        );

        metaEl.textContent = "";

        runBtn.disabled = false;

        return;
      }


      lastJson = data;


      const elapsed =
        Math.round(
          performance.now() -
          start
        );


      renderResults(data);


      metaEl.textContent =
        `Analysis completed in ${elapsed} ms`;


      downloadBtn.disabled = false;

      copyBtn.disabled = false;


    } catch (error) {

      showError(
        `Could not reach backend at ${API_BASE}. Is it running?`
      );

      metaEl.textContent = "";

    } finally {

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
      lastJson
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


      const original =
        copyBtn.textContent;


      copyBtn.textContent =
        "Copied ✅";


      setTimeout(
        () => {

          copyBtn.textContent =
            original;

        },
        1000
      );


    } catch {

      showError(
        "Copy failed. Your browser blocked clipboard access."
      );

    }

  }
);


/* =========================
   INITIALIZE
========================= */

resetResults();

checkHealth();

setInterval(
  checkHealth,
  10000
);