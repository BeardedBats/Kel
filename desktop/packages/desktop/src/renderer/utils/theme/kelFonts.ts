/**
 * Kel: local UI fonts — Söhne for headers, SF Pro Text for body.
 *
 * The font files live in `desktop/public/fonts/` and are intentionally NOT
 * committed (licensed fonts; see `desktop/public/fonts/README.md`). They are
 * registered here with the FontFace API at runtime so a checkout without the
 * files still builds and runs — the CSS fallback stack simply applies.
 *
 * URLs resolve against the document base, which works in dev
 * (http://localhost:5173/) and in the packaged app (file://…/out/renderer/)
 * alike; files inside app.asar are read transparently by Electron.
 */
const DISPLAY_FAMILY = 'Sohne';
const TEXT_FAMILY = 'SF Pro Text';

const DISPLAY_FILES: ReadonlyArray<[file: string, weight: number]> = [
  ['sohne/Sohne-Buch.otf', 400],
  ['sohne/Sohne-Kraftig.otf', 500],
  ['sohne/Sohne-Halbfett.otf', 600],
  ['sohne/Sohne-Dreiviertelfett.otf', 700],
];

const TEXT_FILES: ReadonlyArray<[file: string, weight: number]> = [
  ['sf-pro-text/SF-Pro-Text-Regular.otf', 400],
  ['sf-pro-text/SF-Pro-Text-Medium.otf', 500],
  ['sf-pro-text/SF-Pro-Text-Semibold.otf', 600],
  ['sf-pro-text/SF-Pro-Text-Bold.otf', 700],
];

let started = false;

export function loadKelFonts(root: Document = document): void {
  if (started || typeof FontFace === 'undefined' || !root.fonts) return;
  started = true;
  const register = (family: string, files: ReadonlyArray<[string, number]>): void => {
    for (const [file, weight] of files) {
      const url = new URL(`./fonts/${file}`, root.baseURI).href;
      const face = new FontFace(family, `url(${url})`, {
        weight: String(weight),
        style: 'normal',
        display: 'swap',
      });
      face
        .load()
        .then((loaded) => root.fonts.add(loaded))
        .catch(() => {
          /* Font files are local-only: when absent the CSS fallback stack applies. */
        });
    }
  };
  register(DISPLAY_FAMILY, DISPLAY_FILES);
  register('Instrument Sans', [
    ['instrument-sans/InstrumentSans.ttf', 400],
    ['instrument-sans/InstrumentSans.ttf', 500],
    ['instrument-sans/InstrumentSans.ttf', 600],
    ['instrument-sans/InstrumentSans.ttf', 700],
  ]);
  register(TEXT_FAMILY, TEXT_FILES);
}
