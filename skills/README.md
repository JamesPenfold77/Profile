# Skills

Reusable knowledge documents capturing hard-won lessons from Profile EMR development work. Each skill lives in its own directory and starts with a `SKILL.md` containing YAML front-matter (`name:` and `description:`) so tooling can index them.

## Available skills

### CDO Forms

- **[jfa-format](jfa-format/SKILL.md)** — the JFA file format used by Profile's CDO Forms system. Record types (HEAD/LNVR/OBSV), field positions per record, the 4 OBSV class codes, jaffa value encoding, the embedded DFM payload, the control palette. Source-level Pascal references plus empirically-validated facts from real imports.

- **[pdf-to-jfa-generator](pdf-to-jfa-generator/SKILL.md)** — the Python pipeline at `generators/pdf_to_jfa/` that produces JFA files from PDFs (or from scratch). Architecture, the calibration loop, recipes for adding new forms, common failure modes. Pairs with the **jfa-format** skill.

### Profile development

- **[vb-profile-macros](vb-profile-macros/SKILL.md)** — Profile EMR VBScript / VB macro development. The `IHProfBL` COM type library, `ISProfile` global object, common patterns (provider group resolution, slot-availability detection, modal progress with cancel).

- **[profile-integration-design](profile-integration-design/SKILL.md)** — Integration design patterns for Profile (server-side vs. macro-based options, JIRA IDEA structure, etc.)

### Documentation

- **[customer-facing-docs](customer-facing-docs/SKILL.md)** — Writing customer-facing documentation for Profile features.

## Conventions

Each skill is a directory at `skills/<skill-name>/` containing at minimum a `SKILL.md`. The SKILL.md starts with YAML front matter (`name:` and `description:`) so tooling can index them.

The `description:` field should make it obvious *when* to use the skill. It's the part LLMs and humans see when deciding whether to read further; spend a sentence or two on the trigger conditions.

Cross-references between skills use bold-italic links to the related skill's name (e.g. "see the **jfa-format** skill"). This makes them easy to discover when reading a skill in isolation.
