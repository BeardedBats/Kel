/**
 * Fix Capture (V2.0 preflight) — the whole on-screen part of Ctrl+Shift+F.
 *
 * Mounted once by the shell so the hotkey works on every surface. Selecting never navigates and never
 * changes what is on screen: the overlay is transparent, the highlight is a rectangle, and the click
 * is captured before the app below can act on it.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useLocation, useNavigate } from 'react-router-dom';
import { isPrimaryApplicationShortcut } from '@renderer/utils/ui/keyboardShortcuts';
import type { Rect } from './captureTarget';
import { panelPlacement } from './captureTarget';
import { useFixCapture } from './useFixCapture';
import styles from './fixCapture.module.css';

const PANEL_SIZE = { width: 340, height: 250 };
const ACTIVE_PHASES = new Set(['recording', 'stopping', 'review', 'saving']);

const rectOf = (element: Element | null): Rect | null => {
  if (!element?.getBoundingClientRect) return null;
  const box = element.getBoundingClientRect();
  if (box.width < 2 || box.height < 2) return null;
  return { x: box.left, y: box.top, width: box.width, height: box.height };
};

const clock = (seconds: number): string =>
  `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;

const FixCaptureLayer: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const context = useCallback(
    () => ({
      route: location.pathname || null,
      pageTitle: typeof document === 'undefined' ? null : document.title || null,
      conversation: location.pathname.match(/^\/conversation\/([^/]+)/)?.[1] ?? null,
    }),
    [location.pathname]
  );
  const capture = useFixCapture(context);
  const api = useRef(capture);
  api.current = capture;
  const { state, begin, cancel, stop, again, save, dismiss, setDraft } = capture;
  const phase = state.phase;
  const phaseRef = useRef(phase);
  phaseRef.current = phase;
  const [hover, setHover] = useState<Rect | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  // Ctrl+Shift+F begins a capture, or stops one that is recording; Esc always cancels.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (isPrimaryApplicationShortcut(event, { key: 'f', shiftKey: true, targetGuard: 'embedded-editor' })) {
        event.preventDefault();
        if (phaseRef.current === 'idle') api.current.begin();
        else if (phaseRef.current === 'recording') api.current.stop();
        return;
      }
      if (event.key === 'Escape' && phaseRef.current !== 'idle' && phaseRef.current !== 'saved') {
        event.preventDefault();
        api.current.cancel();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  // Selecting: the overlay is transparent, so hit-testing finds the real element underneath and the
  // click is swallowed before the app below can act on it.
  useEffect(() => {
    if (phase !== 'selecting') {
      setHover(null);
      return;
    }
    const onMove = (event: MouseEvent) => {
      setHover(rectOf(document.elementFromPoint(event.clientX, event.clientY)));
    };
    const onClick = (event: MouseEvent) => {
      // The overlay is transparent to the pointer, so the event target is the element the person
      // clicked; elementFromPoint stays as a fallback for synthetic events.
      const element =
        (event.target instanceof Element ? event.target : null) ??
        document.elementFromPoint(event.clientX, event.clientY);
      if (!element) return;
      event.preventDefault();
      event.stopPropagation();
      void api.current.pick(element);
    };
    window.addEventListener('mousemove', onMove, true);
    window.addEventListener('click', onClick, true);
    // The overlay itself stays transparent to the pointer (hit-testing needs the real element), so
    // the cursor is set on the document for as long as selecting lasts.
    const previousCursor = document.documentElement.style.cursor;
    document.documentElement.style.cursor = 'crosshair';
    return () => {
      window.removeEventListener('mousemove', onMove, true);
      window.removeEventListener('click', onClick, true);
      document.documentElement.style.cursor = previousCursor;
    };
  }, [phase]);

  // While the panel is open: a click on the highlighted area stops the recording, and a click
  // anywhere else cancels — deliberately, and never as a save.
  useEffect(() => {
    if (!ACTIVE_PHASES.has(phase)) return;
    const onMouseDown = (event: MouseEvent) => {
      if (panelRef.current?.contains(event.target as Node)) return;
      if (phaseRef.current === 'saving') return;
      const target = api.current.state.target?.rect ?? null;
      // A meaningful target has area: a zero-size box can never be "the highlighted area".
      const inside =
        !!target &&
        target.width > 0 &&
        target.height > 0 &&
        event.clientX >= target.x &&
        event.clientX <= target.x + target.width &&
        event.clientY >= target.y &&
        event.clientY <= target.y + target.height;
      if (inside && phaseRef.current === 'recording') {
        event.preventDefault();
        event.stopPropagation();
        api.current.stop();
        return;
      }
      if (inside && phaseRef.current !== 'recording') return;
      event.preventDefault();
      event.stopPropagation();
      api.current.cancel();
    };
    window.addEventListener('mousedown', onMouseDown, true);
    return () => window.removeEventListener('mousedown', onMouseDown, true);
  }, [phase]);

  const placement = state.target
    ? panelPlacement(
        state.target.rect,
        { width: window.innerWidth, height: window.innerHeight },
        PANEL_SIZE
      )
    : null;
  const targetLabel = state.target?.label || state.target?.text || state.target?.tag || '';

  return (
    <>
      {phase === 'selecting' &&
        createPortal(
          <div className={styles.overlay} aria-hidden data-testid='fix-capture-overlay'>
            {hover && (
              <div
                className={styles.highlight}
                style={{ top: hover.y, left: hover.x, width: hover.width, height: hover.height }}
              />
            )}
            <div className={styles.hint}>Click the part of Kel that bothered you — Esc cancels</div>
          </div>,
          document.body
        )}

      {(ACTIVE_PHASES.has(phase) || phase === 'saved') &&
        placement &&
        createPortal(
          <div
            ref={panelRef}
            className={styles.panel}
            style={{ top: placement.top, left: placement.left }}
            role='dialog'
            aria-label='Fix Capture'
            data-testid='fix-capture-panel'
            data-phase={phase}
          >
            {phase === 'recording' || phase === 'stopping' ? (
              <>
                <p className={styles.heading}>
                  {phase === 'recording' ? 'Recording fix…' : 'Finishing the transcript…'}
                </p>
                <p className={styles.timer}>{clock(state.seconds)}</p>
                <p className={styles.live} data-testid='fix-capture-live'>
                  {state.live || (phase === 'recording' ? 'Listening…' : 'One moment…')}
                </p>
                {targetLabel && <p className={styles.target}>on “{targetLabel}”</p>}
                <div className={styles.actions}>
                  <button
                    type='button'
                    className={styles.primary}
                    onClick={() => stop()}
                    disabled={phase !== 'recording'}
                    data-testid='fix-capture-stop'
                  >
                    Stop
                  </button>
                  <button type='button' className={styles.quiet} onClick={() => cancel()}>
                    Cancel
                  </button>
                </div>
                <p className={styles.hintLine}>
                  Ctrl+Shift+F stops · clicking the highlighted area stops · Esc cancels
                </p>
              </>
            ) : phase === 'saving' ? (
              <p className={styles.heading}>Saving…</p>
            ) : phase === 'saved' ? (
              <>
                <p className={styles.heading}>Saved as {state.savedId}.</p>
                <div className={styles.actions}>
                  <button
                    type='button'
                    className={styles.primary}
                    onClick={() => {
                      dismiss();
                      navigate('/dogfood');
                    }}
                  >
                    Open Dogfood Fixes
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className={styles.heading}>What went wrong?</p>
                {targetLabel && <p className={styles.target}>on “{targetLabel}”</p>}
                <textarea
                  className={styles.transcript}
                  value={state.draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder='Say or type what bothers you about this part of Kel.'
                  rows={4}
                  data-testid='fix-capture-transcript'
                />
                {state.note && (
                  <p className={styles.note} data-testid='fix-capture-note'>
                    {state.note}
                  </p>
                )}
                <div className={styles.actions}>
                  <button
                    type='button'
                    className={styles.primary}
                    onClick={() => void save()}
                    disabled={!state.draft.trim()}
                    data-testid='fix-capture-save'
                  >
                    Save Fix
                  </button>
                  <button
                    type='button'
                    className={styles.secondary}
                    onClick={() => again()}
                    data-testid='fix-capture-again'
                  >
                    Record Again
                  </button>
                </div>
                <p className={styles.hintLine}>Esc or clicking outside cancels — nothing is saved</p>
              </>
            )}
          </div>,
          document.body
        )}
    </>
  );
};

export default FixCaptureLayer;
