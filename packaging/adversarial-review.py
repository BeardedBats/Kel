#!/usr/bin/env python3
"""Adversarial acceptance sweep for Kel V1.4 (Gate 10).

Checks the shipped tree against the criteria this project committed to, rather than against intent:
the design system's do-not-ship list, the packaged-app contract, ledger honesty, evidence coverage, and
the code smells a hostile reviewer would look for. Prints a bounded report and exits non-zero when a
blocking finding is present.

Usage: python packaging/adversarial-review.py [--json]
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENDERER = ROOT / 'desktop' / 'packages' / 'desktop' / 'src' / 'renderer'
ENGINE = ROOT / 'runtime' / 'kel'
V14_MODULES = ('solution.py', 'team.py', 'providers.py', 'autonomy.py', 'diagnostics.py')
V14_PAGES = ('work', 'team', 'projects', 'providers', 'autonomy', 'diagnostics', 'onboarding')
KEL_CSS = ('kel-tokens.css',)


def sh(command):
    result = subprocess.run(command, shell=True, cwd=str(ROOT), capture_output=True, text=True)
    return result.stdout.strip()


def run_checks():
    findings = []

    def add(severity, area, detail, evidence=''):
        findings.append({'severity': severity, 'area': area, 'detail': detail, 'evidence': evidence})

    # 1. Design-system do-not-ship list ------------------------------------------------------------
    emoji = sh(
        "grep -rhoP '[\\x{1F300}-\\x{1FAFF}\\x{2600}-\\x{27BF}]' --include=*.tsx "
        "desktop/packages/desktop/src/renderer/components/kel desktop/packages/desktop/src/renderer/pages/kel "
        "2>/dev/null | wc -l"
    )
    if emoji and int(emoji) > 0:
        add('high', 'do-not-ship', f'{emoji} emoji characters in Kel UI sources')

    gradients = sh(
        "grep -rn 'linear-gradient\\|radial-gradient' --include=*.css "
        "desktop/packages/desktop/src/renderer/styles 2>/dev/null | grep -v donor legacy | wc -l"
    )
    if gradients and int(gradients) > 0:
        add('medium', 'do-not-ship', f'{gradients} gradient declarations remain in renderer styles')

    bounce = sh(
        "grep -rn 'cubic-bezier(0\\.[6-9]\\|bounce\\|elastic\\|overshoot' --include=*.css "
        "desktop/packages/desktop/src/renderer/styles 2>/dev/null | wc -l"
    )
    if bounce and int(bounce) > 0:
        add('high', 'do-not-ship', f'{bounce} bounce/overshoot easing declarations')

    reduced = sh(
        "grep -c 'prefers-reduced-motion' desktop/packages/desktop/src/renderer/styles/kel-tokens.css"
    )
    if not reduced or int(reduced) == 0:
        add('high', 'do-not-ship', 'no reduced-motion fallback in the Kel token sheet')

    # 2. Engine hygiene ----------------------------------------------------------------------------
    prints = sh(
        "grep -rn 'print(' runtime/kel/solution.py runtime/kel/team.py runtime/kel/providers.py "
        "runtime/kel/autonomy.py runtime/kel/diagnostics.py 2>/dev/null | wc -l"
    )
    if prints and int(prints) > 0:
        add('medium', 'engine-hygiene', f'{prints} print() calls in V1.4 engine modules')

    silent = sh(
        r"grep -rn -A1 'except Exception:' runtime/kel/solution.py runtime/kel/team.py "
        r"runtime/kel/providers.py runtime/kel/autonomy.py runtime/kel/diagnostics.py runtime/kel/service.py "
        r"2>/dev/null | grep -E '^\S+-[0-9]+-\s+pass\s*$' | wc -l"
    )
    if silent and int(silent) > 0:
        add('low', 'engine-hygiene',
            f'{silent} silent catches with no justification comment (every "pass" must say why)')
    justified = sh(
        r"grep -rn -A1 'except Exception:' runtime/kel/solution.py runtime/kel/team.py "
        r"runtime/kel/providers.py runtime/kel/autonomy.py runtime/kel/diagnostics.py runtime/kel/service.py "
        r"2>/dev/null | grep -cE '^\S+-[0-9]+-\s+pass\s+#'"
    )
    add('info', 'engine-hygiene', f'{justified} silent catches carry an inline justification')

    todos = sh(
        "grep -rn 'TODO\\|FIXME\\|XXX\\|HACK' runtime/kel/solution.py runtime/kel/team.py "
        "runtime/kel/providers.py runtime/kel/autonomy.py runtime/kel/diagnostics.py "
        "desktop/packages/desktop/src/renderer/pages/kel desktop/packages/desktop/src/renderer/components/kel "
        "2>/dev/null | wc -l"
    )
    if todos and int(todos) > 0:
        add('medium', 'engine-hygiene', f'{todos} TODO/FIXME markers in V1.4 sources')

    # 3. Ledger honesty ----------------------------------------------------------------------------
    ledger = ROOT / 'docs' / 'v1.4' / 'KEL_V1.4_FEATURE_LEDGER.md'
    if ledger.exists():
        text = ledger.read_text(encoding='utf-8')
        rows = [line for line in text.splitlines() if line.startswith('| V14-')]
        statuses = {}
        vocabulary = ('ALREADY_PRESENT', 'EXTEND', 'NEW', 'IMPLEMENTED', 'VERIFIED', 'PENDING',
                      'DEFERRED', 'BLOCKED', 'COMPLETE', 'IN PROGRESS', 'DONE')
        advanced = 0
        for row in rows:
            cells = [cell.strip() for cell in row.strip('|').split('|')]
            # Match the status by vocabulary rather than by column position: the ledger carries both a
            # provenance column and a status column, so a positional guess reads the wrong one.
            status = next((cell for cell in cells if cell.upper() in vocabulary), 'UNRECOGNISED')
            statuses[status] = statuses.get(status, 0) + 1
            if status.upper() in ('IMPLEMENTED', 'VERIFIED', 'COMPLETE', 'DONE'):
                advanced += 1
        add('info', 'ledger', f'{len(rows)} ledger rows; statuses: {statuses}')
        if statuses.get('UNRECOGNISED', 0) > 0:
            add('medium', 'ledger',
                f"{statuses['UNRECOGNISED']} ledger rows carry no recognised status value")
        # Triage statuses are the starting vocabulary; the gates record their delivered scope in the
        # per-gate blocks. This reports how much of the ledger has advanced per row, which is the
        # documentation gap a hostile reviewer would name first.
        add('info', 'ledger', f'rows advanced past triage (IMPLEMENTED/VERIFIED): {advanced}/{len(rows)}')
        if advanced == 0:
            add('medium', 'ledger',
                'no ledger row has advanced past its triage status; per-gate delivered scope lives in the '
                'gate blocks and the surface column instead of per-row progress')
        elif advanced < len(rows):
            # Keep the remainder visible: rows still at triage are not a blocker, but the count must not
            # quietly disappear from the report.
            add('low', 'ledger',
                f'{len(rows) - advanced} rows remain at their triage status (per-gate delivered scope and '
                'the surface column carry the detail; advancing them row-by-row is recorded in the '
                'adversarial review as a freeze-time task)')
        if len(rows) != 200:
            add('high', 'ledger', f'ledger holds {len(rows)} rows, expected 200')

    # 4. Evidence coverage -------------------------------------------------------------------------
    matrix = ROOT / 'docs' / 'v1.4' / 'KEL_V1.4_VISUAL_ACCEPTANCE_MATRIX.md'
    captures = ROOT / 'docs' / 'v1.4' / 'screenshots'
    if matrix.exists():
        text = matrix.read_text(encoding='utf-8')
        surfaces = [line for line in text.splitlines() if line.startswith('| ') and '| G' in line]
        add('info', 'evidence',
            f'{len(surfaces)} acceptance-matrix rows; {len(list(captures.glob("*/*.png")))} capture files on disk')

    # 5. Packaged-app contract ---------------------------------------------------------------------
    allowlist = sh(
        "grep -c 'api' desktop/packages/desktop/src/process/services/kel/KelService.ts"
    )
    if not allowlist or int(allowlist) == 0:
        add('high', 'packaged-contract', 'the Kel route allowlist is missing from KelService.ts')

    v14_routes = []
    for route in ('brief', 'team', 'providers', 'autonomy', 'diagnostics'):
        if sh(f"grep -c \"{route}\" desktop/packages/desktop/src/process/services/kel/KelService.ts") not in ('', '0'):
            v14_routes.append(route)
    missing = [r for r in ('brief', 'team', 'providers', 'autonomy', 'diagnostics') if r not in v14_routes]
    if missing:
        add('high', 'packaged-contract', f'engine routes not allowlisted for the renderer: {missing}')

    if not (ROOT / 'desktop' / 'packages' / 'desktop' / 'src' / 'process' / 'services' / 'kel'
            / 'kelCredentials.ts').exists():
        add('high', 'packaged-contract', 'credential custody module is missing')

    # 6. Unused lazy imports (known G9 carry-over) -------------------------------------------------
    router = ROOT / 'desktop' / 'packages' / 'desktop' / 'src' / 'renderer' / 'components' / 'layout' / 'Router.tsx'
    if router.exists():
        text = router.read_text(encoding='utf-8')
        unused = [name for name in re.findall(r'const (\w+) = React\.lazy', text)
                  if len(re.findall(rf'\b{name}\b', text)) == 1]
        if unused:
            add('low', 'dead-code', f'declared but unused lazy imports: {unused}')

    return findings


def main():
    findings = run_checks()
    blocking = [f for f in findings if f['severity'] in ('high', 'medium')]
    if '--json' in sys.argv:
        print(json.dumps({'findings': findings, 'blocking': len(blocking)}, indent=2))
    else:
        print('KEL V1.4 ADVERSARIAL SWEEP')
        print('=' * 60)
        for finding in findings:
            line = f"[{finding['severity'].upper():6}] {finding['area']}: {finding['detail']}"
            print(line)
            if finding['evidence']:
                print(f"         {finding['evidence']}")
        print('-' * 60)
        print(f"findings: {len(findings)} | blocking (high+medium): {len(blocking)}")
    return 1 if blocking else 0


if __name__ == '__main__':
    sys.exit(main())
