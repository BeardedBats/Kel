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
import { desktopPanelPlacement, panelPlacement } from './captureTarget';
import recordingDot from '@renderer/assets/figma/fix-capture/recording-dot.svg';
import { useFixCapture } from './useFixCapture';
import styles from './fixCapture.module.css';

const PANEL_SIZE = { width: 340, height: 250 };
const ACTIVE_PHASES = new Set(['recording', 'stopping', 'review', 'saving']);
const captureElement = (element: Element | null): Element | null =>
  element?.closest('button, a, input, textarea, select, [role="button"]') || element;

const rectOf = (element: Element | null): Rect | null => {
  if (!element?.getBoundingClientRect) return null;
  const box = element.getBoundingClientRect();
  if (box.width < 2 || box.height < 2) return null;
  return { x: box.left, y: box.top, width: box.width, height: box.height };
};

const clock = (seconds: number): string =>
  `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;

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
  const { state, begin, cancel, stop, again, retry, save, dismiss, setDraft } = capture;
  const phase = state.phase;
  const phaseRef = useRef(phase);
  phaseRef.current = phase;
  const [hover, setHover] = useState<Rect | null>(null);
  const [hoverLabel, setHoverLabel] = useState('');
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [viewport, setViewport] = useState({ width: window.innerWidth, height: window.innerHeight });
  const desktop = viewport.width >= 768;
  const [panelHeight, setPanelHeight] = useState(PANEL_SIZE.height);
  useEffect(() => {
    const resize = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);
  useEffect(() => {
    if (!desktop || phase === 'idle' || phase === 'saved') return;
    document.body.dataset.kelFixCapture = 'active';
    return () => { delete document.body.dataset.kelFixCapture; };
  }, [desktop, phase]);
  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    setPanelHeight(panel.getBoundingClientRect().height);
    if (typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => setPanelHeight(panel.getBoundingClientRect().height));
    observer.observe(panel);
    return () => observer.disconnect();
  }, [phase]);

  // Ctrl+Shift+F begins a capture, or stops one that is recording; Esc always cancels.
  //
  // The chord is deliberately claimed in the CAPTURE phase: the donor's conversation-search modal
  // also binds Ctrl+Shift+F (a document-capture listener that preventDefaults and opens the search).
  // Fix Capture is the primary consumer of this chord now, so it stops the event before the search
  // handler sees it; search keeps its own trigger and the Ctrl+K palette path. Documented in
  // KNOWN_LIMITATIONS and pinned by `fix-capture.dom.test.ts`.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (isPrimaryApplicationShortcut(event, { key: 'f', shiftKey: true, targetGuard: 'embedded-editor' })) {
        event.preventDefault();
        event.stopPropagation();
        if (phaseRef.current === 'idle') api.current.begin();
        else if (phaseRef.current === 'recording') api.current.stop();
        return;
      }
      if (event.key === 'Escape' && phaseRef.current !== 'idle' && phaseRef.current !== 'saved') {
        event.preventDefault();
        api.current.cancel();
      }
    };
    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, []);

  // Selecting: the overlay is transparent, so hit-testing finds the real element underneath and the
  // click is swallowed before the app below can act on it.
  useEffect(() => {
    if (phase !== 'selecting') {
      setHover(null);
      return;
    }
    const onMove = (event: MouseEvent) => {
      const element = captureElement(document.elementFromPoint(event.clientX, event.clientY));
      setHover(rectOf(element));
      setHoverLabel(element?.getAttribute('aria-label') || element?.textContent?.trim().slice(0, 90) || element?.tagName.toLowerCase() || '');
    };
    const onClick = (event: MouseEvent) => {
      // The overlay is transparent to the pointer, so the event target is the element the person
      // clicked; elementFromPoint stays as a fallback for synthetic events.
      const element = captureElement(
        (event.target instanceof Element ? event.target : null) ??
        document.elementFromPoint(event.clientX, event.clientY));
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
    ? (desktop ? desktopPanelPlacement : panelPlacement)(
        state.target.rect,
        viewport,
        { width: desktop ? (phase === 'recording' || phase === 'stopping' ? 380 : 420) : PANEL_SIZE.width, height: panelHeight },
        desktop ? (phase === 'recording' || phase === 'stopping' ? 51 : 90) : 12
      )
    : null;
  const targetLabel = state.target?.label || state.target?.text || state.target?.tag || '';

  return (
    <>
      {(phase === 'selecting' || (desktop && ACTIVE_PHASES.has(phase))) &&
        createPortal(
          <div className={styles.overlay} aria-hidden data-testid='fix-capture-overlay'>
            {(hover || state.target?.rect) && (
              <div
                className={styles.highlight}
                style={{ top: (hover || state.target!.rect).y - (desktop ? 6 : 0), left: (hover || state.target!.rect).x - (desktop ? 6 : 0), width: (hover || state.target!.rect).width + (desktop ? 12 : 0), height: (hover || state.target!.rect).height + (desktop ? 12 : 0) }}
              />
            )}
            {phase === 'selecting' && <div className={styles.hint}>Click the part of Kel that bothers you. Esc cancels.</div>}
            {phase === 'selecting' && desktop && hover && hoverLabel && <div className={styles.targetLabel} style={{ top: Math.max(4, hover.y - 29), left: Math.max(8, Math.min(hover.x - 19, viewport.width - 200)) }}>{hoverLabel}</div>}
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
            aria-label='Kibble'
            data-testid='fix-capture-panel'
            data-phase={phase}
          >
            {phase === 'recording' || phase === 'stopping' ? (
              <>
                <div className={styles.head}>
                  {desktop && <img src={recordingDot} alt='' />}
                  <p className={styles.heading}>{phase === 'recording' ? (desktop ? 'Recording' : 'Recording fix…') : 'Finishing the transcript…'}</p>
                  <p className={styles.timer}>{clock(state.seconds)}</p>
                </div>
                <div className={styles.liveBox}>
                  {desktop && <p className={styles.liveLabel}>{phase === 'recording' ? 'Listening' : 'Transcribing'}</p>}
                  <p className={styles.live} data-testid='fix-capture-live'>{state.live || (phase === 'recording' ? 'Listening…' : 'One moment…')}</p>
                </div>
                {targetLabel && <p className={styles.target}>on “{targetLabel}”</p>}
                <div className={styles.actions}>
                  <button type='button' className={styles.quiet} onClick={() => cancel()}>
                    Cancel
                  </button>
                  <button
                    type='button'
                    className={`${styles.primary} ${styles.stop}`}
                    onClick={() => stop()}
                    disabled={phase !== 'recording'}
                    data-testid='fix-capture-stop'
                  >
                    Stop
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
                    Open Kibble
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className={styles.head}>
                  <p className={styles.heading}>What went wrong?</p>
                  {desktop && <p className={styles.timer}>{clock(state.seconds)}</p>}
                </div>
                {targetLabel && <p className={styles.target}>on “{targetLabel}”</p>}
                <textarea
                  className={styles.transcript}
                  value={state.draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder='Say or type what bothers you about this part of Kel.'
                  rows={4}
                  data-testid='fix-capture-transcript'
                />
                {desktop && <p className={styles.note}>Kel saves the screenshot, the spot you clicked and this note.</p>}
                {state.note && (
                  <p
                    className={state.retryable ? styles.noteStrong : styles.note}
                    data-testid='fix-capture-note'
                  >
                    {state.note}
                  </p>
                )}
                <div className={styles.actions}>
                  <button
                    type='button'
                    className={`${styles.secondary} ${styles.again}`}
                    onClick={() => again()}
                    data-testid='fix-capture-again'
                  >
                    Record Again
                  </button>
                  {(state.retryable || desktop) && (
                    <button
                      type='button'
                      className={`${styles.secondary} ${styles.retry}`}
                      onClick={() => void retry()}
                      disabled={!state.retryable}
                      data-testid='fix-capture-retry'
                    >
                      {desktop ? 'Retry transcription' : 'Retry Transcription'}
                    </button>
                  )}
                  <button
                    type='button'
                    className={`${styles.primary} ${styles.save}`}
                    onClick={() => void save()}
                    disabled={!state.draft.trim()}
                    data-testid='fix-capture-save'
                  >
                    {desktop ? 'Save fix' : 'Save Fix'}
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
