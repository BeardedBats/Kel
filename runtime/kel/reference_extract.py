"""Local, bounded extraction of selected PDF/image reference bytes.

Extracted text is source material, never a command. Original files stay in the
reference receipt store; this module receives no user path or URL.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

MAX_BYTES = 5_000_000
MAX_TEXT = 30_000
MAX_PAGES = 20
_slot = threading.BoundedSemaphore(1)


def _kind(name, raw):
    if not isinstance(name, str) or not name.strip() or len(name) > 200 or any(c in name for c in '/\\\x00'):
        raise ValueError('Choose a reference file with a short filename.')
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError('Each PDF or image can contain at most 5 MB.')
    ext = Path(name).suffix.lower()
    if ext == '.pdf' and raw.startswith(b'%PDF-'):
        return 'pdf'
    if ((ext == '.png' and raw.startswith(b'\x89PNG\r\n\x1a\n'))
            or (ext in ('.jpg', '.jpeg') and raw.startswith(b'\xff\xd8\xff'))
            or (ext == '.gif' and raw[:6] in (b'GIF87a', b'GIF89a'))
            or (ext == '.webp' and raw.startswith(b'RIFF') and raw[8:12] == b'WEBP')):
        return 'image'
    raise ValueError('Choose a PDF, PNG, JPEG, GIF or WebP file with matching content.')


def _pdf(raw, *, allow_ocr=False):
    from pypdf import PdfReader
    logging.getLogger('pypdf').setLevel(logging.CRITICAL)
    reader = PdfReader(io.BytesIO(raw), strict=True)
    if reader.is_encrypted:
        raise ValueError('Choose a PDF without password protection.')
    if not 0 < len(reader.pages) <= MAX_PAGES:
        raise ValueError('Choose a PDF with at most 20 pages.')
    text = []
    size = 0
    missing = []
    for page in reader.pages:
        content = page.get_contents()
        if content is not None and len(content.get_data()) > 8_000_000:
            raise ValueError('This PDF page is too large to extract safely.')
        part = page.extract_text() or ''
        if not part.strip():
            missing.append(len(text))
        size += len(part) + (2 if text else 0)
        if size > MAX_TEXT:
            raise ValueError('Extracted reference text can contain at most 30,000 characters.')
        text.append(part.strip())
    if missing:
        if not allow_ocr:
            raise ValueError('This PDF has a page without readable text. Add its text or a page image for OCR.')
        return {'needs_ocr': True, 'page_texts': text, 'missing_pages': missing, 'pages': len(text)}
    return {'text': '\n\n'.join(text), 'kind': 'pdf', 'extraction': 'pdf-text', 'pages': len(reader.pages)}


def worker_main():
    """Fixed child entry. A Windows Job limits memory and process lifetime."""
    if os.name != 'nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    try:
        payload = json.loads(sys.stdin.buffer.read(7_000_001))
        raw = base64.b64decode(payload['content'], validate=True)
        if _kind(payload['name'], raw) != 'pdf':
            raise ValueError('The PDF worker accepts PDF bytes only.')
        result = _pdf(raw, allow_ocr=True)
        sys.stdout.write(json.dumps(result, ensure_ascii=True))
        return 0
    except ValueError as error:
        # Only our explicitly authored errors are safe to expose.
        message = str(error) if str(error).startswith(('Choose ', 'This PDF ', 'Extracted reference ')) else 'Kel could not read this PDF. Choose another file or add its text.'
    except Exception:
        message = 'Kel could not read this PDF. Choose another file or add its text.'
    sys.stdout.write(json.dumps({'error': message}))
    return 1


def _bounded_worker(command, payload, *, timeout=20, allow_ocr=False):
    if timeout <= 0:
        raise ValueError('Reading this reference timed out. Choose a smaller file or add its text.')
    deadline = time.monotonic() + timeout
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    close_job = None
    try:
        if os.name == 'nt':
            from .windows_job import bound_child_process
            close_job = bound_child_process(process)
        # No untrusted input is sent until the Windows memory/lifetime limit exists.
        output = []
        failures = []
        def read_output():
            try:
                block = process.stdout.read(200_001)
                output.append(block)
                if len(block) > 200_000 and process.poll() is None:
                    process.kill()
            except OSError:
                failures.append(True)
        def send_input():
            try:
                process.stdin.write(json.dumps(payload, ensure_ascii=True).encode('utf-8'))
                process.stdin.close()
            except (OSError, ValueError):
                failures.append(True)
        reader = threading.Thread(target=read_output, daemon=True)
        writer = threading.Thread(target=send_input, daemon=True)
        reader.start(); writer.start()
        try:
            process.wait(timeout=max(0, deadline-time.monotonic()))
        except subprocess.TimeoutExpired:
            raise ValueError('Reading this reference timed out. Choose a smaller file or add its text.')
        reader.join(timeout=2); writer.join(timeout=2)
        stdout = output[0] if output else b''
        if len(stdout) > 200_000:
            raise ValueError('Kel could not read this reference within its text limit.')
        if failures or reader.is_alive() or writer.is_alive():
            raise ValueError('Kel could not finish reading this reference.')
        try:
            result = json.loads(stdout.decode('utf-8'))
        except (ValueError, UnicodeError):
            raise ValueError('Kel could not read this reference. Choose another file or add its text.') from None
        if not isinstance(result, dict):
            raise ValueError('Kel could not read this reference.')
        if process.returncode:
            error = result.get('error')
            raise ValueError(error if isinstance(error, str) and len(error) <= 250 else 'Kel could not read this reference.')
        if allow_ocr and result.get('needs_ocr') is True:
            parts, missing, pages = result.get('page_texts'), result.get('missing_pages'), result.get('pages')
            if (set(result) != {'needs_ocr', 'page_texts', 'missing_pages', 'pages'} or
                    type(pages) is not int or not 1 <= pages <= MAX_PAGES or
                    not isinstance(parts, list) or len(parts) != pages or
                    any(not isinstance(part, str) for part in parts) or
                    len('\n\n'.join(parts)) > MAX_TEXT or not isinstance(missing, list) or not missing or
                    any(type(index) is not int for index in missing) or
                    missing != [index for index, part in enumerate(parts) if not part.strip()]):
                raise ValueError('Kel could not validate the PDF pages for local OCR.')
            return result
        text = result.get('text')
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
            raise ValueError('No bounded readable text was found. Add the text instead.')
        return result
    finally:
        if close_job:
            close_job()
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        finally:
            for stream in (process.stdin, process.stdout):
                if stream:
                    stream.close()


def extract_reference(name, raw):
    kind = _kind(name, raw)
    if not _slot.acquire(blocking=False):
        raise ValueError('Kel is reading another reference. Try this file again shortly.')
    try:
        deadline = time.monotonic() + 20
        payload = {'name': name, 'content': base64.b64encode(raw).decode('ascii')}
        if kind == 'pdf':
            command = [sys.executable, '--reference-extract-worker'] if getattr(sys, 'frozen', False) else [sys.executable, '-B', str(Path(__file__).resolve().parents[1] / 'kel_backend_entry.py'), '--reference-extract-worker']
        else:
            if os.name != 'nt':
                raise ValueError('Local image text extraction requires Windows. Add the image text instead.')
            system_root = os.environ.get('SystemRoot', r'C:\Windows')
            command = [str(Path(system_root) / 'System32/WindowsPowerShell/v1.0/powershell.exe'), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(Path(__file__).with_name('reference_ocr.ps1'))]
        result = _bounded_worker(command, payload, timeout=deadline-time.monotonic(), allow_ocr=kind == 'pdf')
        if result.get('needs_ocr') is True:
            if os.name != 'nt':
                raise ValueError('Local scanned PDF text extraction requires Windows. Add the PDF text instead.')
            system_root = os.environ.get('SystemRoot', r'C:\Windows')
            command = [str(Path(system_root) / 'System32/WindowsPowerShell/v1.0/powershell.exe'), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(Path(__file__).with_name('reference_pdf_ocr.ps1'))]
            payload.update(page_texts=result['page_texts'], missing_pages=result['missing_pages'], pages=result['pages'])
            result = _bounded_worker(command, payload, timeout=deadline-time.monotonic())
            if (result.get('extraction') != 'pdf-ocr' or type(result.get('pages')) is not int or
                    result['pages'] != payload['pages'] or not isinstance(result.get('language'), str)):
                raise ValueError('Kel could not validate the scanned PDF text.')
        result['kind'] = kind
        if kind == 'image':
            result['extraction'] = 'image-ocr'
        return result
    except OSError:
        raise ValueError('Kel could not start bounded local extraction. Add the reference text instead.') from None
    finally:
        _slot.release()
