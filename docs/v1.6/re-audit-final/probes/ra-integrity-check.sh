#!/usr/bin/env bash
# Final re-audit integrity check: frozen refs + sibling worktree immutability.
set -u
cd "/c/Users/Nick/Desktop/Kel/kel-v16-final-repair" || exit 1

echo "=== FROZEN TAG OBJECTS ==="
for t in v1.2.0 v1.3.0 v1.4.0 v1.4.1 v1.5.0 v1.6.0-pre1; do
  obj=$(git rev-parse "$t^{tag}" 2>/dev/null || echo "-")
  com=$(git rev-parse "$t^{}" 2>/dev/null || echo "-")
  echo "$t tagobj=$obj commit=$com"
done

echo ""
echo "=== RC WORKTREE (kel-ux-v15) ==="
git -C "/c/Users/Nick/Desktop/Kel/kel-ux-v15" rev-parse HEAD
git -C "/c/Users/Nick/Desktop/Kel/kel-ux-v15" status --short | head -8

echo ""
echo "=== CAMPAIGN B AUDIT WORKTREE ==="
git -C "/c/Users/Nick/Desktop/Kel/kel-v16-final-audit" rev-parse HEAD
git -C "/c/Users/Nick/Desktop/Kel/kel-v16-final-audit" status --short | head -12

echo ""
echo "=== MAIN WORKTREE ==="
git -C "/c/Users/Nick/Desktop/Kel/Kel-Repo" rev-parse HEAD
git -C "/c/Users/Nick/Desktop/Kel/Kel-Repo" status --short | head -8

echo ""
echo "=== REPAIR WORKTREE ==="
git -C "/c/Users/Nick/Desktop/Kel/kel-v16-final-repair" rev-parse HEAD
git -C "/c/Users/Nick/Desktop/Kel/kel-v16-final-repair" status --short | head -8

echo ""
echo "=== VISUAL WORKTREES ==="
git -C "/c/Users/Nick/Desktop/Kel/kel-v16-visual-fix" rev-parse HEAD
git -C "/c/Users/Nick/Desktop/Kel/kel-v16-visual-audit" rev-parse HEAD
