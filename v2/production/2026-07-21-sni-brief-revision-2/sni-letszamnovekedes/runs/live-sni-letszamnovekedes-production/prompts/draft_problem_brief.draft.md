TASK: draft_problem_brief
AGENT: problem_framing_editor
LANG: en


Turn the admitted raw policy question below into a bounded English problem-brief proposal for human review. Do not research or answer the question yet.

RAW QUESTION: More children are being identified as having special educational needs — what should Hungary do?
SUBMISSION CONTEXT: Owner-selected policy question from GitHub issue #14, supplemented by a human research proposal. The proposal asks the research to connect identification trends and causes with service capacity, classroom experience, parental school choice, institutional sorting, and inequality. Its empirical and causal claims are hypotheses to test; its response domains are a research agenda, not approved solutions.
SOURCE POINTERS: https://github.com/halacsy/education-policy-lab/issues/14; topics/sni-letszamnovekedes/research-proposal.hu.md
HUMAN RESEARCH DIRECTIONS: {
  "candidate_response_domains": [
    "specialist workforce and travelling-service capacity",
    "mainstream teacher methods, differentiation, crisis management, and co-teaching",
    "finance, governance, placement, and accountability",
    "school-parent communication and conflict handling",
    "international inclusive models with explicit Hungarian transferability tests"
  ],
  "hypotheses_to_test": [
    "Recorded SEN identification has risen materially and continuously over the past decade.",
    "Specialist shortages and methodological capacity gaps prevent adequate support and overload mainstream teachers.",
    "Classroom experience, learning concerns, and safety concerns contribute to parental flight from integrating schools or classes.",
    "Selective parental mobility contributes to institutional sorting and wider educational inequality."
  ],
  "inquiry_priorities": [
    "Separate biological, environmental, diagnostic, definitional, access, and incentive-related explanations for any measured trend.",
    "Investigate parent and teacher experience without conflating SEN, BTMN, autism, behavioural difficulty, and safety incidents.",
    "Test whether parental flight occurs, who can move, which sectors absorb movers, and how mobility changes school composition.",
    "Connect identification and provision to children's outcomes, classroom functioning, rights, inclusion, and inequality."
  ],
  "source_ref": "topics/sni-letszamnovekedes/research-proposal.hu.md",
  "status": "human_provided_hypotheses_and_priorities"
}

Rules:
- Treat every empirical premise in the raw question as something research must verify, not as an established fact.
- Preserve the submitter's real concern while distinguishing prevalence, measurement, definitions, access, incentives, implementation, and value choices where relevant.
- Define a decision-useful scope and state exclusions inside the scope text.
- Write 3-7 learning goals that the later research and option-space nodes can answer.
- Do not propose interventions, scenarios, preferred outcomes, or expert seats.
- Seed sources are pointers only; never infer their contents.
- Treat human hypotheses as questions to test and response domains as areas to
  examine; do not convert either into facts or approved solutions.
- Preserve the requested links among service capacity, classroom experience,
  parental school choice, institutional sorting, and inequality.
- Framing notes must make the important interpretation choices visible to the human reviewer.
