# Josh Mauer CPA LLC — Grounded Knowledge Export (Operational Only)

Source basis: prior recalled context I could ground, plus the current conversation. I excluded tax advice, tax positions, client-identifying details, and anything I could not support well enough.

## Labeling vocabulary

This file uses the three-label framework defined in `SKILL.md`:

- **I know** — claim is grounded in a confirmed source. Safe to use.
- **I am inferring** — claim is a reasoned guess from related facts. Use with the inference label visible.
- **I do not know** — no grounded information. Verify with Josh before any production use.

Legacy "High / Medium / Low" markers below should be read as: High = *I know*, Medium = *I am inferring*, Low = *I do not know*. The Low-Confidence Flag List at the bottom of this file is the *I do not know* register.

## SUMMARY TABLE

| Section | # of Items | Label Distribution |
|---|---:|---|
| 1. Firm Policies & Rules | 4 | 3 know / 1 inferring |
| 2. Decision-Making Patterns | 3 | 3 know |
| 3. Tool & Software Preferences | 7 | 5 know / 2 inferring |
| 4. Team Structure & Delegation | 2 | 1 know / 1 do-not-know |
| 5. Client Communication Philosophy | 0 | N/A |
| 6. Things I've Said the Agent Should or Shouldn't Do | 4 | 3 know / 1 inferring |
| 7. Recurring Problems & Pet Peeves | 2 | 1 know / 1 inferring |
| 8. Anything Else | 2 | 1 know / 1 inferring |

---

## SECTION 1: FIRM POLICIES & RULES

**Policy:** Employees must maintain strict confidentiality of company and client information; unauthorized disclosure can lead to disciplinary action up to termination.  
**Context:** Recalled from documented employment materials and security obligations for staff with access to client systems/data.  
**Confidence:** High

**Policy:** Staff employment, at least in recent hiring documents, is at-will.  
**Context:** Recalled from employment agreements/offer letters for firm hires.  
**Confidence:** High

**Policy:** Remote access to firm systems/client data is permitted as needed, but subject to the same confidentiality and security obligations as in-office work.  
**Context:** Recalled from employment/onboarding materials for staff with system access.  
**Confidence:** High

**Policy:** New staff may begin part-time with phased benefits eligibility (retirement plan after 90 days; HRA upon full-time transition).  
**Context:** Recalled from a specific hire's employment terms; this may not be universal across all roles.  
**Confidence:** Medium

No recalled grounded information on billing, engagement letters, payment terms, review standards, quality control, or deadline-management policy.

---

## SECTION 2: MY DECISION-MAKING PATTERNS

**Pattern:** Pilot operational changes before broader rollout.  
**Example:** A storage change involving Google Drive / Google Drive File Stream was approached by testing with a past Drake year file and a limited staff pilot before any larger migration.  
**Confidence:** High

**Pattern:** Delegate execution and workflow-improvement work, but keep management oversight.  
**Example:** Varun's role combines accounting support with TaxDome workflow improvement under Josh's direct supervision.  
**Confidence:** High

**Pattern:** Choose infrastructure based on operational fit and reliability, especially for Windows-based accounting/tax software.  
**Example:** AWS WorkSpaces remained preferred over alternatives that did not fit Windows/application requirements; storage migration ideas were treated cautiously when multi-user/file-locking risks existed.  
**Confidence:** High

---

## SECTION 3: TOOL & SOFTWARE PREFERENCES

**Tool:** AWS WorkSpaces  
**Preference/Workflow:** Primary Windows virtual desktop environment for Drake Tax and QuickBooks Desktop.  
**Confidence:** High

**Tool:** Drake / Google Drive File Stream  
**Preference/Workflow:** When considering storage changes, use a controlled test with a past-year Drake file and limited staff participation before migrating anything broadly.  
**Confidence:** High

**Tool:** QuickBooks Desktop  
**Preference/Workflow:** Multi-user files should not rely solely on Google Drive until proven safe; file-locking/data-conflict risk is a concern.  
**Confidence:** Medium

**Tool:** Google Drive / CPAVerse B drive  
**Preference/Workflow:** Google Drive was evaluated as a possible replacement for the B drive, but concurrent-edit risks were a major concern.  
**Confidence:** High

**Tool:** Google Vault  
**Preference/Workflow:** Considered useful for retention/compliance, but not treated as backup.  
**Confidence:** High

**Tool:** Google Chat  
**Preference/Workflow:** Used for internal communication. No grounded workflow standard was retrieved beyond that.  
**Confidence:** Medium

**Tool:** TaxDome  
**Preference/Workflow:** Pipeline efficiency is a clear operational priority; at least one staff role was designed in part to improve TaxDome workflow.  
**Confidence:** High

---

## SECTION 4: TEAM STRUCTURE & DELEGATION

**Name:** Varun Ganji  
**Role/Strengths:** Staff Accountant & Workflow Assistant; balance-sheet reconciliations, accounting support, TaxDome pipeline improvements, reporting support, and support for 2025 planning initiatives.  
**Routing:** Work routed to him includes reconciliation, workflow improvement, reporting support, and operational assistance under Josh's supervision.  
**Notes:** Entry-level hire starting 2025-02-16; primarily in-office with remote access as needed; directly supervised by Josh.  
**Confidence:** High

**Name:** Rita  
**Role/Strengths:** Key employee since 2023-08. Exact functional lane is **UNCERTAIN — verify with Josh**.  
**Routing:** Appears to be a trusted/core employee tied to firm growth; exact routing is **UNCERTAIN — verify with Josh**.  
**Notes:** Compensation structure changed effective 2025-01-01 to include revenue share, which suggests trusted/key-employee status, but exact operational responsibilities were not reliably retrieved.  
**Confidence:** Low

---

## SECTION 5: CLIENT COMMUNICATION PHILOSOPHY

No recalled information for this section.

---

## SECTION 6: THINGS I'VE SAID THE AGENT SHOULD OR SHOULDN'T DO

**Directive:** The agent should help with data entry, Drake troubleshooting, TaxDome workflows, client communication, and triage.  
**Context:** Stated explicitly in the current prompt for the firm agent.  
**Confidence:** High

**Directive:** The agent must never give tax advice or state tax positions. That remains the preparer's job.  
**Context:** Stated explicitly in the current prompt.  
**Confidence:** High

**Directive:** The agent should behave like a well-trained staff member on operational/procedural work, not as a tax decision-maker.  
**Context:** Stated in the current prompt and implied by the requested scope.  
**Confidence:** High

**Directive:** There is interest in AI automation / a CPAverse-style agent for workflow improvement, but prior retrieved specifics about scope, red lines, or product vision were limited.  
**Context:** General prior context showed AI automation interest, but detailed prior directives were not retrieved.  
**Confidence:** Medium

---

## SECTION 7: RECURRING PROBLEMS & PET PEEVES

**Problem:** Risk of duplicate files/data conflicts if Google Drive is used for concurrent edits with Drake or QuickBooks.  
**My Fix/Expectation:** Test in a limited pilot first; do not assume multi-user storage changes are safe without proving them.  
**Confidence:** High

**Problem:** TaxDome pipeline efficiency needed improvement strongly enough to create/assign workflow-assistant responsibilities.  
**My Fix/Expectation:** Give workflow improvement explicit ownership instead of treating it as an ad hoc side task.  
**Confidence:** Medium

---

## SECTION 8: ANYTHING ELSE

**Item:** Firm culture appears to favor cautious modernization — trying new systems, but with controlled testing and compliance/security awareness.  
**Confidence:** High

**Item:** Roles can be designed to combine operational improvement with accounting support, suggesting Josh values staff who both execute and improve systems.  
**Confidence:** Medium

---

## "I DO NOT KNOW" REGISTER (formerly Low-Confidence Flag List)

These items are explicitly *I do not know* under the three-label framework. Verify with Josh or strike before using them in production:

1. **Section 1:** New staff may begin part-time with phased benefits eligibility — may be role-specific rather than firm-wide.  
2. **Section 3:** QuickBooks Desktop should not rely solely on Google Drive for multi-user use — grounded concern, but final policy status should be confirmed.  
3. **Section 3:** Google Chat is used for internal communication — no workflow standard was retrieved.  
4. **Section 4:** Rita's exact role, strengths, and routing are uncertain.  
5. **Section 6:** Prior AI automation / CPAverse agent directives beyond the current prompt were not retrieved in detail.  
6. **Section 7:** TaxDome pipeline inefficiency as a recurring pain point is inferred from staffing/workflow focus and should be verified explicitly.  
7. **Section 8:** Combined accounting + workflow-improvement roles as a general preference should be verified as a durable pattern rather than a one-off staffing choice.
