---
name: profile-integration-design
description: "Use this skill when generating an Integration Design Information Checklist report for a specific Profile integration (e.g. ACC, HealthLink, Labs). Triggers include: 'generate an integration design checklist for X', 'fill out the design checklist for Y integration', 'create an integration report for Z'. The skill provides the canonical 13-section template structure and instructions for populating it with integration-specific details as a .docx file."
---

# Profile Integration Design – Information Checklist Skill

## Purpose

This skill produces a completed **Integration Design Information Checklist** `.docx` for a specific Profile integration. It is based on the standard Intrahealth template and should be used whenever a design checklist report needs to be generated or pre-populated for a given integration (e.g. ACC, HealthLink, Labs).

The output is a Word document (`.docx`) built using the `docx` skill. Always read `/mnt/skills/public/docx/SKILL.md` before generating the file.

---

## Template Structure

Every report follows this 13-section structure. Populate each section with integration-specific information provided by the user, inferred from context/memory, or left as a clearly marked placeholder (`[To be confirmed]`) where information is unknown.

### Document Header
- Title: **Integration Design – Information Checklist**
- Sub-title: `<Integration Name> Integration` (e.g. *ACC Integration*)
- Date, Author, Version fields

---

### Section 1 – Workflow Overview
- Description of each workflow's purpose within Profile
- External integrations/dependencies required (e.g. ACC, HealthLink)
- Key scenarios within each workflow:
  - Initial submission
  - Amendment / resubmission
  - Status retrieval / enquiry
- Existing Profile customisations supporting the workflow
- Whether additional customisations are expected or required

### Section 2 – Trigger Events (Profile Behaviour)
- What actions in Profile trigger each workflow (user actions, business events, or system events)
- What triggers message creation or submission
- What triggers follow-up actions (e.g. status checks, resubmission)

### Section 3 – Message Creation & Submission
- How Profile constructs integration messages (high-level)
- When messages are created within the workflow
- Whether submission is immediate or queued
- How Profile determines the destination (e.g. ACC endpoint, HealthLink mailbox)

### Section 4 – Interaction Pattern
- Whether interactions are:
  - Synchronous (request/response), or
  - Asynchronous (submission with subsequent status retrieval)
- How Profile handles intermediate states (e.g. pending)
- Whether polling or scheduled status checks are used

### Section 5 – Data Requirements
- Data required by Profile to initiate each workflow
- Mandatory data elements (high-level)
- What validation is performed
- Data expected to be returned and consumed
- Key identifiers used across interactions (e.g. claim ID, reference ID)

### Section 6 – Response & Status Handling
- How Profile processes responses from external systems
- Status values used within Profile (e.g. pending, accepted, rejected, requires information)
- How statuses are presented to users
- How Profile determines when a workflow is complete

### Section 7 – Amendment / Resubmission Behaviour
- How Profile handles scenarios where external systems require updates or corrections
- How users amend previously submitted data
- How Profile resubmits updated information
- Whether resubmission is treated as a new request or an update to an existing request

### Section 8 – Error Handling & Retry Behaviour
- How Profile handles:
  - Validation errors
  - Business errors
  - Technical failures
- Whether Profile automatically retries failed submissions
- Conditions that trigger retry versus user intervention

### Section 9 – Integration Mechanism (e.g. HealthLink / APIs)
- External systems or services involved in the workflow
- Expected interface(s) used for integration:
  - Direct APIs
  - Intermediaries (e.g. HealthLink / HMS client)
- How message routing is determined
- Whether alternative integration methods are available

### Section 10 – Environment & Configuration
- Available environment endpoints (dev/test/prod)
- Endpoint configuration requirements (e.g. URLs, IP addresses)
- Environment-specific behaviour or differences (e.g. Service Throttling)
- Network requirements (e.g. IP allowlisting)
- Any environment configuration required

### Section 11 – Security & Authentication
- Authentication methods used by Profile
- Certificate or credential requirements
- Encryption requirements (e.g. TLS versions)
- Any additional security constraints

### Section 12 – Operational Behaviour
- Logging and traceability (e.g. correlation IDs, request tracking)
- Monitoring and visibility of integration status
- Support model and issue resolution approach

### Section 13 – Reference Materials
- Existing documentation or workflow descriptions
- Diagrams or implementation notes

---

## Generation Instructions

1. **Always read** `/mnt/skills/public/docx/SKILL.md` first.
2. Ask the user which integration to generate the checklist for if not already specified.
3. Populate each section with whatever detail the user provides. For unknown fields, use `[To be confirmed]`.
4. Build the `.docx` using `docx` (npm) following the docx skill patterns:
   - US Letter page size (12240 × 15840 DXA), 1-inch margins
   - Arial font, 12pt body
   - Heading 1 for section numbers/titles, Heading 2 for sub-sections
   - Bullet lists using `LevelFormat.BULLET` (never unicode bullets)
   - A cover table with Title, Integration, Date, Author, Version
5. Validate the output with `python scripts/office/validate.py`.
6. Copy the final file to `/mnt/user-data/outputs/` and present it with `present_files`.

---

## Template Preamble Text

Include this verbatim in the document's Purpose section:

> To support the detailed design of Profile-based integrations, a clear understanding of how Profile initiates, processes, and manages integration workflows is required.
>
> This is not intended to define internal implementation, but to clarify workflow triggers, integration behaviours and lifecycles, and interaction with external health service providers (e.g. ACC, HealthLink).
>
> The aim is to understand each integration workflow end-to-end – what initiates it, how it progresses, how information is exchanged and how it is completed.

**Definitions:**
- **Integration** – the external system (e.g. ACC, HealthLink)
- **Workflow** – the business capability supported by the integration (e.g. ACC 45 claim submission)
- **Scenario** – a variation or stage within a workflow (e.g. initial submission, amendment/update, status retrieval)

---

## Notes

- Source template: `Integration_Design_Checklist.docx` (uploaded April 2026)
- This skill covers the **output** (report generation). The user supplies the answers; Claude structures them into the document.
- If the user has already described an integration in prior conversation (e.g. ACC), pre-fill what is known from that context before asking for missing details.
