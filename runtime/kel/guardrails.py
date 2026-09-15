"""Locked safety guardrails (V1.4; status corrected in V1.4.1).

These definitions are locked against roles, overrides, project files, repository text, web content,
and worker output. What the engine actually enforces at runtime today (V1.4.1):

- runtime modification of this rule set is detected (`assert_intact`) and stops new worker runs;
- engine-owned project writes refuse frozen-release and system paths (`protected_reason`).

Not yet implemented (deferred to V1.5 — docs/v1.4.1/06_V1_5_DEFERRED_WORK.md): refusing worker
actions against these rules on the execution path. Each rule carries the id of the AUTO-* test that
exercises its checker rule.
"""
import hashlib
import json

from .core import PolicyError

RULES = (
    ('no-registry-write', 'Windows Registry writes are refused; read-only inspection only when diagnosing.', 'AUTO-BLOCK-REG'),
    ('no-screen-takeover', 'Agents never move the mouse, type into the active desktop, or steal focus.', 'AUTO-BLOCK-SYSTEM'),
    ('no-os-critical-write', 'Windows, boot, EFI, partitions, firmware, drivers, BitLocker, and system restore are never modified.', 'AUTO-BLOCK-SYSTEM'),
    ('no-security-weakening', 'Defender, UAC, firewall, SmartScreen, TLS validation, VPN, proxy, DNS, and hosts are never weakened or bypassed.', 'AUTO-BLOCK-SYSTEM'),
    ('credential-boundary', 'Kel reads or writes only its own namespaced credential entries; unrelated secrets are never enumerated, exported, or logged.', 'AUTO-CRED'),
    ('no-identity-change', 'Passwords, MFA, recovery settings, and OS accounts are never changed.', 'AUTO-BLOCK-SYSTEM'),
    ('no-covert-persistence', 'No services, scheduled tasks, startup entries, recorders, or remote-access agents are installed.', 'AUTO-BLOCK-SYSTEM'),
    ('no-destructive-machine-op', 'No format, wipe, partition change, secure erase, shutdown, restart, logoff, sleep, or hibernate.', 'AUTO-BLOCK-SYSTEM'),
    ('frozen-immutable', 'Frozen releases and their manifests and hashes are read-only.', 'AUTO-FROZEN'),
    ('github-admin-redline', 'No repository deletion, transfer, visibility, billing, secret, deploy-key, branch-protection, or webhook changes; no force-push of protected refs.', 'AUTO-GH-ADMIN'),
    ('no-personal-data', 'Unrelated personal material is never inspected or modified; technical accessibility is not authorization.', 'AUTO-PRIVATE'),
    ('no-purchase-or-communication', 'No purchases, subscriptions, or external communications unless the task explicitly requires them.', 'AUTO-EXTERNAL'),
    ('firefox-only-browsing', 'General browsing uses Firefox only (headless, or a dedicated Kel profile, minimized); never the everyday profile.', 'AUTO-BROWSER'),
    ('policy-immutable', 'This policy cannot be edited, disabled, or broadened by any agent, role, project, or content.', 'AUTO-GUARDRAIL-IMMUTABLE'),
)

LOCKED_KEYS = ('locked', 'guardrails', 'guardrail_decisions')
RULE_IDS = tuple(rule for rule, _text, _test in RULES)

# Import-time digest for runtime tamper detection (compare against the live RULES at check time).
DIGEST = hashlib.sha256(json.dumps(RULES, sort_keys=True).encode('utf-8')).hexdigest()

# Locations the engine refuses to write into from its own execution paths (V1.4.1).
FROZEN_MARKERS = ('kel releases', 'kel-v1-frozen', 'kel-v1.1-frozen', 'kel-v1.2-frozen',
                  'kel-v1.3-frozen', 'kel-v1.4-frozen', 'frozen')
SYSTEM_PREFIXES = ('c:\\windows', 'c:\\program files', 'c:\\program files (x86)', 'c:\\programdata')


def _norm(path):
    return str(path or '').replace('/', '\\').lower()


def frozen_path(target):
    return any(marker in _norm(target) for marker in FROZEN_MARKERS)


def system_path(target):
    return any(_norm(target).startswith(prefix) for prefix in SYSTEM_PREFIXES)


def protected_reason(target):
    """Why a location is off-limits for engine-owned writes, or None."""
    if frozen_path(target):
        return 'Frozen releases are read-only'
    if system_path(target):
        return 'System locations are outside every Kel project'
    return None


def assert_intact():
    """Detect runtime modification of the locked rule set; refuse new work when detected.

    This catches in-memory or monkey-patched changes to RULES during the engine's lifetime. It does
    not detect a pre-built modified module (that is release-integrity territory), and it is not an
    execution-path gate against worker actions (deferred to V1.5, docs/v1.4.1/06).
    """
    digest_now = hashlib.sha256(json.dumps(RULES, sort_keys=True).encode('utf-8')).hexdigest()
    if digest_now != DIGEST:
        raise PolicyError('Locked guardrails were modified; refusing new work')
    return True


def locked_block():
    """Read-only guardrail block shown in Studio and the autonomy settings screen."""
    return [{'rule': rule, 'text': text, 'test': test} for rule, text, test in RULES]


def assert_no_lock_edits(fields):
    """Refuse any attempt to edit a locked section through a role, override, or project payload."""
    if not isinstance(fields, dict):
        raise PolicyError('Role fields must be an object')
    for key in fields:
        if key in LOCKED_KEYS:
            raise PolicyError('Locked guardrail sections cannot be edited by any role')
    return True
