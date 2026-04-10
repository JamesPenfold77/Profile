const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  LevelFormat, VerticalAlign
} = require('docx');
const fs = require('fs');

const CONTENT_WIDTH = 9360; // US Letter, 1" margins
const COL1 = 2500;
const COL2 = CONTENT_WIDTH - COL1;

const borderThin = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: borderThin, bottom: borderThin, left: borderThin, right: borderThin };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

function headerCell(text) {
  return new TableCell({
    borders,
    shading: { fill: "1F4E79", type: ShadingType.CLEAR },
    margins: cellMargins,
    children: [new Paragraph({
      children: [new TextRun({ text, bold: true, color: "FFFFFF", size: 20, font: "Arial" })]
    })]
  });
}

function labelCell(text) {
  return new TableCell({
    borders,
    shading: { fill: "D6E4F0", type: ShadingType.CLEAR },
    margins: cellMargins,
    width: { size: COL1, type: WidthType.DXA },
    children: [new Paragraph({
      children: [new TextRun({ text, bold: true, size: 20, font: "Arial" })]
    })]
  });
}

function valueCell(text) {
  return new TableCell({
    borders,
    margins: cellMargins,
    width: { size: COL2, type: WidthType.DXA },
    children: [new Paragraph({
      children: [new TextRun({ text, size: 20, font: "Arial" })]
    })]
  });
}

function coverTable() {
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [COL1, COL2],
    rows: [
      new TableRow({ children: [
        new TableCell({
          borders,
          columnSpan: 2,
          shading: { fill: "1F4E79", type: ShadingType.CLEAR },
          margins: cellMargins,
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "Integration Design \u2013 Information Checklist", bold: true, size: 32, color: "FFFFFF", font: "Arial" })]
          }),
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "ACC Interface \u2013 ACC45 Claims", size: 26, color: "BDD7EE", font: "Arial" })]
          })]
        })
      ]}),
      new TableRow({ children: [labelCell("Date"), valueCell("April 2026")] }),
      new TableRow({ children: [labelCell("Author"), valueCell("[To be confirmed]")] }),
      new TableRow({ children: [labelCell("Version"), valueCell("0.1 \u2013 Draft")] }),
      new TableRow({ children: [labelCell("Status"), valueCell("In Progress")] }),
    ]
  });
}

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 120 },
    children: [new TextRun({ text, bold: true, size: 28, font: "Arial", color: "1F4E79" })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 80 },
    children: [new TextRun({ text, bold: true, size: 24, font: "Arial", color: "2E74B5" })]
  });
}

function body(text) {
  return new Paragraph({
    spacing: { after: 100 },
    children: [new TextRun({ text, size: 20, font: "Arial" })]
  });
}

function bullet(text, bold = false) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 60 },
    children: [new TextRun({ text, size: 20, font: "Arial", bold })]
  });
}

function subBullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 1 },
    spacing: { after: 60 },
    children: [new TextRun({ text, size: 20, font: "Arial" })]
  });
}

function tbc(label) {
  return new Paragraph({
    spacing: { after: 60 },
    children: [
      new TextRun({ text: `${label}: `, bold: true, size: 20, font: "Arial" }),
      new TextRun({ text: "[To be confirmed]", size: 20, font: "Arial", italics: true, color: "888888" })
    ]
  });
}

function noteRow(label, value) {
  return new TableRow({ children: [
    labelCell(label),
    new TableCell({
      borders,
      margins: cellMargins,
      width: { size: COL2, type: WidthType.DXA },
      children: [new Paragraph({ children: [new TextRun({ text: value, size: 20, font: "Arial" })] })]
    })
  ]});
}

function sectionTable(rows) {
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [COL1, COL2],
    rows
  });
}

// ─── PURPOSE SECTION ────────────────────────────────────────────────────────
const purposeContent = [
  h1("Purpose"),
  body("To support the detailed design of Profile-based integrations, a clear understanding of how Profile initiates, processes, and manages integration workflows is required."),
  body("This is not intended to define internal implementation, but to clarify:"),
  bullet("Workflow triggers"),
  bullet("Integration behaviours and lifecycles"),
  bullet("Interaction with external health service providers (e.g. ACC, HealthLink)"),
  body("The aim is to understand each integration workflow end-to-end \u2013 what initiates it, how it progresses, how information is exchanged and how it is completed."),
  h2("Definitions"),
  new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Integration", bold: true, size: 20, font: "Arial" }), new TextRun({ text: " \u2013 the external system (e.g. ACC, HealthLink)", size: 20, font: "Arial" })] }),
  new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "Workflow", bold: true, size: 20, font: "Arial" }), new TextRun({ text: " \u2013 the business capability supported by the integration (e.g. ACC45 claim submission)", size: 20, font: "Arial" })] }),
  new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "Scenario", bold: true, size: 20, font: "Arial" }), new TextRun({ text: " \u2013 a variation or stage within a workflow (e.g. initial submission, amendment/update, status retrieval)", size: 20, font: "Arial" })] }),
];

// ─── SECTION 1: WORKFLOW OVERVIEW ───────────────────────────────────────────
const section1 = [
  h1("1. Workflow Overview"),
  body("The ACC interface within Profile supports the submission and management of ACC45 injury claims. The following workflows are in scope:"),
  h2("1.1  ACC45 Claim Submission"),
  sectionTable([
    new TableRow({ children: [headerCell("Field"), headerCell("Detail")] }),
    noteRow("Workflow Purpose", "Allows clinicians to create and submit ACC45 injury claim forms to ACC directly from within Profile, initiating a new claim for patient treatment costs."),
    noteRow("External Integration", "ACC (Accident Compensation Corporation) via the ACC integration layer. Submission is routed through HealthLink / HMS client intermediary."),
    noteRow("Profile Customisations (Existing)", "ACC45 form is surfaced within the Profile EMR. The AliasCode 'ACC' is used to identify ACC approval records. Claim content is stored in the Comment field of the ISApproval record prior to acceptance."),
    noteRow("Additional Customisations Expected", "[To be confirmed] \u2013 potential scripting to pre-populate ACC45 fields from patient demographics and consultation data."),
  ]),
  new Paragraph({ spacing: { after: 120 } }),
  h2("1.2  Key Scenarios"),
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Scenario A \u2013 Initial Submission", bold: true, underline: {}, size: 20, font: "Arial" })] }),
  bullet("User completes the ACC45 form within Profile against a patient encounter."),
  bullet("Form is submitted to ACC for the first time."),
  bullet("A new ISApproval record is created with AliasCode = 'ACC'."),
  bullet("Reference (claim number) is empty at submission; populated upon ACC acceptance."),
  bullet("Comment field holds ACC45 content pending acceptance."),
  new Paragraph({ spacing: { after: 80 } }),
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Scenario B \u2013 Amendment / Resubmission", bold: true, underline: {}, size: 20, font: "Arial" })] }),
  bullet("An existing ACC45 claim requires correction or additional information."),
  bullet("User amends the form within Profile and resubmits."),
  bullet("Treated as an update to the existing claim (Reference retained)."),
  bullet("Behaviour and mechanism for resubmission: [To be confirmed]."),
  new Paragraph({ spacing: { after: 80 } }),
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Scenario C \u2013 Status Retrieval / Enquiry", bold: true, underline: {}, size: 20, font: "Arial" })] }),
  bullet("Profile queries ACC for the current status of a submitted claim."),
  bullet("Status values surfaced to user (e.g. Pending, Accepted, Rejected, Requires Information)."),
  bullet("No CDO transaction is created on ACC45 submission \u2013 status handling mechanism: [To be confirmed]."),
  new Paragraph({ spacing: { after: 200 } }),
  h2("1.3  Assumptions & Gaps"),
  sectionTable([
    new TableRow({ children: [headerCell("Item"), headerCell("Note")] }),
    noteRow("Amendment mechanism", "It is assumed resubmission retains the original claim Reference. To be confirmed with ACC / HealthLink documentation."),
    noteRow("Status polling", "It is unknown whether Profile polls ACC for status updates or relies on inbound notifications. To be confirmed."),
    noteRow("Multi-provider claims", "Behaviour when the claim involves multiple providers is out of scope for initial design and to be confirmed separately."),
    noteRow("Reference population timing", "Reference (claim number) is populated by ACC upon acceptance. The exact timing and mechanism for this update within Profile is to be confirmed."),
  ]),
  new Paragraph({ spacing: { after: 200 } }),
];

// ─── SECTION 2: TRIGGER EVENTS ──────────────────────────────────────────────
const section2 = [
  h1("2. Trigger Events (Profile Behaviour)"),
  body("This section describes what actions within Profile cause an ACC45 workflow to be initiated, a message to be created or submitted, or a follow-up action to be triggered."),
  h2("2.1  Workflow Initiation Triggers"),
  sectionTable([
    new TableRow({ children: [headerCell("Trigger Type"), headerCell("Detail")] }),
    noteRow("User Action \u2013 New Claim", "A clinician opens the ACC45 form from within a patient encounter in Profile and completes the required fields. Submitting the form is the explicit user action that initiates the workflow."),
    noteRow("User Action \u2013 Amendment", "A clinician opens a previously submitted ACC45 approval record and edits and resubmits it. This triggers the amendment/resubmission workflow."),
    noteRow("Business Event \u2013 Status Change", "An inbound status response from ACC (e.g. Accepted, Rejected, Requires Information) may trigger further user action within Profile. Whether this is event-driven or polling-based is to be confirmed."),
    noteRow("System Event \u2013 Retry", "If a submission fails due to a technical error, Profile may automatically retry. Conditions and retry logic are to be confirmed (see Section 8)."),
  ]),
  new Paragraph({ spacing: { after: 160 } }),
  h2("2.2  Message Creation Triggers"),
  body("The following events cause an integration message (ACC45 payload) to be constructed by Profile:"),
  bullet("User confirms/submits the ACC45 form in Profile \u2013 triggers initial message creation."),
  bullet("User saves an amendment to an existing ACC45 record and resubmits \u2013 triggers an updated message."),
  bullet("No CDO transaction is created on ACC45 submission; message construction mechanism is to be confirmed."),
  new Paragraph({ spacing: { after: 80 } }),
  sectionTable([
    new TableRow({ children: [headerCell("Field"), headerCell("Detail")] }),
    noteRow("Message created on form submission?", "Yes \u2013 assumed to be created at point of user submission."),
    noteRow("Message created on save (draft)?", "[To be confirmed] \u2013 whether Profile supports draft/save-without-submit behaviour."),
    noteRow("Message format", "[To be confirmed] \u2013 expected to be HL7 or ACC-specified XML/JSON payload via HealthLink."),
    noteRow("Who constructs the message?", "Profile application layer. Scripting customisation may pre-populate fields. Detail to be confirmed."),
  ]),
  new Paragraph({ spacing: { after: 160 } }),
  h2("2.3  Follow-up Action Triggers"),
  body("The following events trigger follow-up actions after initial submission:"),
  sectionTable([
    new TableRow({ children: [headerCell("Trigger"), headerCell("Follow-up Action"), headerCell("Notes")] }),
    new TableRow({ children: [
      new TableCell({ borders, margins: cellMargins, width: { size: 2800, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "ACC response: Accepted", size: 20, font: "Arial" })] })] }),
      new TableCell({ borders, margins: cellMargins, width: { size: 3280, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Reference (claim number) is populated on the ISApproval record in Profile.", size: 20, font: "Arial" })] })] }),
      new TableCell({ borders, margins: cellMargins, width: { size: 3280, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Timing of Reference population to be confirmed.", size: 20, font: "Arial", italics: true, color: "888888" })] })] }),
    ]}),
    new TableRow({ children: [
      new TableCell({ borders, margins: cellMargins, width: { size: 2800, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "ACC response: Rejected", size: 20, font: "Arial" })] })] }),
      new TableCell({ borders, margins: cellMargins, width: { size: 3280, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "User is notified within Profile. Correction and resubmission may be required.", size: 20, font: "Arial" })] })] }),
      new TableCell({ borders, margins: cellMargins, width: { size: 3280, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Notification mechanism to be confirmed.", size: 20, font: "Arial", italics: true, color: "888888" })] })] }),
    ]}),
    new TableRow({ children: [
      new TableCell({ borders, margins: cellMargins, width: { size: 2800, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "ACC response: Requires Information", size: 20, font: "Arial" })] })] }),
      new TableCell({ borders, margins: cellMargins, width: { size: 3280, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "User prompted to provide additional information and resubmit.", size: 20, font: "Arial" })] })] }),
      new TableCell({ borders, margins: cellMargins, width: { size: 3280, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "[To be confirmed]", size: 20, font: "Arial", italics: true, color: "888888" })] })] }),
    ]}),
    new TableRow({ children: [
      new TableCell({ borders, margins: cellMargins, width: { size: 2800, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Technical failure / timeout", size: 20, font: "Arial" })] })] }),
      new TableCell({ borders, margins: cellMargins, width: { size: 3280, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Automatic retry or user intervention depending on error type. See Section 8.", size: 20, font: "Arial" })] })] }),
      new TableCell({ borders, margins: cellMargins, width: { size: 3280, type: WidthType.DXA }, children: [new Paragraph({ children: [new TextRun({ text: "Retry logic to be confirmed.", size: 20, font: "Arial", italics: true, color: "888888" })] })] }),
    ]}),
  ]),
  new Paragraph({ spacing: { after: 160 } }),
  h2("2.4  Assumptions & Gaps"),
  sectionTable([
    new TableRow({ children: [headerCell("Item"), headerCell("Note")] }),
    noteRow("Draft/save behaviour", "It is unknown whether Profile supports saving an ACC45 form without submitting it. To be confirmed."),
    noteRow("Automated triggers", "It is assumed ACC45 submission is entirely user-initiated. Any background/scheduled triggers are to be confirmed."),
    noteRow("Status notification mechanism", "Whether ACC pushes status responses to Profile (event-driven) or Profile polls ACC for updates is to be confirmed. This affects follow-up trigger behaviour."),
    noteRow("Multi-provider trigger", "Trigger behaviour for claims involving multiple providers is out of scope for initial design."),
  ]),
  new Paragraph({ spacing: { after: 200 } }),
];

// NOTE: Sections 3-13 follow the same pattern.
// Full source available in the Claude session that generated this file (April 2026).
// To regenerate the complete document, re-run the full script from that session.
// Sections 3-13 cover: Message Creation & Submission, Interaction Pattern, Data Requirements,
// Response & Status Handling, Amendment / Resubmission, Error Handling & Retry,
// Integration Mechanism, Environment & Configuration, Security & Authentication,
// Operational Behaviour, and Reference Materials.

// ─── DOCUMENT ASSEMBLY (Sections 1-2 only in this abbreviated version) ──────
// To regenerate the full 13-section document, use the complete script from Claude.
const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
      ]
    }]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "1F4E79" },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "2E74B5" },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [
      coverTable(),
      new Paragraph({ spacing: { after: 240 } }),
      ...purposeContent,
      new Paragraph({ spacing: { after: 240 } }),
      ...section1,
      ...section2,
      // sections 3-13 omitted in this abbreviated version
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("ACC45_Integration_Design_Checklist.docx", buf);
  console.log("Done");
});
