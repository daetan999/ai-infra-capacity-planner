(() => {
  "use strict";

  const endpoints = {
    scenarios: "/api/scenarios",
    comparison: "/api/scenarios/compare",
  };
  const exportSuffixes = {
    json: "/export?format=json",
    markdown: "/export?format=markdown",
  };
  const numericFields = new Set([
    "model_parameters_billions", "context_tokens", "tokens_per_request", "average_input_tokens",
    "average_output_tokens", "tokens_per_day", "requests_per_second",
    "concurrency", "peak_factor", "latency_target_ms", "availability_target_pct",
    "dataset_tb", "training_window_hours", "storage_tb", "storage_growth_pct", "growth_pct",
    "ingress_gbps", "egress_gbps", "target_utilization_pct", "batch_size",
  ]);
  const assumptionFields = new Set(["batch_size"]);
  const textInputFields = new Set(["model_family", "precision", "region"]);
  const modeLabels = {
    llm_training: "LLM training",
    llm_inference: "LLM inference",
    rag_inference: "RAG inference",
    vision_inference: "Vision inference",
    batch_ai_hpc: "Batch AI / HPC",
  };

  const state = { scenarios: [], activeId: null };
  const byId = (id) => document.getElementById(id);
  const form = byId("scenario-form");
  const list = byId("scenario-list");
  const emptyList = byId("scenario-list-empty");
  const states = {
    loading: byId("loading-state"),
    success: byId("success-state"),
    error: byId("error-state"),
  };

  function unwrap(payload) {
    if (payload && typeof payload === "object" && Object.hasOwn(payload, "data")) return payload.data;
    return payload;
  }

  function collection(payload) {
    const value = unwrap(payload);
    if (Array.isArray(value)) return value;
    if (value && Array.isArray(value.items)) return value.items;
    if (value && Array.isArray(value.scenarios)) return value.scenarios;
    return [];
  }

  function setRequestState(kind, message = "") {
    Object.values(states).forEach((element) => { element.hidden = true; });
    if (!kind || !states[kind]) return;
    states[kind].textContent = message;
    if (kind === "loading") {
      const spinner = document.createElement("span");
      spinner.className = "spinner";
      spinner.setAttribute("aria-hidden", "true");
      states[kind].prepend(spinner);
    }
    states[kind].hidden = false;
    if (kind === "success") window.setTimeout(() => { states.success.hidden = true; }, 3600);
  }

  async function request(url, options = {}) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      });
      if (!response.ok) {
        let detail = `Request failed (${response.status})`;
        try {
          const body = await response.json();
          detail = body.detail || body.error?.message || body.error || detail;
        } catch (_error) {
          // The status code remains the useful error when a response has no JSON body.
        }
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      return response.status === 204 ? null : response.json();
    } catch (error) {
      if (error.name === "AbortError") throw new Error("The planner timed out. Check the service and try again.");
      throw error;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function scenarioId(scenario) {
    return String(scenario.id ?? scenario.scenario_id ?? "");
  }

  function scenarioResult(scenario) {
    return scenario.result || scenario.sizing || scenario.outputs || scenario.capacity || {};
  }

  function modeLabel(scenario) {
    const mode = scenario.workload_mode || scenario.mode || scenario.inputs?.workload_mode;
    return modeLabels[mode] || String(mode || "Unspecified mode").replaceAll("_", " ");
  }

  function buildScenarioItem(scenario) {
    const item = document.createElement("li");
    const id = scenarioId(scenario);
    item.className = `scenario-item${id === state.activeId ? " is-active" : ""}`;
    item.dataset.search = `${scenario.name || "Untitled"} ${modeLabel(scenario)}`.toLowerCase();

    const open = document.createElement("button");
    open.type = "button";
    open.dataset.scenarioId = id;
    const title = document.createElement("strong");
    title.textContent = scenario.name || "Untitled scenario";
    const meta = document.createElement("small");
    meta.textContent = modeLabel(scenario);
    open.append(title, meta);

    const choose = document.createElement("input");
    choose.type = "checkbox";
    choose.className = "compare-check";
    choose.value = id;
    choose.setAttribute("aria-label", `Select ${scenario.name || "scenario"} for comparison`);
    item.append(open, choose);
    return item;
  }

  function renderScenarioList(filter = "") {
    list.replaceChildren();
    const needle = filter.trim().toLowerCase();
    const visible = state.scenarios.filter((scenario) => {
      const search = `${scenario.name || ""} ${modeLabel(scenario)}`.toLowerCase();
      return !needle || search.includes(needle);
    });
    visible.forEach((scenario) => list.append(buildScenarioItem(scenario)));
    emptyList.hidden = visible.length > 0;
    byId("scenario-count").textContent = String(state.scenarios.length);
  }

  function pick(source, names, fallback = null) {
    for (const name of names) {
      if (source && source[name] !== undefined && source[name] !== null) return source[name];
    }
    return fallback;
  }

  function formatValue(value, fallback = "—") {
    if (value === undefined || value === null || value === "") return fallback;
    if (Array.isArray(value)) return value.map((item) => formatValue(item)).join("–");
    if (typeof value === "object") {
      if (value.low !== undefined || value.high !== undefined || value.min !== undefined || value.max !== undefined) {
        const low = value.low ?? value.min ?? "?";
        const high = value.high ?? value.max ?? "?";
        return `${low}–${high}${value.unit ? ` ${value.unit}` : ""}`;
      }
      if (value.value !== undefined) return `${value.value}${value.unit ? ` ${value.unit}` : ""}`;
    }
    return String(value);
  }

  function setText(id, value) {
    byId(id).textContent = formatValue(value);
  }

  function renderList(id, values, fallback) {
    const target = byId(id);
    target.replaceChildren();
    const entries = Array.isArray(values) && values.length ? values : [fallback];
    entries.forEach((value) => {
      const item = document.createElement("li");
      item.textContent = typeof value === "string" ? value : formatValue(value);
      target.append(item);
    });
  }

  function renderQuestions(values) {
    const target = byId("validation-question-list");
    if (!Array.isArray(values) || !values.length) return;
    target.replaceChildren();
    values.forEach((value) => {
      const item = document.createElement("li");
      item.textContent = typeof value === "string" ? value : value.question || formatValue(value);
      target.append(item);
    });
  }

  function renderResult(scenario) {
    const result = scenarioResult(scenario);
    const capacity = result.capacity || result;
    const views = result.views || {};
    const confidence = result.confidence || {};
    const bottleneck = result.bottleneck || {};
    const commercial_band = result.commercial_band || {};
    const profile = result.profile || {};
    state.activeId = scenarioId(scenario);
    byId("workspace-mode").textContent = modeLabel(scenario);
    byId("workspace-title").textContent = scenario.name || "Capacity scenario";
    byId("empty-state").hidden = true;
    byId("result-content").hidden = false;
    byId("export-json").disabled = false;
    byId("export-markdown").disabled = false;

    const accelerators = pick(capacity, ["accelerators", "accelerator_count", "accelerator_range"]);
    const cost = capacity.monthly_cost_usd || commercial_band.monthly_range_usd || pick(result, ["monthly_cost", "monthly_cost_range", "cost"]);
    setText("result-accelerators", accelerators);
    setText("result-accelerators-range", profile.name || profile.illustrative_name || pick(result, ["accelerator_note", "accelerator_profile"], "Illustrative profile"));
    setText("result-cost", cost);
    setText("result-cost-range", commercial_band.label || pick(result, ["cost_basis"], "Indicative monthly band"));
    setText("result-planning-status", result.planning_status || "Planning status unavailable");
    setText("result-calibration-status", profile.calibration_status || "illustrative");
    setText("result-evidence-reference", profile.evidence_reference || "No evidence reference recorded");
    setText("result-measurement-scope", profile.measurement_scope || "No measurement scope recorded");
    setText("result-profile-limitations", profile.limitations || "Requires representative validation");
    setText("result-cpu", pick(capacity, ["cpu_cores", "cpu", "cpu_range"]));
    setText("result-memory", pick(capacity, ["memory", "memory_gb", "memory_range"]));
    setText("result-storage", pick(capacity, ["storage", "storage_tb", "storage_range"]));
    setText("result-storage-throughput", pick(capacity, ["storage_throughput_gbps"]));
    setText("result-network", pick(capacity, ["network", "network_gbps", "network_range"]));
    setText("result-racks", pick(capacity, ["racks", "rack_count", "rack_range"]));
    setText("result-power", pick(capacity, ["power", "power_kw", "power_range"]));
    setText("result-theoretical", views.theoretical_accelerators ?? pick(result, ["theoretical", "theoretical_throughput"]));
    setText("result-derated", views.derated_accelerators ?? pick(result, ["derated", "derated_throughput"]));
    const utilization = views.target_utilization_pct !== undefined
      ? `${views.target_utilization_pct}% target`
      : pick(result, ["utilization", "utilization_pct"], "—");
    setText("result-utilization", utilization);
    setText("result-utilization-detail", utilization);
    setText("result-bottleneck", bottleneck.primary || pick(result, ["primary_bottleneck"], "Needs benchmark"));
    setText("result-bottleneck-detail", bottleneck.reason || pick(result, ["bottleneck_detail", "bottleneck_rationale"], "Validate the limiting resource under sustained peak demand."));
    const confidenceLabel = confidence.level
      ? `${confidence.level} · ${confidence.score ?? "?"}/100`
      : pick(result, ["confidence_level", "confidence_score"], "Indicative");
    setText("result-confidence", confidenceLabel);
    setText("result-confidence-detail", confidence.basis || pick(result, ["confidence_detail", "confidence_rationale"], "Confidence improves as workload measurements replace planning assumptions."));
    byId("result-confidence-chip").textContent = formatValue(confidence.level || confidenceLabel);
    renderList("missing-inputs-list", confidence.missing_inputs || pick(result, ["missing_inputs", "missing"], []), "No missing inputs reported");
    renderQuestions(pick(result, ["validation_questions", "questions", "benchmark_questions"], []));
    renderScenarioList(byId("scenario-filter").value);
  }

  function populateForm(scenario) {
    const values = {
      ...(scenario.inputs || {}),
      ...(scenario.inputs?.assumption_overrides || {}),
      ...scenario,
    };
    Array.from(form.elements).forEach((control) => {
      if (!control.name || values[control.name] === undefined) return;
      control.value = values[control.name];
    });
    byId("target-utilization-value").textContent = `${byId("target-utilization").value}%`;
  }

  function collectScenario() {
    const data = new FormData(form);
    const inputs = {};
    const assumptionOverrides = {};
    let name = "";
    let description = "";
    let workloadMode = "";
    data.forEach((raw, key) => {
      const value = numericFields.has(key) ? Number(raw) : String(raw).trim();
      if (key === "name") name = value;
      else if (key === "description") description = value;
      else if (key === "workload_mode") workloadMode = value;
      else if (key === "accelerator_profile") inputs[key] = value;
      else if (assumptionFields.has(key)) assumptionOverrides[key] = value;
      else if (numericFields.has(key) || textInputFields.has(key)) inputs[key] = value;
    });
    inputs.assumption_overrides = assumptionOverrides;
    const payload = { name, workload_mode: workloadMode, inputs };
    if (description) payload.description = description;
    return payload;
  }

  async function loadScenarios() {
    setRequestState("loading", "Loading saved scenarios…");
    try {
      state.scenarios = collection(await request(endpoints.scenarios));
      renderScenarioList();
      setRequestState(null);
    } catch (error) {
      setRequestState("error", error.message);
    }
  }

  async function saveScenario(event) {
    event.preventDefault();
    if (!form.reportValidity()) return;
    setRequestState("loading", "Calculating capacity envelope…");
    try {
      const payload = unwrap(await request(endpoints.scenarios, {
        method: "POST",
        body: JSON.stringify(collectScenario()),
      }));
      const saved = payload.scenario || payload;
      state.scenarios = [saved, ...state.scenarios.filter((item) => scenarioId(item) !== scenarioId(saved))];
      renderResult(saved);
      setRequestState("success", "Scenario saved. Review confidence and validation questions next.");
    } catch (error) {
      setRequestState("error", error.message);
    }
  }

  async function openScenario(id) {
    const local = state.scenarios.find((scenario) => scenarioId(scenario) === id);
    if (!local) return;
    populateForm(local);
    renderResult(local);
  }

  function selectedScenarioIds() {
    return Array.from(
      document.querySelectorAll(".compare-check:checked"),
      (input) => Number(input.value),
    );
  }

  function comparisonRows(payload) {
    const unwrapped = unwrap(payload);
    if (Array.isArray(unwrapped)) return unwrapped;
    return unwrapped.comparison || unwrapped.scenarios || unwrapped.items || [];
  }

  function renderComparison(payload) {
    const scenarios = comparisonRows(payload);
    const body = byId("comparison-body");
    const head = byId("comparison-head");
    body.replaceChildren();
    head.replaceChildren();
    const headerRow = document.createElement("tr");
    const measureHeader = document.createElement("th");
    measureHeader.scope = "col";
    measureHeader.textContent = "Measure";
    headerRow.append(measureHeader);
    scenarios.forEach((scenario) => {
      const scenarioHeader = document.createElement("th");
      scenarioHeader.scope = "col";
      scenarioHeader.textContent = scenario.name || "Scenario";
      headerRow.append(scenarioHeader);
    });
    head.append(headerRow);
    const measures = [
      ["Scenario", (item) => item.name],
      ["Accelerators", (item) => {
        const result = scenarioResult(item);
        return pick(result.capacity || result, ["accelerators", "accelerator_count", "accelerator_range"]);
      }],
      ["Monthly cost", (item) => {
        const result = scenarioResult(item);
        return result.capacity?.monthly_cost_usd || result.commercial_band?.monthly_range_usd || pick(result, ["monthly_cost", "monthly_cost_range", "cost"]);
      }],
      ["Power", (item) => {
        const result = scenarioResult(item);
        return pick(result.capacity || result, ["power", "power_kw", "power_range"]);
      }],
      ["Confidence", (item) => {
        const result = scenarioResult(item);
        return result.confidence?.level || pick(result, ["confidence_level", "confidence_score"]);
      }],
      ["Calibration", (item) => scenarioResult(item).profile?.calibration_status || "Unavailable"],
    ];
    measures.forEach(([label, getValue]) => {
      const row = document.createElement("tr");
      const heading = document.createElement("th");
      heading.scope = "row";
      heading.textContent = label;
      row.append(heading);
      scenarios.forEach((scenario) => {
        const cell = document.createElement("td");
        cell.textContent = formatValue(getValue(scenario));
        row.append(cell);
      });
      body.append(row);
    });
  }

  async function compareSelected() {
    const ids = selectedScenarioIds();
    if (ids.length < 2 || ids.length > 3) {
      setRequestState("error", "Select two or three scenarios to compare.");
      return;
    }
    setRequestState("loading", "Comparing scenarios…");
    try {
      const payload = await request(endpoints.comparison, { method: "POST", body: JSON.stringify({ scenario_ids: ids }) });
      renderComparison(payload);
      setRequestState("success", "Comparison updated.");
      byId("comparison-panel").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      setRequestState("error", error.message);
    }
  }

  async function exportScenario(format) {
    if (!state.activeId) return;
    setRequestState("loading", `Preparing ${format === "json" ? "JSON" : "Markdown"} export…`);
    const suffix = exportSuffixes[format];
    const controller = new AbortController();
    try {
      const response = await fetch(`${endpoints.scenarios}/${encodeURIComponent(state.activeId)}${suffix}`, { signal: controller.signal });
      if (!response.ok) throw new Error(`Export failed (${response.status})`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `capacity-scenario-${state.activeId}.${format === "json" ? "json" : "md"}`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setRequestState("success", "Export downloaded.");
    } catch (error) {
      setRequestState("error", error.message);
    }
  }

  form.addEventListener("submit", saveScenario);
  list.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-scenario-id]");
    if (button) openScenario(button.dataset.scenarioId);
  });
  byId("scenario-filter").addEventListener("input", (event) => renderScenarioList(event.target.value));
  byId("target-utilization").addEventListener("input", (event) => { byId("target-utilization-value").textContent = `${event.target.value}%`; });
  byId("workload-mode").addEventListener("change", (event) => {
    const trainingWindow = byId("training-window");
    if (["llm_training", "batch_ai_hpc"].includes(event.target.value) && Number(trainingWindow.value) === 0) {
      trainingWindow.value = "168";
    }
  });
  byId("compare-scenarios").addEventListener("click", compareSelected);
  byId("export-json").addEventListener("click", () => exportScenario("json"));
  byId("export-markdown").addEventListener("click", () => exportScenario("markdown"));
  byId("refresh-scenarios").addEventListener("click", loadScenarios);
  byId("new-scenario").addEventListener("click", () => {
    form.reset();
    state.activeId = null;
    byId("workspace-mode").textContent = "New model";
    byId("workspace-title").textContent = "Build a capacity scenario";
    byId("empty-state").hidden = false;
    byId("result-content").hidden = true;
    byId("export-json").disabled = true;
    byId("export-markdown").disabled = true;
    renderScenarioList(byId("scenario-filter").value);
    byId("scenario-name").focus();
  });
  byId("reset-form").addEventListener("click", () => window.setTimeout(() => {
    byId("target-utilization-value").textContent = `${byId("target-utilization").value}%`;
  }, 0));

  loadScenarios();
})();
