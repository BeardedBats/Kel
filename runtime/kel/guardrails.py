"""Locked safety guardrails (V1.4).

Immutable by design: no role, override, project file, repository text, web content, or worker output
may add, weaken, or disable a rule. Only a direct user instruction can change these definitions.
Every rule carries the id of the test that proves it is enforced.
"""
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
