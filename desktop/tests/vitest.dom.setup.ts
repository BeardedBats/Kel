/**
 * jsdom-lane vitest setup: the counterpart of vitest.setup.ts for `*.dom.test.ts(x)`.
 *
 * The in-thread hand-off card and line remember each hand-off across re-renders (FIX-0025); tests
 * reuse submission ids, so that memory is cleared after every test. The module has no dependencies,
 * so importing it here never pre-loads anything a test mocks.
 */
import { afterEach } from 'vitest';
import { resetHandoffMemory } from '../packages/desktop/src/renderer/components/kel/workCards/handoffMemory';

afterEach(() => resetHandoffMemory());
