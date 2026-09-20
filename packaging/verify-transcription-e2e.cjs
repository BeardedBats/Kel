/**
 * D4 — live transcription fixture flow against the real Kel engine HTTP service.
 *
 * Starts `python -m kel.service` on a throwaway data dir, reads the descriptor (url + token),
 * then drives the full transcription family over HTTP in the credential-free practice mode:
 * status → upload → live stream (start/chunk/status/finish) → save_recording → folders/rename/
 * assign → combine → exports → library → key set/clear. Writes machine-readable evidence to
 * docs/daily-driver/evidence/d4/transcription-e2e.json.
 *
 * Usage: node packaging/verify-transcription-e2e.cjs
 */
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const REPO = path.resolve(__dirname, '..');
const RUNTIME = path.join(REPO, 'runtime');
const OUT = path.join(REPO, 'docs', 'daily-driver', 'evidence', 'd4');
const PYTHON = process.env.KEL_PYTHON || 'python';

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function wavFixture(seconds, sampleRate = 24000) {
  const samples = Math.floor(seconds * sampleRate);
  const dataSize = samples * 2;
  const buffer = Buffer.alloc(44 + dataSize);
  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(36 + dataSize, 4);
  buffer.write('WAVE', 8);
  buffer.write('fmt ', 12);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write('data', 36);
  buffer.writeUInt32LE(dataSize, 40);
  for (let i = 0; i < samples; i += 1) {
    buffer.writeInt16LE(Math.round(Math.sin((i / sampleRate) * 2 * Math.PI * 220) * 12000), 44 + i * 2);
  }
  return buffer;
}

function pcmFixture(seconds, sampleRate = 24000) {
  const samples = Math.floor(seconds * sampleRate);
  const buffer = Buffer.alloc(samples * 2);
  for (let i = 0; i < samples; i += 1) {
    buffer.writeInt16LE(Math.round(Math.sin((i / sampleRate) * 2 * Math.PI * 180) * 9000), i * 2);
  }
  return buffer;
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'kel-d4-'));
  const results = { dataDir, checks: {}, startedAt: new Date().toISOString() };

  const child = spawn(PYTHON, ['-m', 'kel.service', '--data', dataDir], { cwd: RUNTIME, windowsHide: true });
  const logs = [];
  child.stdout.on('data', (data) => logs.push(data.toString('utf8')));
  child.stderr.on('data', (data) => logs.push(data.toString('utf8')));

  let descriptor = null;
  for (let attempt = 0; attempt < 120 && !descriptor; attempt += 1) {
    await wait(200);
    try {
      descriptor = JSON.parse(fs.readFileSync(path.join(dataDir, 'desktop-session.json'), 'utf8'));
    } catch {
      /* engine still starting */
    }
    if (child.exitCode !== null) break;
  }
  if (!descriptor) throw new Error('engine did not publish a descriptor: ' + logs.join('').slice(0, 400));

  const call = async (action, body = {}) => {
    const response = await fetch(descriptor.url.replace(/\/?$/, '/') + 'api/transcription', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: 'Bearer ' + descriptor.token },
      body: JSON.stringify({ action, ...body }),
    });
    const json = await response.json().catch(() => null);
    if (!response.ok) throw new Error(`${action} -> ${response.status} ${json && json.error}`.trim());
    return json;
  };

  try {
    // 1) honest mode reporting with no key present
    const status = await call('status');
    results.checks.status = {
      mode: status.mode,
      label: status.label,
      has_key: status.has_key,
      live_capable: status.live_capable,
      detail: status.detail,
    };

    // 2) upload a fixture wav -> deterministic practice transcript saved to the library
    const wav = wavFixture(4.2);
    const uploaded = await call('upload', {
      filename: 'd4-fixture.wav',
      audio: wav.toString('base64'),
      title: 'D4 fixture upload',
    });
    results.checks.upload = {
      id: uploaded.id,
      status: uploaded.status,
      has_audio: uploaded.has_audio,
      duration_ms: uploaded.duration_ms,
      text_head: (uploaded.text || '').slice(0, 90),
    };

    // 3) live recording stream lifecycle (start -> chunks -> status -> finish)
    const started = await call('stream_start');
    const session = started.session_id;
    let chunkResult = null;
    for (const chunk of [pcmFixture(2), pcmFixture(2), pcmFixture(0.6)]) {
      chunkResult = await call('stream_chunk', { session, pcm: chunk.toString('base64') });
    }
    const midStatus = await call('stream_status', { session });
    const finished = await call('stream_finish', { session });
    results.checks.stream = {
      session_created: Boolean(session),
      live: started.live,
      chunk_ok: Boolean(chunkResult),
      mid_text_head: (midStatus.text || '').slice(0, 60),
      final_text_head: (finished.text || '').slice(0, 90),
      duration_ms: finished.duration_ms,
    };

    // 4) save the live recording (with audio) into recents
    const saved = await call('save_recording', {
      text: finished.text || '',
      duration_ms: finished.duration_ms || 0,
      audio: wav.toString('base64'),
      name: 'D4 fixture recording',
    });
    results.checks.save_recording = { id: saved.id, has_audio: saved.has_audio, name: saved.name };

    // 5) folders: create -> rename transcript -> assign -> folder rename -> move back
    const folder = await call('folder_create', { name: 'D4 folder' });
    const renamed = await call('rename', { id: saved.id, name: 'D4 renamed recording' });
    const assigned = await call('assign', { id: saved.id, folder: folder.id });
    const unassigned = await call('assign', { id: saved.id, folder: null });
    results.checks.folders = {
      folder: folder.name,
      renamed: renamed.name,
      assigned: assigned.folder_id === folder.id,
      unassigned: unassigned.folder_id === null,
    };

    // 6) combine: append the upload into the recording (source is consumed)
    const combined = await call('combine', { id: saved.id, source: uploaded.id });
    results.checks.combine = { duration_ms: combined.duration_ms, text_head: (combined.text || '').slice(0, 90) };

    // 7) exports: transcript text + saved audio
    const textExport = await call('export_text', { id: saved.id });
    const audioExport = await call('export_audio', { id: saved.id });
    results.checks.exports = {
      text: { name: textExport.name, chars: (textExport.text || '').length },
      audio: { name: audioExport.name, mime: audioExport.mime, bytes: Buffer.from(audioExport.data || '', 'base64').length },
    };

    // 8) library reflects the combined state; key lifecycle is metadata-only practice mode
    const library = await call('library');
    results.checks.library = {
      folders: library.folders.length,
      transcripts: library.transcripts.length,
      combined_present: library.transcripts.some((row) => row.id === saved.id),
      upload_consumed_by_combine: !library.transcripts.some((row) => row.id === uploaded.id),
    };
    const setKey = await call('set_key', { key: 'practice-key-not-a-real-credential' });
    const afterSet = await call('status');
    const cleared = await call('clear_key');
    results.checks.key_lifecycle = {
      set_ack: setKey.has_key === true,
      mode_after_set: afterSet.mode,
      cleared: cleared.has_key === false,
      mode_after_clear: (await call('status')).mode,
    };

    // 9) plain-language errors: unknown action + missing fields
    const expectPlainError = async (action, body, needle) => {
      try {
        await call(action, body);
        return { action, got_error: false };
      } catch (error) {
        const message = String(error.message || error);
        return { action, got_error: true, plain: message.includes(needle), message };
      }
    };
    results.checks.plain_errors = [
      await expectPlainError('stream_chunk', {}, 'recording session has ended'),
      await expectPlainError('export_audio', { id: 'missing-id' }, 'no longer exists'),
    ];

    results.finishedAt = new Date().toISOString();
    fs.writeFileSync(path.join(OUT, 'transcription-e2e.json'), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results, null, 2));
  } finally {
    child.kill();
  }
}

main().catch((error) => {
  console.error('D4 TRANSCRIPTION E2E FAILED:', error && error.stack ? error.stack : error);
  process.exit(1);
});
