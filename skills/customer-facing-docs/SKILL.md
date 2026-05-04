---
name: customer-facing-docs
description: "Use this skill whenever a customer-facing Word document needs to be generated against the Intrahealth corporate template. Triggers include: 'customer-facing doc', 'doc I can share with customer', 'using the Intrahealth template', any .docx output intended for a customer, partner, or external audience. The skill defines the canonical approach — inject content into the template's own styles rather than applying custom styling via docx-js — and requires the template file to be available either from the JamesPenfold77/Profile repo (canonical) or attached to the conversation."
---

# Customer-Facing Documents – Intrahealth Template Skill

## Purpose

This skill produces customer-facing `.docx` deliverables (overviews, functional summaries, integration briefs, proposals) that use the **Intrahealth corporate template** directly. The template carries the letterhead, logo, fonts, colour palette, heading styles, table styles, and footer binding — so the output looks identical to anything else produced from that template.

The key principle: **never rebuild the branding in code**. Take the actual template file, unpack it, replace the body content while preserving its styles, and repack. Do not try to approximate the template with docx-js style overrides — the result will always drift.

A second, equally important principle: **never invent Profile functional behaviour**. The Profile source is accessible; read it before describing how anything in Profile actually works. See pre-requisite 2 below.

---

## Pre-requisites

1. **The Intrahealth template must be available.** Canonical source is `docs/Intrahealth Document Template.docx` in the JamesPenfold77/Profile repo — fetch it via the GitHub connector at the start of the task. If the connector is unavailable or returns garbled bytes (a known issue with binary content over the MCP wrapper), ask the user to attach the template and stop until they do. Do not fall back to a generic Arial/plain-styled doc — producing something that looks "close to" the template is worse than asking.

2. **For Profile functional behaviour, ground the doc in the Profile source.** Whenever the doc describes how a Profile interface, integration, feature or workflow actually works, read the source before writing. Profile source lives at `intrahealth-source/profile` (GitHub) — connect via the GitHub MCP and start at `docs/Integrations/eMessages/` for any integration topic, then drill into the relevant setup form (`Profile/Client/Interface/UIRSD*.pas`) and the message-type catalogue (`Profile/Common/Business/UBRSDTypes.pas`, `Profile/Common/Business/UBEMessageService.pas`). For integrations that are *not* in the eMessages catalogue (e.g. anything launched as an HTML View, like BPAC eForms), check `Profile/Common/Infrastructure/UStdHTMLViews.pas` and `Profile/Client/Interface/UIHTMLViewsSetup.pas`. Do not write from priors and offer to verify later — verify first, write second.

   The repo also contains internal customer-facing setup PDFs alongside the integration docs which are useful secondary sources. If the user provides a setup guide or other Intrahealth document for the topic, treat that as primary truth; corroborate against the source for anything beyond what it covers.

   If the source has been read and an unverified claim is still needed (e.g. retry intervals, status names, identifiers), explicitly mark it in the draft as needing user confirmation rather than stating it confidently. A document that flags two open questions is honest; a document that confidently invents details a customer architect will design against is a liability.

3. The `docx` skill at `/mnt/skills/public/docx/SKILL.md` must be read first — it documents `unpack.py`, `pack.py`, and `validate.py` which this skill relies on.

---

## Workflow

### 1. Read the docx skill
Always start with `view /mnt/skills/public/docx/SKILL.md` — confirms the scripts path and unpack/pack behaviour.

### 2. Unpack the template
```bash
cp /mnt/user-data/uploads/<template>.docx /home/claude/work/template.docx
python3 /mnt/skills/public/docx/scripts/office/unpack.py template.docx unpacked/
```

### 3. Discover the template's style IDs
Always inspect the template before writing content — don't assume standard names. Run:
```bash
grep -E 'w:styleId=' unpacked/word/styles.xml
```
Map the styles you'll need:
- Title style (often `Title`)
- Subtitle style (Intrahealth template uses `Sub-Title` with a hyphen — **not** the built-in `Subtitle`)
- Heading styles (`Heading1`, `Heading2`, `Heading3`)
- Body paragraph style (Intrahealth uses default `Normal`; custom `Body` style exists but isn't required)
- Bullet style (Intrahealth: `BodyBullet`, which references `numId=1` already defined in `numbering.xml`)
- Table style (Intrahealth: `PlainTable11` — navy header row, light banding, bold first column)

### 4. Inspect the footer binding
Check `unpacked/word/footer1.xml`. The Intrahealth template's footer pulls the document title from `coreProperties/dc:title` via a structured document tag (`<w:sdt>`). To make the footer show the right title:
```bash
sed -i 's|<dc:title>Document Title</dc:title>|<dc:title>Your Document Title</dc:title>|' unpacked/docProps/core.xml
```

### 5. Rewrite the document body
Work on `unpacked/word/document.xml`. The body has this structure:
```
<w:body>
  <w:bookmarkStart .../>       ← keep or discard; benign either way
  <w:p pStyle=Title>...</w:p>  ← first two paragraphs (Title + Sub-Title)
  <w:p pStyle=Sub-Title>...</w:p>
  ... existing lorem ipsum content ...
  <w:sectPr>...</w:sectPr>     ← MUST be preserved — contains page size, margins,
                                 header/footer refs, column settings
</w:body>
```

The safe rewrite pattern is to keep `<w:body>` open, keep the final `<w:sectPr>` block, and replace everything between. Use a Python script that anchors on `<w:body>` and `<w:sectPr` and splices new content between them.

### 6. Build paragraphs using the template's styles
Write paragraph XML directly — don't use docx-js. Minimum viable paragraph:
```xml
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Heading text</w:t></w:r></w:p>
```

Body text omits the `<w:pStyle>` to inherit `Normal`. Bullets use `<w:pStyle w:val="BodyBullet"/>`. Always XML-escape text (`&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`) and add `xml:space="preserve"` on `<w:t>` elements with leading/trailing whitespace.

### 7. Tables — use the template's table style
Do **not** hand-roll borders, shading, or header colours. Reference `PlainTable11` and let the template's style do the work:
```xml
<w:tbl>
  <w:tblPr>
    <w:tblStyle w:val="PlainTable11"/>
    <w:tblW w:w="0" w:type="auto"/>
    <w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="0"
               w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>
  </w:tblPr>
  <w:tblGrid><w:gridCol w:w="2200"/>...</w:tblGrid>
  <w:tr>
    <w:trPr>
      <!-- cnfStyle marks this as the first (header) row -->
      <w:cnfStyle w:val="100000000000" w:firstRow="1" .../>
    </w:trPr>
    <w:tc><w:tcPr><w:tcW w:w="2200" w:type="dxa"/></w:tcPr>
      <w:p><w:r><w:t>Header</w:t></w:r></w:p>
    </w:tc>
    ...
  </w:tr>
  ...
</w:tbl>
```

**Critical `tblLook` flags:**
- `w:firstRow="1"` — style the header row (navy background, white bold text)
- `w:lastRow="0"` — **do not** style the last row (otherwise `PlainTable11` will bold the body text in your last data row)
- `w:firstColumn="0"` — set to `0` if you don't want the first column auto-bolded across all rows; set to `1` if you do (useful for key/value tables where the key should stand out)
- `w:noVBand="1"` — disable vertical banding

Only the first row needs the `<w:cnfStyle>` marker inside `<w:trPr>` — that's what tells the table style this is the header row.

### 8. Pack and validate
```bash
python3 /mnt/skills/public/docx/scripts/office/pack.py unpacked/ Output.docx --original template.docx
```
`pack.py` validates automatically. If it reports `All validations PASSED`, the file is structurally sound.

### 9. Visual check
Rendering differences between LibreOffice and Word are rare, but table style flags in particular can surprise you. Convert to PDF and eyeball the first 2 pages:
```bash
python3 /mnt/skills/public/docx/scripts/office/soffice.py --headless --convert-to pdf Output.docx
pdftoppm -jpeg -r 100 Output.pdf page
```
Then `view page-1.jpg` and `view page-2.jpg`. Confirm:
- The Intrahealth logo is in the top-left of page 1
- The footer shows the document title on the left and page number on the right
- Headings are the Intrahealth blue
- Tables have the navy header row with white bold text
- Body text is regular weight (not bolded by an unintended `lastRow` or `firstColumn` flag)

### 10. Deliver
```bash
cp Output.docx /mnt/user-data/outputs/
```
Then call `present_files` with the output path.

---

## Content Style Guidelines

Customer-facing content has different rules from internal engineering documentation. Strip these before generating:

- **No file paths, unit names, class names, or COM interfaces.** A customer does not need to know about `UBClickSendServiceClient_RS.pas`.
- **No SQL queries, config file snippets, or log paths.** Operational detail belongs in internal runbooks.
- **No internal product terminology the customer wouldn't recognise.** "eMessage service" is fine if the customer-facing UI uses that term; "RSD message type" is not.
- **Frame behaviour functionally.** Instead of "IHServer calls `StartSendSms` which returns a ClickSend ID stored against the message record", write "When Profile hands a message to the gateway, the gateway returns a reference that Profile uses to match replies and delivery updates."
- **Keep statuses and SLAs (retry intervals, expiry windows, status values) — these are customer-relevant.**
- **Use Australian / NZ English spelling** (behaviour, organisation, authorised) — Intrahealth customer base is AU/NZ.
- **Lead with the "at a glance" summary.** Customers often read the first paragraph only.

---

## Structural Defaults

Every customer-facing doc should have, at minimum:

1. **Title** (template `Title` style) — the subject, e.g. "ClickSend SMS Integration"
2. **Subtitle** (template `Sub-Title` style) — the framing, e.g. "Profile EMR — functional overview"
3. **Intro paragraph** — one short paragraph that answers "what is this and why does the reader care"
4. **One Heading 1 per major topic** — usually 3–5 for a functional overview
5. **Heading 2 for sub-topics within each Heading 1**
6. **Tables for structured comparisons** (statuses, retry matrices, environment endpoints) — always using `PlainTable11`
7. **No coloured callout boxes, no custom shading, no "At a glance" cards built from tables.** The template's own styles are sufficient; bespoke styling always looks out of place once inside the corporate template.

---

## Failure Modes to Avoid

- **Writing functional behaviour from priors instead of source.** Plausible-sounding but invented status names, retry intervals, message formats, transport mechanisms, or identifiers will read as authoritative to a customer architect and may be designed against. If the integration is in Profile's eMessages catalogue, the answer is in `UBRSDTypes.pas` and the relevant setup form — read them first. If the integration is *not* in the eMessages catalogue (e.g. BPAC eForms, which uses HTML Views), do not assume it doesn't exist; check `UStdHTMLViews.pas`, `UIHTMLViewsSetup.pas`, and any setup guide the user provides. When in doubt, mark a claim as needing user confirmation rather than asserting it.
- **Rebuilding the template in docx-js.** Tempting when the template isn't available yet, but the output will never quite match the real template and will be visually inconsistent with other Intrahealth docs. Always fetch from the repo or ask for the template instead.
- **Using `Subtitle` (no hyphen) when the template defines `Sub-Title` (with hyphen).** The built-in `Subtitle` style exists alongside the custom one and will render differently. Verify by grepping `styles.xml`.
- **Forgetting to update `dc:title` in `core.xml`.** The footer will keep saying "Document Title" because it's bound to that field.
- **Setting `w:lastRow="1"` on tables with more than one data row.** `PlainTable11` will bold the final data row, which looks like a typo to the reader.
- **Replacing the entire `<w:body>` contents including `<w:sectPr>`.** The document will lose its page size, margins, header/footer references, and orientation.
- **Producing a "plain styled" fallback when the template isn't available.** Don't. Fetch from the repo or ask the user.

---

## Notes

- Canonical template location: `docs/Intrahealth Document Template.docx` in JamesPenfold77/Profile (note spaces in filename). Fetch via GitHub connector at the start of any task.
- Profile source: `intrahealth-source/profile` on GitHub. Integration documentation lives under `docs/Integrations/`, with eMessages-specific docs at `docs/Integrations/eMessages/`. The eMessages catalogue defines 109 message types — most Profile integrations are one of these. HTML Views (used by BPAC eForms and a small number of other UI-embedded integrations) are a separate mechanism, not part of the eMessages framework.
- Template as of April 2026: uses `Title`, `Sub-Title`, `Heading1/2/3`, `BodyBullet`, `PlainTable11`; footer binds to `dc:title` via structured document tag.
- If the template changes (new styles, new footer binding, new logo), re-discover style IDs via `grep -E 'w:styleId='` before writing content. Don't assume last session's style names still apply.
