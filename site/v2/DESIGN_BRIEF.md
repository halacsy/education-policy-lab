# Transformation Observatory — design brief

## Subject

An education-system transformation atlas: a public learning space where a
curious reader can start with a concrete question, understand possible change
directions, see how different professional perspectives assess them, and
recognise the value dilemmas evidence cannot settle.

## Audience

Interested people who are only beginning to learn how the Hungarian education
system works come first. Policy practitioners, researchers, and civil actors
are secondary audiences served by progressively deeper layers. The first
screen must use plain language and require no policy vocabulary. The interface
is bilingual, with Hungarian as the default view and English as an exact
downstream projection where source localization exists.

## One job

Move from a public problem to a concrete transformation direction, then see
its mechanism, implementation path, scientific scrutiny, unresolved dilemmas,
and research agenda without reconstructing a debate between named speakers.

## Visual direction

"Systems workshop on tracing paper": warm mineral paper, disciplined cobalt
construction lines, vermilion dilemma markers, and chartreuse readiness
signals. The signature motif is the **change spine**, a numbered rail that
connects system problem → lever → action → effects → decision. Square sheets,
registration marks, and monospaced audit labels make provenance visible
without turning the site into a developer console.

## Content hierarchy

1. Public question and transformation portfolio
2. Change spine and proposal sheets
3. Scientific lens matrix
4. Human decision dilemmas
5. Research agenda and audit trail

## Interaction

- HU/EN switch with persisted preference
- Lens filters on topic pages
- Anchor navigation along the change spine
- Full keyboard focus, reduced-motion support, and a single-column mobile rail

## Localization contract

- `config/v2/locales/en.json` and `hu.json` are the versioned source of truth
  for navigation, interface copy, artifact names, enum values, and recurring
  terminology.
- Hungarian is the default public view. English source excerpts may appear in
  it only behind an explicitly Hungarian disclosure label and `lang="en"`.
- A missing key or a raw English interface term in the Hungarian view fails
  verification; there is no silent language fallback.
- Audited Hungarian `content_replacements` can repair legacy loanwords at
  render time without changing canonical records or their hashes.

## Honesty boundary

The public dossiers are generated only from the accepted, fresh, sourced v2
production runs. They may be used for learning and public scrutiny, but their
current `ready_with_conditions` status and pending human policy gate must stay
visible. Migration fixtures, experiments, and the retired v1/v2 comparison
remain internal audit material rather than public navigation.
