"""Requested image output is a real captured asset, never a description or model claim."""
import contextlib
import hashlib
import struct
import zlib
from pathlib import Path
from .core import PolicyError

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 16 * 1024 * 1024


def requires_image(contract, milestone_id=None):
    from .router import image_generation_intent
    explicit = contract.get('output_contract') or {}
    requested = contract.get('kind') == 'image' or (isinstance(explicit, dict) and explicit.get('kind') == 'image') or image_generation_intent(contract.get('request', ''))
    if not requested:
        return False
    final = contract.get('final_milestone')
    return not final or milestone_id is None or final == milestone_id


def ensure_image_schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS image_receipts('
               'run_id TEXT PRIMARY KEY,job_id TEXT NOT NULL,milestone_id TEXT NOT NULL,'
               'path TEXT NOT NULL,sha256 TEXT NOT NULL,bytes INTEGER NOT NULL,'
               'media_type TEXT NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL,'
               'provider TEXT NOT NULL,model TEXT,created REAL NOT NULL)')


def validate_png(raw):
    """Decode bounded normalized RGB/RGBA PNG scanlines and check all chunk CRCs.

    Desktop capture normalizes through Electron nativeImage first. Palette, interlaced and other
    formats fail closed rather than relying on filename/header guesses or a missing decoder.
    """
    if not isinstance(raw, bytes) or not 45 <= len(raw) <= MAX_IMAGE_BYTES or raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise PolicyError('The generated image is not a bounded PNG file.')
    pos, width, height, channels = 8, None, None, None
    data = bytearray()
    ended = False
    data_ended = False
    while pos < len(raw):
        if pos + 12 > len(raw):
            raise PolicyError('The generated image has a truncated PNG chunk.')
        size = struct.unpack('>I', raw[pos:pos+4])[0]
        kind = raw[pos+4:pos+8]
        if not all(65 <= value <= 90 or 97 <= value <= 122 for value in kind):
            raise PolicyError('The generated image has an invalid PNG chunk name.')
        stop = pos + 12 + size
        if stop > len(raw):
            raise PolicyError('The generated image has a truncated PNG chunk.')
        value = raw[pos+8:pos+8+size]
        crc = struct.unpack('>I', raw[pos+8+size:stop])[0]
        if zlib.crc32(kind + value) & 0xffffffff != crc:
            raise PolicyError('The generated image has a corrupt PNG chunk.')
        if width is None and kind != b'IHDR':
            raise PolicyError('The generated image is missing its PNG header.')
        if kind == b'IHDR':
            if width is not None or size != 13:
                raise PolicyError('The generated image has an invalid PNG header.')
            width, height, bits, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', value)
            if not width or not height or width > 8192 or height > 8192 or width * height > MAX_IMAGE_PIXELS:
                raise PolicyError('The generated image exceeds its pixel limit.')
            if bits != 8 or color not in (2, 6) or compression or filtering or interlace:
                raise PolicyError('The image must be normalized to a non-interlaced RGB/RGBA PNG.')
            channels = 3 if color == 2 else 4
        elif kind == b'IDAT':
            if data_ended:
                raise PolicyError('The generated image has separated PNG data chunks.')
            data.extend(value)
        elif kind == b'IEND':
            if size or not data or stop != len(raw):
                raise PolicyError('The generated image has an invalid PNG end marker.')
            ended = True
        elif kind == b'PLTE':
            if not size or size % 3 or size > 768 or data:
                raise PolicyError('The generated image has an invalid palette chunk.')
        elif kind[0] & 32 == 0:
            raise PolicyError('The generated image uses an unsupported critical PNG chunk.')
        if data and kind != b'IDAT':
            data_ended = True
        pos = stop
    if not ended:
        raise PolicyError('The generated image is incomplete.')
    stride = width * channels + 1
    expected = stride * height
    decoder = zlib.decompressobj()
    try:
        decoded = decoder.decompress(bytes(data), expected + 1)
    except zlib.error:
        raise PolicyError('The generated image data does not decode.') from None
    if len(decoded) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise PolicyError('The generated image data has an invalid decoded size.')
    if any(decoded[row * stride] > 4 for row in range(height)):
        raise PolicyError('The generated image has an invalid scanline filter.')
    return {'width': width, 'height': height}


def _receipt(db, job_id, milestone_id, run_id):
    ensure_image_schema(db)
    row = db.execute('SELECT * FROM image_receipts WHERE run_id=? AND job_id=? AND milestone_id=?',
                     (run_id, job_id, milestone_id)).fetchone()
    return dict(row) if row else None


def receipt_artifact(store, receipt):
    if not receipt or receipt.get('media_type') != 'image/png' or not receipt.get('provider'):
        raise PolicyError('No trusted generated image receipt was recorded.')
    relative = receipt.get('path')
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise PolicyError('The generated image has an untrusted artifact path.')
    path = (store.root / relative).resolve()
    if not path.is_relative_to((store.root / 'artifacts').resolve()) or not path.is_file():
        raise PolicyError('The generated image file is missing or escaped its artifact root.')
    size = path.stat().st_size
    if not 45 <= size <= MAX_IMAGE_BYTES or size != receipt.get('bytes'):
        raise PolicyError('The generated image size changed or exceeds its limit.')
    with path.open('rb') as stream:
        raw = stream.read(MAX_IMAGE_BYTES + 1)
    if len(raw) != size:
        raise PolicyError('The generated image changed while it was read.')
    if hashlib.sha256(raw).hexdigest() != receipt.get('sha256'):
        raise PolicyError('The generated image changed after capture.')
    dimensions = validate_png(raw)
    if dimensions != {'width': receipt.get('width'), 'height': receipt.get('height')}:
        raise PolicyError('The generated image dimensions do not match its receipt.')
    return {key: receipt[key] for key in ('path', 'sha256', 'bytes', 'job_id', 'milestone_id',
                                         'run_id', 'media_type', 'width', 'height', 'provider', 'model')}


def accept_image_result(store, job, run, result, db):
    """Only a server-persisted, run-bound receipt can capture an image result."""
    if result.get('outcome') != 'SUCCESS':
        return None
    receipt = _receipt(db, job['id'], run['milestone_id'], run['id'])
    if not receipt:
        return None
    return receipt_artifact(store, receipt)


def image_check(store, job, milestone_id, *, db=None):
    if not requires_image(job['contract'], milestone_id):
        return None
    if db is None:
        with contextlib.closing(store.connect()) as connection:
            return image_check(store, job, milestone_id, db=connection)
    artifact = (job.get('milestones', {}).get(milestone_id) or {}).get('artifact') or {}
    try:
        receipt = _receipt(db, job['id'], milestone_id, artifact.get('run_id'))
        captured = receipt_artifact(store, receipt)
        if any(artifact.get(key) != captured.get(key) for key in ('path', 'sha256', 'bytes', 'run_id', 'job_id', 'milestone_id', 'media_type')):
            raise PolicyError('The generated image is not this milestone’s captured output.')
        return {'kind': 'requested_image_output', 'verdict': 'VERIFIED',
                'subject': captured['sha256'], 'receipt_run': captured['run_id'],
                'width': captured['width'], 'height': captured['height'],
                'visual_review': 'not_performed'}
    except (OSError, ValueError, KeyError, TypeError, PolicyError) as exc:
        return {'kind': 'requested_image_output', 'verdict': 'FAILED',
                'reason': str(exc), 'failure': 'missing_image_output'}


def display_image(store, job, milestone_id, *, db=None):
    checked = image_check(store, job, milestone_id, db=db)
    if not checked or checked['verdict'] != 'VERIFIED':
        raise PolicyError('No checked generated image is available to show.')
    return '![Generated image](kel-image://%s/%s)' % (job['id'], milestone_id)
