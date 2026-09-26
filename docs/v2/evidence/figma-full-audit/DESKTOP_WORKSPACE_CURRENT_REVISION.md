# Desktop Workspace and File preview — current Figma

The current [Workspace panel `273:13249`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=273-13249) and [File preview `273:13459`](https://www.figma.com/design/BlpVvZGuc9j9HhxUojIiJI/Kel-Design-System?node-id=273-13459) were read directly and implemented together.

## Source and render verification

Workspace measures 340px at 1440px and contracts to 260px at 800px. Its rows measure 28px. Original folder/file/header assets render at 14px; chevrons render at 12px. The surface blends blue at 5% with the dark glass layer at 40%. The neutral structural edge uses 12% opacity. Files and Changes use 28px controls. Warm text and a subtle full fill replace the prohibited single-side selected-tab underline.

The actual disposable project contains three changed files. Its Git state supplies Changes · 3 and warm file labels. Search returns two actual hero files at both widths. Refresh, close/reopen, Collapse all, and the selected-file state pass. Add folder uses the existing native dialog bridge with an injected canceled result; no folder was attached. Terminal and File Explorer requests carry the actual disposable folder. Those requests were intercepted, so physical OS tool launch remains unverified. Open with still exposes VS Code and Browser.

File preview's outer region measures 560px at 1440px; its inner surface measures 559px after the structural border. At 800px the outer region measures 340px. Three real text files exercise the tab bar and actual content API. Tabs measure 34px. Original file and close assets render at 13px and 12px. The code surface uses a 10px radius, a full neutral border, and 12px/14px padding. The toolbar uses 10px/14px padding. CodeMirror retains syntax highlighting and editing behavior. Preview is read-only; Code enables editing; split view mounts both. File details show the actual relative path, line count, and unsaved state. The app does not invent "edited by Kel" attribution.

Add to chat produces the actual project-file attachment in the active chat. Show in folder addresses the file by project root and relative path; its OS request was intercepted. A real save reached the disposable file. The editor restored its content, then cleanup restored the original bytes. The existing editor normalizes saved CRLF text to LF. This is an existing save behavior, not byte-preserving round-trip proof. No chat was submitted.

Both views have zero document overflow and renderer errors. Checks also compare pane edges and composer button bounds; hidden clipping is not accepted as a pass. The narrow composer wraps its input and retains Send. Workspace stays mounted when temporarily hidden for a narrow preview. The native Windows titlebar requires 28px more top space than the frameless Figma samples. Saved panel widths remain supported. Fixture filenames and sorted roots reflect actual files rather than Figma's illustrative project.

TypeScript and source build pass. The full desktop suite passed 414 tests across 57 files before the final tab keyboard adjustment; the final focused Workspace/File controls passed 7 tests. Final package verification is pending. Canonical App still packages `8c67121`; App and durable Data are untouched. Mobile remains paused.
