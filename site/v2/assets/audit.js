(() => {
  const dataElement = document.getElementById("audit-data");
  if (!dataElement) return;
  const data = JSON.parse(dataElement.textContent);
  const topicSelect = document.getElementById("audit-topic");
  const runSelect = document.getElementById("audit-run");
  const graphRoot = document.getElementById("audit-graph");
  const inspector = document.getElementById("audit-inspector");
  const notice = document.getElementById("audit-notice");
  const graphTitle = document.getElementById("graph-title");
  const graphKicker = document.getElementById("graph-kicker");
  const graphSummary = document.getElementById("graph-summary");
  const graphFallback = document.getElementById("graph-fallback");
  const viewButtons = [...document.querySelectorAll("[data-view]")];
  const schemaById = new Map(data.schema.nodes.map((node) => [node.id, node]));
  const params = new URLSearchParams(window.location.search);

  const state = {
    topic: params.get("topic") || (data.topics.some((topic) => topic.id === "korai-szelekcio") ? "korai-szelekcio" : data.topics[0].id),
    run: params.get("run"),
    view: ["execution", "database", "schema"].includes(params.get("view")) ? params.get("view") : "execution",
    selection: {
      execution: params.get("node"),
      database: params.get("artifact") || "transformation_proposal",
      schema: params.get("type") || "transformation_proposal",
    },
  };

  const TYPE_POSITIONS = {
    source: [20, 80], assumption: [20, 220], uncertainty: [20, 360], finding: [250, 180],
    transformation_family: [480, 40], transformation_proposal: [480, 210], lens_definition: [480, 390],
    coverage_ledger: [710, 20], lens_assessment: [710, 170], dilemma: [710, 330], research_question: [710, 490],
    decision_package: [960, 210], evaluation: [1190, 100], decision_readiness: [1190, 340], provenance: [960, 520],
  };

  const EXECUTION_POSITIONS = {
    research: [20, 190], registry: [260, 50], transformations: [260, 270], assessments: [510, 160],
    dilemmas: [760, 40], agenda: [760, 280], package: [1000, 160], evaluation: [1240, 50], readiness: [1240, 290],
  };

  const copy = {
    execution: {
      kicker: { en: "ACTUAL EXECUTION DAG", hu: "TÉNYLEGES FUTÁSI GRÁF" },
      title: { en: "What happened, and when?", hu: "Mi történt, és mikor?" },
    },
    database: {
      kicker: { en: "CONCRETE ARTIFACT DATABASE", hu: "KONKRÉT ARTEFAKTUM-ADATBÁZIS" },
      title: { en: "What exists, and what does it cite?", hu: "Mi létezik, és mire hivatkozik?" },
    },
    schema: {
      kicker: { en: "VERSIONED JSON SCHEMA", hu: "VERZIÓZOTT JSON SÉMA" },
      title: { en: "What may connect to what?", hu: "Mi kapcsolódhat mihez?" },
    },
  };

  function language() {
    return document.documentElement.dataset.language === "en" ? "en" : "hu";
  }

  function local(value) {
    if (value && typeof value === "object") return value[language()] || value.en || value.hu || "";
    return value == null ? "" : String(value);
  }

  function formatTime(value) {
    if (!value) return "—";
    const date = new Date(value);
    return new Intl.DateTimeFormat(language() === "hu" ? "hu-HU" : "en-GB", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    }).format(date);
  }

  function formatDuration(seconds) {
    if (seconds == null) return "—";
    if (seconds < 1) return `${Math.round(seconds * 1000)} ms`;
    if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)} s`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes} min ${Math.round(seconds % 60)} s`;
  }

  function element(name, className, text) {
    const node = document.createElement(name);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function currentRuns() {
    return data.runs.filter((run) => run.topic === state.topic);
  }

  function currentRun() {
    return data.runs.find((run) => run.id === state.run) || currentRuns().at(-1);
  }

  function populateTopics() {
    topicSelect.replaceChildren();
    data.topics.forEach((topic) => {
      const option = element("option", "", local(topic.title));
      option.value = topic.id;
      option.selected = topic.id === state.topic;
      topicSelect.append(option);
    });
  }

  function populateRuns(preserve = true) {
    const runs = currentRuns();
    if (!preserve || !runs.some((run) => run.id === state.run)) state.run = runs.at(-1).id;
    runSelect.replaceChildren();
    runs.forEach((run) => {
      const option = element("option", "", local(run.label));
      option.value = run.id;
      option.selected = run.id === state.run;
      runSelect.append(option);
    });
  }

  function updateUrl() {
    const next = new URL(window.location.href);
    next.searchParams.set("topic", state.topic);
    next.searchParams.set("run", state.run);
    next.searchParams.set("view", state.view);
    next.searchParams.delete("node");
    next.searchParams.delete("artifact");
    next.searchParams.delete("type");
    const key = state.view === "execution" ? "node" : state.view === "database" ? "artifact" : "type";
    if (state.selection[state.view]) next.searchParams.set(key, state.selection[state.view]);
    history.replaceState(null, "", next);
  }

  function executionGroup(nodeId) {
    if (nodeId.startsWith("research_")) return "research";
    if (nodeId.startsWith("assess_") || nodeId === "apply_scientific_lenses") return "assessments";
    if (nodeId.startsWith("register_")) return "registry";
    if (nodeId === "derive_transformations" || nodeId === "compile_transformations") return "transformations";
    if (nodeId === "identify_decision_dilemmas") return "dilemmas";
    if (nodeId === "build_research_agenda") return "agenda";
    if (nodeId === "assemble_decision_package") return "package";
    if (nodeId === "evaluate_decision_package") return "evaluation";
    if (nodeId === "assess_decision_readiness") return "readiness";
    return nodeId;
  }

  function groupTitle(id, count) {
    const labels = {
      research: { en: `${count} research steps`, hu: `${count} kutatási lépés` },
      registry: { en: "Perspective registry", hu: "Nézőpontjegyzék" },
      transformations: { en: "Derive transformations", hu: "Átalakítások levezetése" },
      assessments: { en: `${count} assessment steps`, hu: `${count} vizsgálati lépés` },
      dilemmas: { en: "Identify dilemmas", hu: "Dilemmák azonosítása" },
      agenda: { en: "Research agenda", hu: "Kutatási agenda" },
      package: { en: "Decision package", hu: "Döntési csomag" },
      evaluation: { en: "Package evaluation", hu: "Csomagértékelés" },
      readiness: { en: "Decision readiness", hu: "Döntési készültség" },
    };
    return labels[id] || { en: id.replaceAll("_", " "), hu: id.replaceAll("_", " ") };
  }

  function aggregateExecution(run) {
    const groups = new Map();
    run.execution.nodes.forEach((node) => {
      const id = executionGroup(node.id);
      if (!groups.has(id)) groups.set(id, {
        id, children: [], input_count: 0, output_count: 0, cache_hits: 0, failures: 0,
        output_types: {}, start: null, finish: null, sequence: node.sequence,
      });
      const group = groups.get(id);
      group.children.push(node);
      group.input_count += node.input_count;
      group.output_count += node.output_count;
      group.cache_hits += node.cache_hits;
      group.failures += node.failures;
      group.sequence = Math.min(group.sequence, node.sequence);
      if (node.start && (!group.start || node.start < group.start)) group.start = node.start;
      if (node.finish && (!group.finish || node.finish > group.finish)) group.finish = node.finish;
      Object.entries(node.output_types).forEach(([type, count]) => {
        group.output_types[type] = (group.output_types[type] || 0) + count;
      });
    });
    groups.forEach((group) => {
      group.title = groupTitle(group.id, group.children.length);
      group.disposition = group.failures ? "failed" : group.children.every((child) => child.disposition === "cache_hit") ? "cache_hit" : "executed";
      const start = group.start ? new Date(group.start) : null;
      const finish = group.finish ? new Date(group.finish) : null;
      group.duration_seconds = start && finish ? (finish - start) / 1000 : null;
    });
    const edges = new Map();
    run.execution.edges.forEach((edge) => {
      const from = executionGroup(edge.from);
      const to = executionGroup(edge.to);
      if (from === to) return;
      const key = `${from}|${to}`;
      if (!edges.has(key)) edges.set(key, { from, to, count: 0 });
      edges.get(key).count += edge.count;
    });
    return {
      nodes: [...groups.values()].sort((a, b) => a.sequence - b.sequence),
      edges: [...edges.values()], width: 1450, height: 500,
    };
  }

  function modelForView(run) {
    if (state.view === "execution") return aggregateExecution(run);
    if (state.view === "schema") {
      return { nodes: data.schema.nodes.map((node) => ({ ...node })), edges: data.schema.edges, width: 1400, height: 680 };
    }
    const counts = new Map(run.database.nodes.map((node) => [node.id, node]));
    return {
      nodes: data.schema.nodes.map((node) => ({ ...node, ...(counts.get(node.id) || { count: 0, example: null }) })),
      edges: run.database.edges, width: 1400, height: 680,
    };
  }

  function positionFor(node, index) {
    if (state.view === "execution") return EXECUTION_POSITIONS[node.id] || [20 + (index % 5) * 230, 60 + Math.floor(index / 5) * 140];
    return TYPE_POSITIONS[node.id] || [20 + (index % 5) * 230, 60 + Math.floor(index / 5) * 140];
  }

  function nodeLabel(node) {
    if (state.view === "execution") return local(node.title);
    return local(node.title);
  }

  function nodeCount(node) {
    if (state.view === "execution") return node.output_count;
    if (state.view === "database") return node.count;
    return node.fields.length;
  }

  function nodeMeta(node) {
    if (state.view === "execution") {
      if (node.children.length > 1) return language() === "hu" ? `${node.children.length} lépés · ${formatTime(node.start)}–${formatTime(node.finish)}` : `${node.children.length} steps · ${formatTime(node.start)}–${formatTime(node.finish)}`;
      return `${formatTime(node.start)} · ${formatDuration(node.duration_seconds)}`;
    }
    if (state.view === "database") return node.count ? (language() === "hu" ? "konkrét rekord" : "concrete records") : (language() === "hu" ? "nincs ebben a futásban" : "absent from this run");
    return language() === "hu" ? `${node.references.length} kapcsolat · v${node.version}` : `${node.references.length} references · v${node.version}`;
  }

  function createSvgEdge(svg, edge, positions, selected, maxWeight) {
    const from = positions.get(edge.from);
    const to = positions.get(edge.to);
    if (!from || !to) return;
    const startX = from[0] + 178;
    const startY = from[1] + 42;
    const endX = to[0];
    const endY = to[1] + 42;
    const bend = Math.max(45, Math.abs(endX - startX) * .45);
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", `M ${startX} ${startY} C ${startX + bend} ${startY}, ${endX - bend} ${endY}, ${endX} ${endY}`);
    path.setAttribute("marker-end", "url(#audit-arrow)");
    path.classList.add("graph-edge");
    if ((edge.count || 1) > Math.max(3, maxWeight * .45)) path.dataset.weight = "heavy";
    if (selected) {
      if (edge.from === selected || edge.to === selected) path.classList.add("is-related");
      else path.classList.add("is-muted");
    }
    svg.append(path);
  }

  function createGraphNode(node, position, relatedIds) {
    const button = element("button", "graph-node");
    button.type = "button";
    button.style.left = `${position[0]}px`;
    button.style.top = `${position[1]}px`;
    button.setAttribute("aria-pressed", String(state.selection[state.view] === node.id));
    button.setAttribute("aria-label", `${nodeLabel(node)}: ${nodeCount(node)}`);
    if (state.selection[state.view] && !relatedIds.has(node.id)) button.classList.add("is-muted");
    if (state.view === "database" && !node.count) button.classList.add("is-empty");
    if (node.id === "provenance") button.classList.add("is-provenance");
    if (state.view === "execution" && node.disposition === "cache_hit") button.classList.add("is-reused");
    if (state.view === "execution" && node.failures) button.classList.add("is-failed");
    button.append(element("span", "node-code", node.id));
    button.append(element("span", "node-title", nodeLabel(node)));
    button.append(element("strong", "node-count", String(nodeCount(node))));
    button.append(element("span", "node-meta", nodeMeta(node)));
    button.addEventListener("click", () => {
      state.selection[state.view] = node.id;
      updateUrl();
      render();
    });
    return button;
  }

  function renderGraph(model) {
    const previousScroll = graphRoot.scrollLeft;
    graphRoot.replaceChildren();
    const canvas = element("div", "graph-canvas");
    canvas.style.width = `${model.width}px`;
    canvas.style.height = `${model.height}px`;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("graph-edges");
    svg.setAttribute("viewBox", `0 0 ${model.width} ${model.height}`);
    svg.setAttribute("aria-hidden", "true");
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    marker.id = "audit-arrow";
    marker.setAttribute("viewBox", "0 0 10 10");
    marker.setAttribute("refX", "9"); marker.setAttribute("refY", "5"); marker.setAttribute("markerWidth", "6"); marker.setAttribute("markerHeight", "6"); marker.setAttribute("orient", "auto-start-reverse");
    const arrow = document.createElementNS("http://www.w3.org/2000/svg", "path");
    arrow.setAttribute("d", "M 0 0 L 10 5 L 0 10 z"); arrow.setAttribute("fill", "currentColor");
    marker.append(arrow); defs.append(marker); svg.append(defs);
    canvas.append(svg);

    const positions = new Map();
    model.nodes.forEach((node, index) => positions.set(node.id, positionFor(node, index)));
    const selected = state.selection[state.view];
    const relatedIds = new Set(selected ? [selected] : model.nodes.map((node) => node.id));
    if (selected) model.edges.forEach((edge) => {
      if (edge.from === selected || edge.to === selected) { relatedIds.add(edge.from); relatedIds.add(edge.to); }
    });
    const maxWeight = Math.max(1, ...model.edges.map((edge) => edge.count || edge.paths?.length || 1));
    model.edges.forEach((edge) => createSvgEdge(svg, edge, positions, selected, maxWeight));
    model.nodes.forEach((node) => canvas.append(createGraphNode(node, positions.get(node.id), relatedIds)));
    graphRoot.append(canvas);
    graphRoot.scrollLeft = previousScroll;
    graphFallback.textContent = model.nodes.map((node) => `${nodeLabel(node)}: ${nodeCount(node)}`).join("; ");
  }

  function factList(rows) {
    const list = element("dl", "inspector-facts");
    rows.forEach(([term, value]) => {
      const row = element("div");
      row.append(element("dt", "", term));
      row.append(element("dd", "", value));
      list.append(row);
    });
    return list;
  }

  function inspectorHeader(index, title, code) {
    inspector.replaceChildren();
    const top = element("div", "inspector-index");
    top.append(element("span", "", index));
    top.append(element("span", "", code));
    inspector.append(top);
    inspector.append(element("h3", "", title));
  }

  function appendSection(title, child) {
    const section = element("section", "inspector-section");
    section.append(element("h4", "", title));
    section.append(child);
    inspector.append(section);
  }

  function renderSchemaInspector(run, node, databaseMode) {
    const databaseNode = run.database.nodes.find((item) => item.id === node.id) || { count: 0, example: null };
    inspectorHeader(databaseMode ? (language() === "hu" ? "ADATBÁZIS-TÍPUS" : "DATABASE TYPE") : (language() === "hu" ? "SÉMA-TÍPUS" : "SCHEMA TYPE"), local(node.title), node.id);
    inspector.append(element("p", "inspector-description", local(node.description)));
    inspector.append(factList([
      [language() === "hu" ? "Sémaverzió" : "Schema version", node.version],
      [language() === "hu" ? "Azonosítóminta" : "ID pattern", node.id_pattern || "—"],
      [language() === "hu" ? "Rekord ebben a futásban" : "Records in this run", String(databaseNode.count)],
      [language() === "hu" ? "Kapcsolattípus" : "Reference fields", String(node.references.length)],
    ]));

    const refList = element("ul", "inspector-list");
    node.references.forEach((ref) => {
      const target = schemaById.get(ref.target);
      refList.append(element("li", "", `→ ${local(target?.title || ref.target)} · ${ref.many ? "0..n" : "1"} · ${ref.path}`));
    });
    appendSection(language() === "hu" ? "Hivatkozások" : "References", refList);

    const wrap = element("div", "table-wrap");
    const table = element("table", "field-table");
    const thead = element("thead");
    const headRow = element("tr");
    [language() === "hu" ? "Mező" : "Field", language() === "hu" ? "Alak" : "Shape", language() === "hu" ? "Kötelező" : "Required"].forEach((label) => headRow.append(element("th", "", label)));
    thead.append(headRow); table.append(thead);
    const tbody = element("tbody");
    node.fields.forEach((field) => {
      const row = element("tr");
      row.append(element("td", "", field.name)); row.append(element("td", "", field.shape)); row.append(element("td", "", field.required ? "✓" : "—"));
      tbody.append(row);
    });
    table.append(tbody); wrap.append(table);
    appendSection(language() === "hu" ? "Tartalmi mezők" : "Content fields", wrap);

    if (databaseMode && databaseNode.example) {
      const example = databaseNode.example;
      inspector.append(factList([
        [language() === "hu" ? "Példaazonosító" : "Example ID", example.id],
        [language() === "hu" ? "Állapot" : "Status", example.status],
        [language() === "hu" ? "Bejövő / kimenő" : "Incoming / outgoing", `${example.incoming} / ${example.outgoing}`],
        [language() === "hu" ? "Lenyomat" : "Hash", example.hash.slice(0, 16) + "…"],
      ]));
      appendSection(language() === "hu" ? "Valódi példa" : "Concrete example", element("p", "inspector-preview", example.preview));
    }
  }

  function renderExecutionInspector(node) {
    inspectorHeader(language() === "hu" ? "FUTÁSI LÉPÉS" : "EXECUTION STEP", local(node.title), node.id);
    const status = node.failures ? (language() === "hu" ? "sikertelen" : "failed") : node.disposition === "cache_hit" ? (language() === "hu" ? "újrafelhasznált" : "reused") : (language() === "hu" ? "végrehajtott" : "executed");
    inspector.append(factList([
      [language() === "hu" ? "Állapot" : "Status", status],
      [language() === "hu" ? "Kezdés" : "Started", formatTime(node.start)],
      [language() === "hu" ? "Befejezés" : "Finished", formatTime(node.finish)],
      [language() === "hu" ? "Időtartam" : "Duration", formatDuration(node.duration_seconds)],
      [language() === "hu" ? "Bemenet" : "Inputs", String(node.input_count)],
      [language() === "hu" ? "Kimenet" : "Outputs", String(node.output_count)],
      [language() === "hu" ? "Újrafelhasználás" : "Cache hits", String(node.cache_hits)],
    ]));
    const outputs = element("ul", "inspector-list");
    Object.entries(node.output_types).forEach(([type, count]) => outputs.append(element("li", "", `${local(schemaById.get(type)?.title || type)} · ${count}`)));
    appendSection(language() === "hu" ? "Létrehozott artefaktumok" : "Produced artifacts", outputs);
    if (node.children.length > 1) {
      const children = element("ul", "inspector-list");
      node.children.forEach((child) => children.append(element("li", "", `${local(child.title)} · ${formatTime(child.start)} · ${child.output_count}`)));
      appendSection(language() === "hu" ? "Összevont lépések" : "Grouped steps", children);
    }
  }

  function renderInspector(run, model) {
    let selected = model.nodes.find((node) => node.id === state.selection[state.view]);
    if (!selected) {
      selected = model.nodes.find((node) => node.id === (state.view === "execution" ? "transformations" : "transformation_proposal")) || model.nodes[0];
      state.selection[state.view] = selected.id;
    }
    if (state.view === "execution") renderExecutionInspector(selected);
    else renderSchemaInspector(run, selected, state.view === "database");
  }

  function renderHeading(run, model) {
    graphKicker.textContent = local(copy[state.view].kicker);
    graphTitle.textContent = local(copy[state.view].title);
    if (state.view === "execution") {
      const outputCount = model.nodes.reduce((sum, node) => sum + node.output_count, 0);
      graphSummary.textContent = language() === "hu" ? `${run.execution.nodes.length} tényleges lépés, ${run.execution.event_count} esemény és ${outputCount} rögzített kimenet. A párhuzamos kutatási és vizsgálati lépések összevonva látszanak.` : `${run.execution.nodes.length} actual steps, ${run.execution.event_count} events, and ${outputCount} recorded outputs. Parallel research and assessment steps are grouped.`;
    } else if (state.view === "database") {
      const present = model.nodes.filter((node) => node.count).length;
      const references = model.edges.reduce((sum, edge) => sum + edge.count, 0);
      graphSummary.textContent = language() === "hu" ? `${run.database.artifact_count} pontos artefaktumverzió, ${present} jelen lévő rekordtípus és ${references} típusos hivatkozás.` : `${run.database.artifact_count} exact artifact versions, ${present} present record types, and ${references} typed references.`;
    } else {
      graphSummary.textContent = language() === "hu" ? `${model.nodes.length} verziózott rekordtípus és ${model.edges.length} megengedett szemantikai kapcsolattípus. Az eredetnapló minden rekordhoz kötelező, ezért külön sávként jelenik meg.` : `${model.nodes.length} versioned record types and ${model.edges.length} permitted semantic relation types. Provenance is mandatory for every record and appears as a separate rail.`;
    }
  }

  function render() {
    const run = currentRun();
    state.run = run.id;
    viewButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.view === state.view)));
    notice.replaceChildren(element("p", "", local(run.notice)));
    const model = modelForView(run);
    renderHeading(run, model);
    renderGraph(model);
    renderInspector(run, model);
    updateUrl();
  }

  topicSelect.addEventListener("change", () => {
    state.topic = topicSelect.value;
    populateRuns(false);
    state.selection.execution = null;
    render();
  });
  runSelect.addEventListener("change", () => { state.run = runSelect.value; state.selection.execution = null; render(); });
  viewButtons.forEach((button) => button.addEventListener("click", () => { state.view = button.dataset.view; render(); }));

  populateTopics();
  populateRuns(true);
  render();

  const languageObserver = new MutationObserver((entries) => {
    if (entries.some((entry) => entry.attributeName === "data-language")) {
      populateTopics(); populateRuns(true); render();
    }
  });
  languageObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-language"] });
})();
