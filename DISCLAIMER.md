# DISCLAIMER — Industrial Use

> **Read this before using any output of AUTOMATION_FACTORY in an
> industrial installation.** This document supplements (and does not
> replace) the [LICENSE](LICENSE) and the AI Responsibility section of
> the [README](README.md).

## 1. What this software is — and is not

AUTOMATION_FACTORY is an **engineering productivity tool**. It drafts
documentation and PLC code skeletons to assist a **qualified automation
engineer**. It is **not** a certified engineering tool, **not** a
substitute for engineering judgment, and **not** a source of validated,
field-ready control logic.

## 2. No warranty

The software and all of its outputs (documents, IO lists, SCL/DB
sources, reports, labels) are provided **"AS IS", without warranty of
any kind**, express or implied — including, without limitation,
warranties of merchantability, fitness for a particular purpose,
accuracy, or non-infringement. AI-generated content can be wrong in
ways that look plausible.

## 3. Verification obligation

No output of this tool may be deployed to a machine until it has passed,
at minimum:

1. line-by-line review by a qualified engineer,
2. a successful TIA Portal compile,
3. behavioural testing (PLCSIM or equivalent), and
4. commissioning tests (FAT/SAT) appropriate to the installation.

The labels emitted by the tool (`DRAFT_UNVERIFIED`,
`AUTO_VERIFIED_structural`, `AUTO_VERIFIED_compile`,
`PENDING_PLCSIM_VERIFY`) exist to make this obligation visible — none of
them means "field-ready".

## 4. Functional safety

Outputs of this tool are **never** suitable for Safety Instrumented
Systems (IEC 61508 / IEC 62061) or safety-related control functions
(ISO 13849). The tool deliberately refuses to generate safety logic and
skips F-blocks on import. SIL/PLr assignment, F-program design and
safety validation are the exclusive responsibility of a certified
safety engineer.

## 5. Limitation of liability

To the maximum extent permitted by applicable law, the authors and
contributors of this software accept **no liability** for any direct,
indirect, incidental, special, consequential or exemplary damages
arising from the use of this software or its outputs — including but
not limited to production loss, equipment damage, data loss, personal
injury, or death. **The engineer who reviews, imports, modifies or
approves an output assumes full professional and legal responsibility
for the resulting PLC program and its behaviour in the field.**

## 6. Data responsibility

The built-in classification guard reduces, but cannot eliminate, the
risk of sending sensitive data to cloud AI providers. Verifying the
data classification of a project, obtaining customer permission for any
data transfer, and redacting identifying information from images/PDFs
remain the user's responsibility.

---

*This document is an engineering-practice disclaimer, not legal advice.
If you redistribute this tool commercially or bundle it into a paid
service, have the wording reviewed by qualified legal counsel for your
jurisdiction.*
