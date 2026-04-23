#!/usr/bin/env python3
"""Generate the customer-facing "Importing Files from SharePoint into Profile" doc.

Follows the `customer-facing-docs` skill pattern: unpacks the Intrahealth
corporate Word template, splices new body content into the template's own
styles (Title, Sub-Title, Heading1/2, BodyBullet, PlainTable11), updates
`dc:title` in core.xml so the footer binding picks up the document title,
and repacks to a valid `.docx`.

Usage:
    # Prerequisites: the Intrahealth template unpacked under ./unpacked/,
    # which you get by running:
    #   python3 /mnt/skills/public/docx/scripts/office/unpack.py \
    #       Intrahealth_Document_Template.docx unpacked/
    #
    # Then:
    python3 generate_sharepoint_import_doc.py
    #
    # Then pack back up with:
    #   python3 /mnt/skills/public/docx/scripts/office/pack.py \
    #       unpacked/ "Importing Files from SharePoint into Profile.docx" \
    #       --original Intrahealth_Document_Template.docx

This script only performs the body-splice step. Unpack and pack are delegated
to the `docx` skill's helper scripts so that template fidelity (logo, footer
binding, header, section properties, theme) is preserved byte-for-byte.
"""
import re
from pathlib import Path

DOC_PATH = Path("unpacked/word/document.xml")
CORE_PATH = Path("unpacked/docProps/core.xml")

DOC_TITLE = "Importing Files from SharePoint into Profile"
DOC_SUBTITLE = "Profile EMR \u2014 options for retrieving content from Microsoft 365 SharePoint"

# ---------------------------------------------------------------------------
# Helpers for building OOXML paragraph/table fragments
# ---------------------------------------------------------------------------


def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def para(style: str | None, text: str) -> str:
    """Paragraph with optional pStyle. Body text passes style=None (inherits Normal)."""
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return (
        f'<w:p>{ppr}'
        f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
        f'</w:p>'
    )


def bullet(text: str) -> str:
    # BodyBullet has numId=1 baked into the style definition, no numPr needed.
    return para("BodyBullet", text)


def heading(level: int, text: str) -> str:
    return para(f"Heading{level}", text)


def title(text: str) -> str:
    return para("Title", text)


def subtitle(text: str) -> str:
    # This template's custom styleId is "Sub-Title" (with hyphen).
    # The built-in "Subtitle" (no hyphen) also exists but looks different.
    # Re-check with `grep -E 'w:styleId=' unpacked/word/styles.xml` if the
    # template is updated, per the customer-facing-docs skill.
    return para("Sub-Title", text)


def table(headers: list[str], rows: list[list[str]], col_widths: list[int]) -> str:
    """Build a PlainTable11 table.

    col_widths: DXA, sum should equal table width.
    The first row is marked with cnfStyle so PlainTable11's firstRow rule
    (bold header) applies. tblLook has lastRow=0 and firstColumn=0 so the
    last data row and first column are not auto-bolded.
    """
    total = sum(col_widths)
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in col_widths)

    def cell(width: int, text: str) -> str:
        return (
            f'<w:tc>'
            f'<w:tcPr><w:tcW w:w="{width}" w:type="dxa"/></w:tcPr>'
            f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
            f'</w:tc>'
        )

    header_cells = "".join(cell(w, h) for w, h in zip(col_widths, headers))
    header_row = (
        f'<w:tr>'
        f'<w:trPr>'
        f'<w:cnfStyle w:val="100000000000" w:firstRow="1" w:lastRow="0" '
        f'w:firstColumn="0" w:lastColumn="0" w:oddVBand="0" w:evenVBand="0" '
        f'w:oddHBand="0" w:evenHBand="0" w:firstRowFirstColumn="0" '
        f'w:firstRowLastColumn="0" w:lastRowFirstColumn="0" w:lastRowLastColumn="0"/>'
        f'</w:trPr>'
        f'{header_cells}'
        f'</w:tr>'
    )

    body_rows = []
    for row in rows:
        cells = "".join(cell(w, t) for w, t in zip(col_widths, row))
        body_rows.append(f"<w:tr>{cells}</w:tr>")

    return (
        f'<w:tbl>'
        f'<w:tblPr>'
        f'<w:tblStyle w:val="PlainTable11"/>'
        f'<w:tblW w:w="{total}" w:type="dxa"/>'
        f'<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" '
        f'w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
        f'</w:tblPr>'
        f'<w:tblGrid>{grid}</w:tblGrid>'
        f'{header_row}'
        f'{"".join(body_rows)}'
        f'</w:tbl>'
    )


# ---------------------------------------------------------------------------
# Document content
# ---------------------------------------------------------------------------


def build_body_parts() -> list[str]:
    parts: list[str] = []

    # Title block
    parts.append(title(DOC_TITLE))
    parts.append(subtitle(DOC_SUBTITLE))

    # Intro
    parts.append(para(None,
        "Profile's macro environment can retrieve files from a Microsoft 365 SharePoint library "
        "and import them into Profile. This document outlines the three practical approaches, "
        "compares them, and makes a recommendation."))

    # At a glance
    parts.append(heading(1, "At a glance"))
    parts.append(para(None,
        "Three approaches are available. Each handles SharePoint authentication differently, "
        "which is the main factor that will drive the right choice for your site."))
    parts.append(bullet(
        "Mapped network location \u2014 treat the SharePoint library as a drive letter or network path. "
        "Profile reads the file directly with no additional software."))
    parts.append(bullet(
        "OneDrive sync \u2014 let the Microsoft sync client mirror the SharePoint library to a local folder. "
        "Profile reads the local copy."))
    parts.append(bullet(
        "Download helper \u2014 a small companion utility signs in to SharePoint, downloads the file to a "
        "known local location, and Profile imports from there."))

    # Option 1
    parts.append(heading(1, "Option 1: Mapped network location"))
    parts.append(para(None,
        "The SharePoint library is exposed to the workstation as a network path, and the Profile macro "
        "reads the file in the same way it would read any other file on a network share."))
    parts.append(heading(2, "How it works"))
    parts.append(para(None,
        "Your IT team maps the SharePoint document library using standard Windows integration. "
        "Once mapped, the library appears as a drive letter or network path. When a user runs "
        "the macro, Profile opens the file using that path and imports the contents."))
    parts.append(heading(2, "Considerations"))
    parts.append(bullet("Simplest option to implement from the Profile side \u2014 no additional software needed on the workstation."))
    parts.append(bullet("Sign-in is handled transparently by Windows, provided the user is signed in to Microsoft 365."))
    parts.append(bullet("Behaviour can vary between workstations depending on network conditions and Windows version."))
    parts.append(bullet("Not suitable for unattended use (scheduled jobs, service accounts) \u2014 the mapping relies on an interactive user session."))

    # Option 2
    parts.append(heading(1, "Option 2: OneDrive sync"))
    parts.append(para(None,
        "The SharePoint library is synced to a local folder on the workstation using the Microsoft "
        "sync client. Profile reads the file from that local folder as if it were any other local file."))
    parts.append(heading(2, "How it works"))
    parts.append(para(None,
        "Your IT team configures the SharePoint library to sync to a standard local folder. "
        "Microsoft's sync client keeps the folder up to date in the background. When a user runs "
        "the macro, Profile opens the file from the local folder and imports the contents."))
    parts.append(heading(2, "Considerations"))
    parts.append(bullet("Most reliable option for everyday use \u2014 once set up, the file is always available locally."))
    parts.append(bullet("Works offline: if SharePoint or the internet is briefly unavailable, the last synced copy is still there."))
    parts.append(bullet("Sign-in is handled by the sync client using the user's Microsoft 365 credentials."))
    parts.append(bullet("Requires the sync client to be installed and configured on each workstation that will run the import."))
    parts.append(bullet("There can be a short delay between a new file appearing in SharePoint and the sync client making it available locally."))

    # Option 3
    parts.append(heading(1, "Option 3: Download helper"))
    parts.append(para(None,
        "A small companion utility runs alongside the Profile macro. It signs in to SharePoint, "
        "downloads the required file to a known local location, and signals when it is ready. "
        "Profile then reads the downloaded file and performs the import."))
    parts.append(heading(2, "How it works"))
    parts.append(para(None,
        "When the user runs the macro, Profile launches the helper utility. The helper connects to "
        "SharePoint using a Microsoft-supported sign-in flow, downloads the file, and returns control "
        "to Profile. Profile then opens the downloaded file and imports the contents."))
    parts.append(heading(2, "Considerations"))
    parts.append(bullet("Most flexible option \u2014 can target specific files, specific library paths, or apply rules about which file to retrieve."))
    parts.append(bullet("Handles modern authentication cleanly, including multi-factor authentication."))
    parts.append(bullet("The only option suitable for fully unattended use (scheduled imports, service accounts), though this document assumes interactive use."))
    parts.append(bullet("Requires the helper utility to be installed and maintained as a separate piece of software."))
    parts.append(bullet("Sign-in may require a one-time consent step from a Microsoft 365 administrator."))

    # Comparison
    parts.append(heading(1, "Comparison"))
    parts.append(para(None,
        "The table below summarises the trade-offs. Usable content width for the comparison is allocated "
        "across four columns."))

    # US Letter with 1080 DXA side margins: content width = 12240 - 2160 = 10080
    # Columns: 2400 + 1800 + 2280 + 3600 = 10080
    parts.append(table(
        headers=["Approach", "Setup effort", "Reliability", "Best for"],
        rows=[
            ["Mapped network location", "Low", "Depends on network conditions", "Small sites, single workstation, occasional use"],
            ["OneDrive sync", "Low to medium", "High \u2014 file is always locally present", "Everyday imports on workstations that are already signed in to Microsoft 365"],
            ["Download helper", "Medium", "High \u2014 controlled download on demand", "Sites where the file set changes often, or where auditability of each retrieval matters"],
        ],
        col_widths=[2400, 1800, 2280, 3600],
    ))

    # Recommendation
    parts.append(heading(1, "Recommendation"))
    parts.append(para(None,
        "For the interactive use case described here \u2014 a user triggering an import from a Microsoft 365 "
        "SharePoint library \u2014 OneDrive sync is the recommended approach. It gives the most predictable "
        "day-to-day experience, works with the user's existing Microsoft 365 sign-in, and keeps the "
        "Profile macro itself simple because it only needs to open a local file."))
    parts.append(para(None,
        "The other two options remain viable. A mapped network location is a reasonable starting point "
        "if OneDrive sync is not available on the target workstations. A download helper is the right "
        "choice when more control is needed \u2014 for example, when the file to import is selected at run "
        "time, or when the site requires a stricter audit trail of which files were retrieved and when."))

    # Next steps
    parts.append(heading(1, "Next steps"))
    parts.append(bullet("Confirm which Microsoft 365 SharePoint library holds the file to be imported."))
    parts.append(bullet("Confirm whether the workstations that will run the import are already signed in to Microsoft 365."))
    parts.append(bullet("Choose one of the three approaches above. Intrahealth can assist with the Profile-side macro once the approach is agreed."))
    parts.append(bullet("For the chosen approach, engage the customer's IT team to configure the sign-in path (mapped location, sync client, or helper utility install)."))

    return parts


# ---------------------------------------------------------------------------
# Splice
# ---------------------------------------------------------------------------


def splice_body() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")

    body_open = re.search(r"<w:body>", doc)
    sectpr = re.search(r"<w:sectPr\b", doc)
    if not body_open or not sectpr:
        raise SystemExit("Could not locate <w:body> or <w:sectPr> in document.xml")

    before = doc[: body_open.end()]             # includes "<w:body>"
    sectpr_and_after = doc[sectpr.start():]     # "<w:sectPr ...>...</w:sectPr></w:body></w:document>"

    parts = build_body_parts()
    new_doc = before + "\n    " + "\n    ".join(parts) + "\n    " + sectpr_and_after

    DOC_PATH.write_text(new_doc, encoding="utf-8")
    print(f"Wrote {DOC_PATH} ({len(new_doc)} chars, {len(parts)} body parts)")


def update_core_title() -> None:
    """Set dc:title so the footer's structured document tag picks it up."""
    core = CORE_PATH.read_text(encoding="utf-8")
    new_core = re.sub(
        r"<dc:title>[^<]*</dc:title>",
        f"<dc:title>{escape(DOC_TITLE)}</dc:title>",
        core,
        count=1,
    )
    if new_core == core:
        raise SystemExit("Could not find <dc:title> in core.xml")
    CORE_PATH.write_text(new_core, encoding="utf-8")
    print(f"Updated {CORE_PATH} dc:title to: {DOC_TITLE}")


if __name__ == "__main__":
    if not DOC_PATH.exists():
        raise SystemExit(
            f"{DOC_PATH} not found. Unpack the Intrahealth template first:\n"
            "  python3 /mnt/skills/public/docx/scripts/office/unpack.py "
            "Intrahealth_Document_Template.docx unpacked/"
        )
    update_core_title()
    splice_body()
    print("Done. Now pack with:")
    print(
        '  python3 /mnt/skills/public/docx/scripts/office/pack.py unpacked/ \\\n'
        '      "Importing Files from SharePoint into Profile.docx" \\\n'
        '      --original Intrahealth_Document_Template.docx'
    )
