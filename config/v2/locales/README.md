# V2 website localization catalogs

The public v2 website is localized from the versioned `en.json` and
`hu.json` message catalogs at build time. The catalogs are the single source
of truth for navigation, interface labels, artifact names, enum values, and
repeated technical terminology.

Canonical semantic policy records use schema version 2.1.0 and store every
declared prose leaf as one exact `{en, hu}` pair (D-58, restoring D-34).
Identifiers, references, enum values, URLs, and provenance metadata remain
language-neutral technical data. These catalogs localize only navigation,
interface labels, artifact names, enum labels, and repeated technical terms;
they do not carry policy-content translations. The website projects policy
prose directly from the canonical record. The Hungarian catalog may also
contain audited `content_replacements` for legacy loanwords at render time.

Rules enforced by `scripts/verify_v2.py`:

- both catalogs conform to `catalog.schema.json`;
- locale versions and flattened message-key sets are identical;
- missing translations fail the build instead of falling back silently;
- visible Hungarian UI text is checked for raw English interface terms;
- explicitly marked English source excerpts (`lang="en"`) are exempt.

Add a message to both catalogs, then use its dotted key through the site
builder's `ui()` or `label()` helpers. Do not add one-off translations to the
HTML templates when a shared concept already exists in this catalog.
