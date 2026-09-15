# 09 — Security Review (Kel V1.5)

Status: **in progress** — first results land from the G1/G2 authorization increment; the full
25-case adversarial sweep (Workstream 30) is the G9 gate.

Matrix cases: 1 no lease · 2 expired · 3 revoked · 4 spoofed actor · 5 outside repo · 6 outside
filesystem root · 7 unauthorized domain · 8 unauthorized tool · 9 locked capability · 10 frozen
path · 11 system path · 12 destructive without snapshot · 13 allow-once reused · 14 project grant
revoked · 15 emergency stop during active worker · 16 guardrail tamper · 17 provider credential
leak · 18 renderer requesting secret · 19 export leaking secret · 20 role-policy bypass ·
21 external agent effect outside lease · 22 internal worker recursive spawn · 23 stale authorization
context after restart · 24 job resumed after revoked lease · 25 permission denial during active work.

Per-case results (test + runtime evidence) are appended here as they run; blocking findings stop
the release until fixed.
