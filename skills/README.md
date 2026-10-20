# Skills

Reusable knowledge documents capturing hard-won lessons from Profile EMR development work. Each skill lives in its own directory and starts with a `SKILL.md` containing YAML front-matter (`name:` and `description:`) so tooling can index them.

## Available skills

### CDO Forms

- **[jfa-format](jfa-format/SKILL.md)** — the JFA file format used by Profile's CDO Forms system. Record types (HEAD/LNVR/OBSV), field positions per record, the 4 OBSV class codes, jaffa value encoding, the embedded DFM payload, the control palette. Also macro exports (TYPT records) and their decode/edit/re-encode workflow. Source-level Pascal references plus empirically-validated facts from real imports. Includes the optional "modern" form style (header bar, section cards, rounded buttons and input frames) and two tools in `jfa-format/tools/`: `jfa_preview.py` (draws a PNG preview of a form) and `jfa_layout_check.py` (offline layout and control-reference check).

- **[ih-edit-jfa-forms](ih-edit-jfa-forms/SKILL.md)** — step-by-step workflow for editing an existing `.jfa` CDO form: the `\0d\0a` vs `^^^` escaping traps, splicing and rewrapping `Macros.Strings` items safely, verifying before writing back, version-label bumps, and patterns for macro-driven forms (never-saved call-log forms, Cancel/X close-query prompts, moving a form to another folder). Pairs with the **jfa-format** skill. Also kept as a Claude Code project skill in the Intrahealth Profile source repo at `.claude/skills/ih-edit-jfa-forms/` — keep the two copies in step.

- **[pdf-to-jfa-generator](pdf-to-jfa-generator/SKILL.md)** — the Python pipeline at `generators/pdf_to_jfa/` that produces JFA files from PDFs (or from scratch). Architecture, the calibration loop, recipes for adding new forms, common failure modes. Pairs with the **jfa-format** skill.

### Profile development

- **[vb-profile-macros](vb-profile-macros/SKILL.md)** — Profile EMR VBScript / VB macro development. The `IHProfBL` COM type library, `ISProfile` global object, common patterns (provider group resolution, slot-availability detection, modal progress with cancel), sharing code via `ExecuteGlobal`, offline testing with `cscript`, and building/validating XML with MSXML.

- **[ihq-stored-query-format](ihq-stored-query-format/SKILL.md)** — Reading Profile stored-query (`.ihq`) exports: the Delphi binary layout, the Select / Conditions / Common records, `?ask?` run-time parameters, a checklist for reviewing queries, and a working decoder (`ihq_decode.py`).

- **[dex-reporting](dex-reporting/SKILL.md)** — Generating the DSS Data Exchange (DEX) upload XML from Profile (DEXREPORT / DEXLOADORG macros) and diagnosing DEX rejections: XSD sequence order, OrganisationData.xml requirement codes, common errors and fixes, PHI-safe anonymised output.

- **[profile-integration-design](profile-integration-design/SKILL.md)** — Integration design patterns for Profile (server-side vs. macro-based options, JIRA IDEA structure, etc.)

### Documentation

- **[customer-facing-docs](customer-facing-docs/SKILL.md)** — Writing customer-facing documentation for Profile features.

## Conventions

Each skill is a directory at `skills/<skill-name>/` containing at minimum a `SKILL.md`. The SKILL.md starts with YAML front matter (`name:` and `description:`) so tooling can index them.

The `description:` field should make it obvious *when* to use the skill. It's the part LLMs and humans see when deciding whether to read further; spend a sentence or two on the trigger conditions.

Cross-references between skills use bold-italic links to the related skill's name (e.g. "see the **jfa-format** skill"). This makes them easy to discover when reading a skill in isolation.
