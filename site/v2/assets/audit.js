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
      kicker: { en: "FROM QUESTION TO DATABASE", hu: "A KÉRDÉSTŐL AZ ADATBÁZISIG" },
      title: { en: "How was the database built?", hu: "Hogyan épült fel az adatbázis?" },
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
    if (nodeId.startsWith("root:")) return "roots";
    if (nodeId.startsWith("research_")) return "research";
    if (nodeId.startsWith("assess_") || nodeId === "apply_scientific_lenses") return "assessments";
    if (nodeId.startsWith("register_")) return "registry";
    if (nodeId === "derive_transformations" || nodeId === "compile_transformations") return "transformations";
    if (nodeId === "derive_option_space") return "option_space";
    if (nodeId === "approve_option_space") return "human_gate";
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
      roots: { en: "Admitted run inputs", hu: "Jóváhagyott futási bemenetek" },
      option_space: { en: "Derive option space", hu: "Opciótér levezetése" },
      human_gate: { en: "Human option-space gate", hu: "Emberi opciótér-kapu" },
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
    if (state.view === "execution") return run.execution;
    if (state.view === "schema") {
      return { nodes: data.schema.nodes.map((node) => ({ ...node })), edges: data.schema.edges, width: 1400, height: 680 };
    }
    const counts = new Map(run.database.nodes.map((node) => [node.id, node]));
    return {
      nodes: data.schema.nodes.map((node) => ({ ...node, ...(counts.get(node.id) || { count: 0, example: null }) })),
      edges: run.database.edges, width: 1400, height: 680,
    };
  }

  function executionRecordMap(run) {
    return new Map(run.execution.records.map((record) => [record.hash, record]));
  }

  function executionNodeMap(run) {
    return new Map(run.execution.nodes.map((node) => [node.id, node]));
  }

  function normalizeExecutionSelection(run) {
    const nodes = run.execution.nodes;
    const aliases = {
      research: nodes.find((node) => node.id.startsWith("research_"))?.id,
      transformations: "derive_transformations",
      assessments: nodes.find((node) => node.id.startsWith("assess_"))?.id,
      registry: "register_baseline_lenses",
      dilemmas: "identify_decision_dilemmas",
      agenda: "build_research_agenda",
      package: "assemble_decision_package",
      evaluation: "evaluate_decision_package",
      readiness: "assess_decision_readiness",
    };
    if (run.provenance_status === "complete" && state.selection.execution === "context") {
      state.selection.execution = "root:problem_brief";
    }
    if (aliases[state.selection.execution]) state.selection.execution = aliases[state.selection.execution];
    const isNode = nodes.some((node) => node.id === state.selection.execution);
    const isRecord = String(state.selection.execution || "").startsWith("record:");
    const isContext = ["context", "frames"].includes(state.selection.execution);
    if (!isNode && !isRecord && !isContext) state.selection.execution = "context";
  }

  function outputSummary(node) {
    return Object.entries(node.output_types)
      .map(([type, count]) => `${count} ${local(schemaById.get(type)?.title || type)}`)
      .join(" · ");
  }

  function selectExecution(id) {
    state.selection.execution = id;
    render();
    if (window.matchMedia("(max-width: 1100px)").matches) {
      requestAnimationFrame(() => inspector.scrollIntoView({ behavior: "smooth", block: "start" }));
    }
  }

  function flowCard(node, compact = false) {
    const button = element("button", `flow-card flow-card-call${compact ? " is-compact" : ""}`);
    button.type = "button";
    button.setAttribute("aria-pressed", String(state.selection.execution === node.id));
    const call = node.calls.at(-1);
    const kinds = {
      llm: { en: "LLM CALL", hu: "LLM-HÍVÁS" },
      human_gate: { en: "HUMAN GATE", hu: "EMBERI KAPU" },
      root: { en: "ADMITTED ROOT", hu: "JÓVÁHAGYOTT GYÖKÉR" },
      deterministic: { en: "DETERMINISTIC", hu: "DETERMINISZTIKUS" },
    };
    button.append(element("span", "flow-kind", local(kinds[node.kind] || kinds.deterministic)));
    button.append(element("strong", "flow-title", local(node.title)));
    button.append(element("span", "flow-agent", `${local(node.agent.name)} · ${call?.model || node.contract.model || "local"}`));
    button.append(element("span", "flow-output", outputSummary(node) || (language() === "hu" ? "nincs új rekord" : "no new record")));
    button.addEventListener("click", () => selectExecution(node.id));
    return button;
  }

  function contextCard(run, kind) {
    const context = run.execution.context;
    const button = element("button", "flow-card flow-card-input");
    button.type = "button";
    button.setAttribute("aria-pressed", String(state.selection.execution === kind));
    button.append(element("span", "flow-kind", language() === "hu" ? "EMBER ÁLTAL JÓVÁHAGYOTT BEMENET" : "HUMAN-APPROVED INPUT"));
    button.append(element("strong", "flow-title", kind === "frames" ? (language() === "hu" ? "Lefedendő változtatási irányok" : "Required transformation directions") : local(context.title)));
    button.append(element("span", "flow-agent", kind === "frames" ? `${context.frames.length} ${language() === "hu" ? "irány" : "directions"}` : local(context.public_question)));
    button.append(element("span", "flow-output", language() === "hu" ? "Ez még nem adatbázis-rekord." : "This is not a database record yet."));
    button.addEventListener("click", () => selectExecution(kind));
    return button;
  }

  function proposalCard(record) {
    const proposal = record.proposal;
    const button = element("button", "flow-card flow-card-record");
    button.type = "button";
    const selection = `record:${record.hash}`;
    button.setAttribute("aria-pressed", String(state.selection.execution === selection));
    button.append(element("span", "flow-kind", language() === "hu" ? "ADATBÁZIS-REKORD" : "DATABASE RECORD"));
    button.append(element("strong", "flow-title", proposal.title));
    button.append(element("span", "flow-agent", `${record.id} · ${proposal.finding_refs.length} ${language() === "hu" ? "hivatkozott megállapítás" : "cited findings"}`));
    button.append(element("span", "flow-output", proposal.goal));
    button.addEventListener("click", () => selectExecution(selection));
    return button;
  }

  function connector(label) {
    const node = element("div", "flow-connector");
    node.append(element("span", "", "↓"));
    node.append(element("b", "", label));
    return node;
  }

  function flowPhase(number, title, description, cards, className = "") {
    const section = element("section", `flow-phase ${className}`.trim());
    const header = element("header", "flow-phase-header");
    header.append(element("span", "flow-step", number));
    const copy = element("div");
    copy.append(element("h3", "", title));
    copy.append(element("p", "", description));
    header.append(copy);
    section.append(header);
    const grid = element("div", "flow-grid");
    cards.forEach((card) => grid.append(card));
    section.append(grid);
    return section;
  }

  function renderExecutionFlow(run) {
    normalizeExecutionSelection(run);
    graphRoot.replaceChildren();
    graphRoot.classList.add("is-flow");
    const flow = element("div", "execution-flow");
    const nodes = run.execution.nodes;
    const research = nodes.filter((node) => node.id.startsWith("research_"));
    const derive = nodes.find((node) => node.id === "derive_transformations");
    const register = nodes.find((node) => node.id === "register_baseline_lenses");
    const assessments = nodes.filter((node) => node.id.startsWith("assess_") && node.id !== "assess_decision_readiness");
    const downstreamIds = ["identify_decision_dilemmas", "build_research_agenda", "assemble_decision_package", "evaluate_decision_package", "assess_decision_readiness"];
    const downstream = downstreamIds.map((id) => nodes.find((node) => node.id === id)).filter(Boolean);
    const recordMap = executionRecordMap(run);
    const proposals = run.execution.proposals.map((hash) => recordMap.get(hash)).filter(Boolean);

    if (run.provenance_status === "complete") {
      const problemRoot = nodes.find((node) => node.id === "root:problem_brief");
      const lensRoots = nodes.filter((node) => node.id.startsWith("root:lens_"));
      const deriveOptions = nodes.find((node) => node.id === "derive_option_space");
      const optionGate = nodes.find((node) => node.id === "approve_option_space");
      flow.append(flowPhase("00", language() === "hu" ? "Pontos, jóváhagyott gyökerek" : "Exact admitted roots", language() === "hu" ? "A brief és a szakmai lencsék hash-elt adatbázis-rekordok; ezek a RunPlan változtathatatlan bemenetei." : "The brief and professional lenses are hashed database records and immutable RunPlan inputs.", [flowCard(problemRoot), ...lensRoots.map((node) => flowCard(node, true))], "phase-input"));
      flow.append(connector(language() === "hu" ? "ugyanaz a brief + egy pontos lencse-artifakt minden kutatóágon" : "the same brief + one exact lens artifact on each research branch"));
      flow.append(flowPhase("01", language() === "hu" ? `${research.length} explicit kutatóág` : `${research.length} explicit research branches`, language() === "hu" ? "Minden kártya külön node, saját deklarált bemenetekkel, prompttal és válaszlenyomattal." : "Every card is a separate node with declared inputs, prompt, and response hash.", research.map((node) => flowCard(node)), "phase-parallel"));
      flow.append(connector(language() === "hu" ? "a friss megállapításokból új opciótér-jelölt készül" : "fresh findings produce a new option-space candidate"));
      flow.append(flowPhase("02", language() === "hu" ? "Opciótér levezetése" : "Derive option space", language() === "hu" ? "Ez az LLM-lépés még nem kap jóváhagyott irányokat: kizárólag a briefből és a friss kutatási rekordokból dolgozik." : "This LLM step receives no approved directions; it uses only the brief and fresh research records.", [flowCard(deriveOptions)], "phase-synthesis"));
      flow.append(connector(language() === "hu" ? "egy pontos jelölthash emberi jóváhagyása" : "human approval of one exact candidate hash"));
      flow.append(flowPhase("03", language() === "hu" ? "Emberi opciótér-kapu" : "Human option-space gate", language() === "hu" ? "A kapu változtatás nélkül fogadja be vagy küldi vissza a jelöltet. Más hashhez új döntés kell." : "The gate admits the candidate unchanged or sends it back. A different hash requires a new decision.", [flowCard(optionGate)], "phase-input"));
      flow.append(connector(language() === "hu" ? "jóváhagyott opciótér + friss bizonyítékok" : "approved option space + fresh evidence"));
      flow.append(flowPhase("04", language() === "hu" ? "Átalakítások levezetése" : "Derive transformations", language() === "hu" ? "Az LLM itt már a jóváhagyott opciótér-artifaktot kapja, és minden irány lefedését géppel ellenőrzött jegyzékben rögzíti." : "The LLM now receives the approved option-space artifact and records machine-checked coverage of every direction.", [flowCard(derive), ...proposals.map(proposalCard)], "phase-records"));
      flow.append(connector(language() === "hu" ? "minden átalakítás × minden szakmai nézőpont" : "every transformation × every professional perspective"));
      flow.append(flowPhase("05", language() === "hu" ? `${assessments.length} szakmai vizsgálat` : `${assessments.length} professional assessments`, language() === "hu" ? "Minden node ugyanazokat a javaslatokat, a saját lencsét és a saját kutatási eredményeit kapja." : "Each node receives the same proposals, its exact lens, and its own research findings.", assessments.map((node) => flowCard(node, true)), "phase-parallel"));
      flow.append(connector(language() === "hu" ? "dilemmák → kutatási agenda → csomag → értékelés → készültség" : "dilemmas → research agenda → package → evaluation → readiness"));
      flow.append(flowPhase("06", language() === "hu" ? "Összeállítás és ellenőrzés" : "Assembly and checks", language() === "hu" ? "Az utolsó node-ok is kizárólag a RunPlanban deklarált rekordokat olvassák." : "The final nodes also read only records declared by the RunPlan.", downstream.map((node) => flowCard(node, true)), "phase-downstream"));
      graphRoot.append(flow);
      graphFallback.textContent = nodes.map((node) => `${local(node.title)}: ${node.output_count}`).join("; ");
      return;
    }

    flow.append(flowPhase("00", language() === "hu" ? "Kiinduló kérdés" : "Starting question", language() === "hu" ? "A futás ezt az ember által jóváhagyott problémafelvetést kapta. Nem LLM állította elő ebben a futásban." : "The run received this human-approved problem statement. It was not generated by an LLM in this run.", [contextCard(run, "context")], "phase-input"));
    flow.append(connector(language() === "hu" ? "ugyanaz a brief + külön agent-leírás minden ágon" : "the same brief + a different agent definition on each branch"));
    flow.append(flowPhase("01", language() === "hu" ? `${research.length} párhuzamos kutatóág` : `${research.length} parallel research branches`, language() === "hu" ? "Mindegyik külön LLM-folyamat: webes kutatás, majd strukturált válasz. Egy kártya egy valódi futási node." : "Each is a separate LLM process: web research followed by a structured answer. One card is one actual execution node.", research.map((node) => flowCard(node)), "phase-parallel"));
    flow.append(connector(language() === "hu" ? `${research.reduce((sum, node) => sum + (node.output_types.finding || 0), 0)} megállapítás + források + feltételezések + bizonytalanságok` : `${research.reduce((sum, node) => sum + (node.output_types.finding || 0), 0)} findings + sources + assumptions + uncertainties`));
    flow.append(flowPhase("02", language() === "hu" ? "Átalakítások levezetése" : "Derive transformations", language() === "hu" ? "A transformation_architect agent egyszerre megkapta a kutatási rekordokat és a jóváhagyott lefedési irányokat." : "The transformation_architect agent received the research records and the approved coverage directions together.", [contextCard(run, "frames"), flowCard(derive)], "phase-synthesis"));
    flow.append(connector(language() === "hu" ? `${proposals.length} külön átalakítási rekord — mind ugyanennek az LLM-hívásnak a kimenete` : `${proposals.length} distinct transformation records — all outputs of this LLM call`));
    flow.append(flowPhase("03", language() === "hu" ? "Az adatbázisba írt átalakítások" : "Transformations written to the database", language() === "hu" ? "Kattints egy átalakításra: látható lesz az előállító agent, a prompt és a pontos megállapítások, amelyekre hivatkozik." : "Select a transformation to see its producing agent, prompt, and the exact findings it cites.", proposals.map(proposalCard), "phase-records"));
    flow.append(connector(language() === "hu" ? "minden átalakítás × minden szakmai nézőpont" : "every transformation × every professional perspective"));
    flow.append(flowPhase("04", language() === "hu" ? `${assessments.length} párhuzamos szakmai vizsgálat` : `${assessments.length} parallel professional assessments`, language() === "hu" ? "A nézőpontjegyzék determinisztikusan rögzül, majd minden agent mind a hat változtatást értékeli." : "The perspective registry is recorded deterministically, then every agent evaluates all six transformations.", [flowCard(register, true), ...assessments.map((node) => flowCard(node, true))], "phase-parallel"));
    flow.append(connector(language() === "hu" ? "értékelésekből dilemmák, kutatási kérdések és döntési csomag" : "assessments become dilemmas, research questions, and a decision package"));
    flow.append(flowPhase("05", language() === "hu" ? "Összeállítás és ellenőrzés" : "Assembly and checks", language() === "hu" ? "Az utolsó node-ok már az előző rekordokra hivatkozva építik és ellenőrzik a döntési csomagot." : "The final nodes build and check the decision package by referencing the previous records.", downstream.map((node) => flowCard(node, true)), "phase-downstream"));
    graphRoot.append(flow);
    graphFallback.textContent = nodes.map((node) => `${local(node.title)}: ${node.output_count}`).join("; ");
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

  function recordList(run, hashes, emptyText) {
    const recordMap = executionRecordMap(run);
    const list = element("ul", "inspector-list inspector-records");
    hashes.map((hash) => recordMap.get(hash)).filter(Boolean).forEach((record) => {
      const item = element("li");
      const heading = element("b", "", `${record.id} · ${local(schemaById.get(record.type)?.title || record.type)}`);
      item.append(heading);
      item.append(element("span", "", record.preview));
      list.append(item);
    });
    if (!list.childElementCount) list.append(element("li", "", emptyText));
    return list;
  }

  function collapsibleRecordGroups(run, groups) {
    const wrapper = element("div", "inspector-details-stack");
    Object.entries(groups).forEach(([name, hashes], index) => {
      const details = element("details", "inspector-details");
      if (index === 0 && hashes.length <= 20) details.open = true;
      details.append(element("summary", "", `${name} · ${hashes.length}`));
      details.append(recordList(run, hashes, language() === "hu" ? "Nincs rekord." : "No records."));
      wrapper.append(details);
    });
    return wrapper;
  }

  function promptStack(prompts) {
    const wrapper = element("div", "inspector-details-stack");
    prompts.forEach((prompt) => {
      const details = element("details", "inspector-details prompt-details");
      details.append(element("summary", "", prompt.name));
      const pre = element("pre", "prompt-text");
      pre.append(element("code", "", prompt.text));
      details.append(pre);
      wrapper.append(details);
    });
    if (!prompts.length) wrapper.append(element("p", "inspector-preview", language() === "hu" ? "Ez a node nem indított LLM-hívást, ezért nincs promptja." : "This node did not make an LLM call, so it has no prompt."));
    return wrapper;
  }

  function renderContextInspector(run, kind) {
    const context = run.execution.context;
    if (kind === "frames") {
      inspectorHeader(language() === "hu" ? "EMBERI BEMENET" : "HUMAN INPUT", language() === "hu" ? "Lefedendő változtatási irányok" : "Required transformation directions", "approved_frames");
      inspector.append(element("p", "inspector-description", language() === "hu" ? "Ezeket az irányokat a transformation_architect promptja kötelező lefedési kapuként kapta meg." : "The transformation_architect prompt received these directions as mandatory coverage gates."));
      const list = element("ul", "inspector-list inspector-records");
      context.frames.forEach((frame) => {
        const item = element("li");
        item.append(element("b", "", `${frame.id} · ${local(frame.title)}`));
        item.append(element("span", "", local(frame.scope)));
        list.append(item);
      });
      appendSection(language() === "hu" ? "Jóváhagyott irányok" : "Approved directions", list);
      return;
    }
    inspectorHeader(language() === "hu" ? "FUTÁSI BEMENET" : "RUN INPUT", local(context.title), "problem_brief");
    inspector.append(element("p", "inspector-description", local(context.public_question)));
    appendSection(language() === "hu" ? "Problémafelvetés" : "Problem statement", element("p", "inspector-preview", local(context.problem_statement)));
    appendSection(language() === "hu" ? "Hatókör" : "Scope", element("p", "inspector-preview", local(context.scope)));
    inspector.append(element("p", "inspector-boundary", language() === "hu" ? "Ez a production futás bemenete volt; nem állítjuk, hogy ebben a DAG-ban egy LLM készítette." : "This was an input to the production run; the DAG does not claim an LLM generated it here."));
  }

  function renderProposalInspector(run, record) {
    const proposal = record.proposal;
    const nodeMap = executionNodeMap(run);
    const producer = nodeMap.get(record.producer);
    const recordById = new Map(run.execution.records.map((item) => [item.id, item]));
    inspectorHeader(language() === "hu" ? "ÁTALAKÍTÁSI REKORD" : "TRANSFORMATION RECORD", proposal.title, record.id);
    inspector.append(element("p", "inspector-description", proposal.goal));
    inspector.append(factList([
      [language() === "hu" ? "Előállító agent" : "Producing agent", local(producer?.agent.name) || "—"],
      [language() === "hu" ? "Előállító node" : "Producing node", record.producer || "—"],
      [language() === "hu" ? "Modell" : "Model", producer?.calls.at(-1)?.model || producer?.contract.model || "—"],
      [language() === "hu" ? "Bizonyítékállapot" : "Evidence status", proposal.evidence_status],
      [language() === "hu" ? "Hivatkozott megállapítás" : "Cited findings", String(proposal.finding_refs.length)],
    ]));
    if (producer) {
      const producerButton = element("button", "inspector-jump", language() === "hu" ? "Mutasd az előállító LLM-hívást és promptot →" : "Show producing LLM call and prompt →");
      producerButton.type = "button";
      producerButton.addEventListener("click", () => selectExecution(producer.id));
      inspector.append(producerButton);
    }
    const findings = element("ul", "inspector-list inspector-records");
    proposal.finding_refs.forEach((id) => {
      const finding = recordById.get(id);
      const item = element("li");
      item.append(element("b", "", `${id} · ${finding?.producer || "—"}`));
      item.append(element("span", "", finding?.preview || ""));
      findings.append(item);
    });
    appendSection(language() === "hu" ? "Mely kutatási eredményekből?" : "Which research findings feed it?", findings);
    const mechanisms = element("ol", "inspector-list inspector-records");
    proposal.mechanisms.forEach((value) => mechanisms.append(element("li", "", value)));
    appendSection(language() === "hu" ? "Levezetett mechanizmusok" : "Derived mechanisms", mechanisms);
  }

  function renderExecutionInspector(run, node) {
    const inspectorKinds = {
      llm: { en: "LLM PROCESS", hu: "LLM-FOLYAMAT" },
      human_gate: { en: "HUMAN GATE", hu: "EMBERI KAPU" },
      root: { en: "ADMITTED RUN ROOT", hu: "JÓVÁHAGYOTT FUTÁSI GYÖKÉR" },
      deterministic: { en: "DETERMINISTIC STEP", hu: "DETERMINISZTIKUS LÉPÉS" },
    };
    inspectorHeader(local(inspectorKinds[node.kind] || inspectorKinds.deterministic), local(node.title), node.id);
    const status = node.failures ? (language() === "hu" ? "sikertelen" : "failed") : node.disposition === "cache_hit" ? (language() === "hu" ? "újrafelhasznált" : "reused") : (language() === "hu" ? "végrehajtott" : "executed");
    const call = node.calls.at(-1);
    inspector.append(factList([
      [language() === "hu" ? "Állapot" : "Status", status],
      [language() === "hu" ? "Agent" : "Agent", local(node.agent.name)],
      [language() === "hu" ? "Szerep" : "Role", call?.role || node.contract.role || "local"],
      [language() === "hu" ? "Szolgáltató / modell" : "Provider / model", `${call?.provider || node.contract.provider || "local"} / ${call?.model || node.contract.model || "deterministic"}`],
      [language() === "hu" ? "Időtartam" : "Duration", formatDuration(node.duration_seconds)],
      [language() === "hu" ? "Bemenet" : "Inputs", String(node.input_count)],
      [language() === "hu" ? "Kimenet" : "Outputs", String(node.output_count)],
      [language() === "hu" ? "Rögzített LLM-hívás" : "Recorded LLM calls", String(node.calls.length)],
      ["RunPlan hash", node.contract.run_plan_hash ? `${node.contract.run_plan_hash.slice(0, 16)}…` : "—"],
      [language() === "hu" ? "Hash-elt próbálkozás" : "Hashed attempts", String(node.contract.attempts?.length || 0)],
    ]));
    inspector.append(element("p", "inspector-description", `${node.agent.discipline} · ${node.agent.definition_source}`));

    if (node.agent.questions.length) {
      const contract = element("ul", "inspector-list");
      node.agent.questions.forEach((question) => contract.append(element("li", "", question)));
      appendSection(language() === "hu" ? "Az agent kérdései" : "Agent questions", contract);
    }
    if (node.calls.length) {
      const calls = element("ul", "inspector-list inspector-records");
      node.calls.forEach((entry, index) => {
        const item = element("li");
        item.append(element("b", "", `${index + 1}. ${entry.task} · ${entry.model}`));
        const searches = entry.web_searches != null ? ` · ${entry.web_searches} web search` : "";
        item.append(element("span", "", `${entry.input_tokens || 0} → ${entry.output_tokens || 0} token · ${formatDuration((entry.ms || 0) / 1000)}${searches}`));
        calls.append(item);
      });
      appendSection(language() === "hu" ? "Tényleges modellhívások" : "Actual model calls", calls);
    }
    if (node.contract.attempts?.length) {
      const attempts = element("ul", "inspector-list inspector-records");
      node.contract.attempts.forEach((attempt) => {
        const item = element("li");
        item.append(element("b", "", attempt.stage));
        item.append(element("span", "", `prompt ${attempt.prompt_hash.slice(0, 16)}… · response ${attempt.response_hash.slice(0, 16)}… · ${attempt.status}`));
        attempts.append(item);
      });
      appendSection(language() === "hu" ? "Változtathatatlan prompt–válasz párok" : "Immutable prompt–response pairs", attempts);
    }
    const inputGroups = Object.keys(node.inputs).length ? node.inputs : {
      [language() === "hu" ? "problem_brief + agent-leírás (konfigurációs bemenet)" : "problem brief + agent definition (configuration input)"]: [],
    };
    appendSection(language() === "hu" ? "Pontos bemenetek" : "Exact inputs", collapsibleRecordGroups(run, inputGroups));
    appendSection(language() === "hu" ? "A modellnek elküldött prompt" : "Prompt sent to the model", promptStack(node.prompts));
    appendSection(language() === "hu" ? "Létrehozott adatbázis-rekordok" : "Database records produced", collapsibleRecordGroups(run, {outputs: node.outputs}));
  }

  function renderInspector(run, model) {
    if (state.view === "execution") {
      normalizeExecutionSelection(run);
      if (state.selection.execution === "context" || state.selection.execution === "frames") {
        renderContextInspector(run, state.selection.execution);
        return;
      }
      if (state.selection.execution.startsWith("record:")) {
        const hash = state.selection.execution.slice("record:".length);
        const record = executionRecordMap(run).get(hash);
        if (record?.proposal) {
          renderProposalInspector(run, record);
          return;
        }
      }
      const selectedNode = run.execution.nodes.find((node) => node.id === state.selection.execution) || run.execution.nodes[0];
      state.selection.execution = selectedNode.id;
      renderExecutionInspector(run, selectedNode);
      return;
    }
    let selected = model.nodes.find((node) => node.id === state.selection[state.view]);
    if (!selected) {
      selected = model.nodes.find((node) => node.id === (state.view === "execution" ? "transformations" : "transformation_proposal")) || model.nodes[0];
      state.selection[state.view] = selected.id;
    }
    renderSchemaInspector(run, selected, state.view === "database");
  }

  function renderHeading(run, model) {
    graphKicker.textContent = local(copy[state.view].kicker);
    graphTitle.textContent = local(copy[state.view].title);
    if (state.view === "execution") {
      const researchCount = run.execution.nodes.filter((node) => node.id.startsWith("research_")).length;
      const proposalCount = run.execution.proposals.length;
      graphSummary.textContent = language() === "hu" ? `${run.execution.nodes.length} tényleges node. A ${researchCount} kutatóág és a ${proposalCount} létrehozott átalakítás külön-külön látszik; kattintásra megnyílik az agent, a prompt és a pontos I/O.` : `${run.execution.nodes.length} actual nodes. All ${researchCount} research branches and ${proposalCount} resulting transformations are shown separately; select one to inspect the agent, prompt, and exact I/O.`;
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
    if (state.view === "execution") renderExecutionFlow(run);
    else {
      graphRoot.classList.remove("is-flow");
      renderGraph(model);
    }
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
