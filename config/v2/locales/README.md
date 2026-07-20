# V2 website localization catalogs

The public v2 website is localized from the versioned `en.json` and
`hu.json` message catalogs at build time. The catalogs are the single source
of truth for navigation, interface labels, artifact names, enum values, and
repeated technical terminology.

The canonical policy records under `v2/` remain English-only. Localization is
a downstream presentation concern: it must never change record identifiers,
dependency hashes, or policy content. Topic prose already available in the
legacy bilingual corpus is projected into the corresponding language view.
The Hungarian catalog may also contain audited `content_replacements` for
legacy loanwords. These replacements affect rendered text only; source
artifacts remain byte-for-byte unchanged.

Rules enforced by `scripts/verify_v2.py`:

- both catalogs conform to `catalog.schema.json`;
- locale versions and flattened message-key sets are identical;
- missing translations fail the build instead of falling back silently;
- visible Hungarian UI text is checked for raw English interface terms;
- explicitly marked English source excerpts (`lang="en"`) are exempt.

Add a message to both catalogs, then use its dotted key through the site
builder's `ui()` or `label()` helpers. Do not add one-off translations to the
HTML templates when a shared concept already exists in this catalog.
