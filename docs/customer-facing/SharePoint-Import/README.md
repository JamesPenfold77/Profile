# SharePoint Import — Customer-Facing Doc

This folder contains the generator script for the customer-facing document **"Importing Files from SharePoint into Profile"**, which outlines three practical approaches for a Profile macro to retrieve files from a Microsoft 365 SharePoint library and makes a recommendation.

## Files

| File | Description |
|------|-------------|
| `generate_sharepoint_import_doc.py` | Python script that injects the document body into an unpacked copy of the Intrahealth corporate template |
| `README.md` | This file |

## Pattern

This generator follows the `customer-facing-docs` skill (`skills/customer-facing-docs/SKILL.md`) rather than the `docx-js`-from-scratch approach used by `docs/integration-design/ACC45/generate_acc45_checklist.js`. The reason: customer-facing deliverables must match the Intrahealth corporate template exactly (letterhead, logo, fonts, heading colours, `PlainTable11` table style, footer binding). Rebuilding the template in `docx-js` always drifts visually, so the skill mandates unpacking the real template and splicing content into its own styles.

The split is:

- **Unpack and pack** are delegated to the `docx` skill's helper scripts (`/mnt/skills/public/docx/scripts/office/unpack.py` and `pack.py`). These preserve the template's logo, header, footer, section properties, numbering, and theme byte-for-byte.
- **Body splice** is what this script does — it rewrites `unpacked/word/document.xml` between `<w:body>` and the final `<w:sectPr>`, and updates `dc:title` in `unpacked/docProps/core.xml` so the footer's structured document tag picks up the new title.

## Usage

### Prerequisites

- Python 3
- The Intrahealth corporate template. This is **not** stored in the repo; obtain the current version and save it as `Intrahealth_Document_Template.docx` in this folder (or adjust the paths below).
- Access to the `docx` skill's helper scripts at `/mnt/skills/public/docx/scripts/office/` (available in the Claude skills environment; equivalents can be used elsewhere).

### Generate the document

Run from inside this folder:

```bash
# 1. Unpack the template into ./unpacked/
python3 /mnt/skills/public/docx/scripts/office/unpack.py \
    Intrahealth_Document_Template.docx unpacked/

# 2. Splice new body content and set dc:title
python3 generate_sharepoint_import_doc.py

# 3. Pack back into a .docx
python3 /mnt/skills/public/docx/scripts/office/pack.py \
    unpacked/ "Importing Files from SharePoint into Profile.docx" \
    --original Intrahealth_Document_Template.docx
```

The generator script expects to run from a working directory that contains the `unpacked/` folder produced by step 1.

### Optional: visual check

```bash
python3 /mnt/skills/public/docx/scripts/office/soffice.py --headless \
    --convert-to pdf "Importing Files from SharePoint into Profile.docx"
pdftoppm -jpeg -r 100 "Importing Files from SharePoint into Profile.pdf" page
# Inspect page-1.jpg, page-2.jpg, page-3.jpg
```

## Document Structure

The generated document is 3 pages and contains:

1. **Title + Subtitle** — using the template's `Title` and `Sub-Title` styles (note: the template defines both `Sub-Title` custom and `Subtitle` built-in — this doc uses the custom `Sub-Title`).
2. **Intro paragraph**
3. **At a glance** (Heading 1) — summary of the three options as bullets
4. **Option 1: Mapped network location** (Heading 1) with How it works / Considerations (Heading 2) subsections
5. **Option 2: OneDrive sync** (Heading 1) with same subsections
6. **Option 3: Download helper** (Heading 1) with same subsections
7. **Comparison** (Heading 1) — `PlainTable11` with 4 columns
8. **Recommendation** (Heading 1)
9. **Next steps** (Heading 1)

## Content Style Notes

Per the `customer-facing-docs` skill, the body deliberately avoids internal engineering vocabulary:

- No mention of `MSXML2.XMLHTTP`, `CreateObject`, `Shell`, `WebDAV`, OAuth / MSAL / Graph / PnP, or any specific COM or PowerShell cmdlet.
- Options are framed functionally ("mapped network location", "OneDrive sync", "download helper") rather than by their underlying technology.
- Language uses Australian / New Zealand English spelling (behaviour, organisation, authorised).
- Recommendation is included with the caveat that the other options remain viable (per user preference when the doc was commissioned).

## Scope

This document assumes:

- **Deployment:** generic (any Profile deployment — on-prem, Deployed Offline, or hosted).
- **SharePoint:** Microsoft 365 (SharePoint Online).
- **Use:** interactive (user present, triggers the import).

If any of these change, the content in the script should be revised before regenerating.

## Template Version

Last regenerated against `Intrahealth_Document_Template.docx` as of April 2026. If the template is updated, re-run `grep -E 'w:styleId=' unpacked/word/styles.xml` and verify the style IDs used here (`Title`, `Sub-Title`, `Heading1`, `Heading2`, `BodyBullet`, `PlainTable11`) still exist. The skill warns explicitly against assuming last session's style names still apply.
