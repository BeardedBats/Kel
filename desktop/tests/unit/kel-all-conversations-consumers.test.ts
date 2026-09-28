import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

// Real chats never use the engine's hidden 'main' conversation (D-53), so every surface that
// summarizes work must read the all-conversations scope or it silently shows nothing.
const RENDERER = join(__dirname, '../../packages/desktop/src/renderer');
const CONSUMERS = [
  'pages/kel/activity/index.tsx',
  'pages/kel/autonomy/index.tsx',
  'components/kel/KelCommandPalette.tsx',
  'pages/guid/components/KelResumptionBrief.tsx',
  'hooks/system/notification/useKelAttentionNotification.ts',
];

describe('work summary surfaces read every conversation', () => {
  // D-54: Activity also passes the active project (`kelState(KEL_ALL_CONVERSATIONS, active)`).
  it.each(CONSUMERS)('%s uses kelState(KEL_ALL_CONVERSATIONS)', (file) => {
    const source = readFileSync(join(RENDERER, file), 'utf8');
    expect(source).toMatch(/kelState\(KEL_ALL_CONVERSATIONS[,)]/);
    expect(source).not.toMatch(/kelState\(\)/);
  });
});
