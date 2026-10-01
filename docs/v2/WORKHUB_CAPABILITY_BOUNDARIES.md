# Work-hub capability boundaries

September 30 continuation. This document describes source contracts. The installed
commit and acceptance receipts live in `App/kel-install-provenance.json` and
`Tools/strategy-2026-09-30`. A source change alone does not prove installed behavior.

## Bringing existing work into Kel

Users choose a Project, select or paste a transcript, review it, and confirm.
Supported structured inputs are Kel transcript JSON, completed Codex CLI JSONL,
and successful Claude Code terminal JSON/JSONL. Claude imports only its final
result. Intermediate text, tool work, reasoning, and original attachments remain
explicit omissions. Source session IDs are references, never continuation grants.
Claude and DeepSeek browser exports have no verified parser here. Plain text
remains available for both. Kel never guesses an undocumented vendor schema.

References can contain UTF-8 text, PDF text, or image OCR. Selected originals are
inert database BLOBs. Extraction receives bytes, never a user path or remote URL.
The child has a 20-second limit, a Windows Job memory limit of 512 MB, one active
process, and a parent output cap of 200,000 bytes. PDF extraction accepts at most
20 pages. Password-protected PDFs and pages without readable text fail with a
plain reason. Windows OCR needs an installed recognition language. It extracts
text, not the meaning of diagrams or document layout.

Each selected original is limited to 5 MB. Derived text is limited to 30,000
characters. An import accepts ten references and 100,000 combined characters.
Original storage has a 50 MB total limit, including adopted originals. Staged
receipts expire after 24 hours; adopted originals stay with their first import.
Deleted or moved conversations cannot expose originals through the old Project.

The interface exposes the full bounded extracted text before confirmation.
Preview and confirmation bind original/text hashes and extraction provenance.
Confirmation rechecks the receipt atomically. Saving an original requires an
explicit action and returns an inert download. Importing never starts a worker.
Changing Projects clears pending input and stops later batch extraction requests.

## Direct writing and attachments

Direct writing can enforce supported total-word limits and unambiguous paragraph
counts from the current trusted request. Quoted examples cannot create a limit.
A topical year such as “about 2020” cannot disable an exact word instruction.
Maximum-word corrections may stay shorter than the maximum. Corrections preserve
authored paragraph boundaries. One durable, accounted correction is allowed;
both candidate selection and final publication enforce the requested constraints.
Explicit prose paragraphs also require sentence-ending punctuation. Inspection
never changes the authored text. This catches unfinished endings; it does not
prove grammatical or semantic quality. Complex per-part formats are not
generalized from this contract.

Direct replies with explicit prose paragraph constraints require one bounded
review from a confirmed different model family. This review checks the final
authored bytes against the request. It refuses unclear, rejected, malformed,
unavailable, or late verdicts. Publication binds the request and candidate hashes.
The request allows at most three admitted adapter calls and 120 seconds.
The reviewer cannot use an API fallback or start another repair loop.
Factual review uses the request only. Essential unseen context requires uncertainty.
Fixture verdicts prove publication control, not actual reviewer accuracy.

Supported native Codex image input uses actual selected conversation-owned bytes.
Delivery rechecks size, MIME, digest, storage ancestry, and conversation ownership.
Private staging supplies fixed `--image` arguments. It does not enable file tools
or accept user-controlled flags. Unsupported selected models fail explicitly.
They do not silently switch to an API connection or broad Claude Read access.
Selected PDFs use bounded derived text rather than raw PDF syntax.

Imported source context stays tied to the original visible import message and
current Project. It survives the recent-message window. Selected source bodies
are mandatory and appear once. Large sources use bounded lexical excerpts with
character ranges, hashes, and explicit partial coverage. Whole-source requests
that cannot fit fail before dispatch. Lexical selection does not prove semantic
coverage. A trusted prompt guard forbids claims about unseen source sections.

## Execution protection and capture

Trusted test commands use the configured Codex sandbox for both native providers.
Missing readiness or startup failure stops the command. Ordinary-process fallback
is forbidden. Working paths must have plain ancestors and retain their initial
identity. Source tests exercise authority, scope, cancellation, and output limits.

The measured Windows boundary blocked an owned sibling write. It allowed a
loopback connection despite network-disabled configuration. Complete read
confinement and external network denial are not established. Elevated mode
remains explicit and fails closed when unavailable. Arbitrary Windows batch
shims have a failed compatibility receipt; that failure is not labeled success.
Recognized installed npm/npx shims use the matching adjacent Node executable and
fixed npm entry file without a shell. Receipts disclose the original command,
actual arguments, and installed npm version. Unknown shims are refused. The
bounded production npm-version check passed after a separate fixture config error.

Microphone initialization releases acquired tracks and created resources on
failure. Insecure or unsupported browser origins show a specific recording
reason. Typed input and recorded-file upload remain available. Responsive render
and mocked capture checks do not establish physical-phone or speech accuracy.

## Evidence limits

Small writing samples can demonstrate a particular checked reply. They cannot
establish a universal best model or guaranteed cost savings. Calibration remains
advisory. API-equivalent estimates are not billed subscription charges.

The earlier packaged writing-check creation was rejected by automatic approval
review. It must not be retried through another route. Generic import/layout App
checks do not represent packaged writing acceptance. The repository's named
`request_review` tool is unavailable; independent agent reviews are identified
separately. Existing policy-blocked cleanup paths stay untouched.

This continuation preserves the approved appearance, user edits, real Data,
credentials, and Git history. Delivery requires matching frozen modules,
resources, actual installer payload, and canonical installed App identity.
