import React, { useState } from 'react';
import Modal from '@renderer/components/base/AionModal';
import kelMark from '@renderer/assets/figma/kel-mark.png';
import { KelButton } from './KelPrimitives';
import { diagnosticsText, type EngineStateFrame } from './engineFailure';
import { engineDiagnostics } from './kelApi';

export default function KelStoppedEngineView({ frame, retrying, onRestart, onReport }: {
  frame: EngineStateFrame; retrying: boolean; onRestart: () => void; onReport: () => void;
}) {
  const [details, setDetails] = useState('');
  const [copied, setCopied] = useState(false);
  const readDetails = async () => {
    const diagnostics = await engineDiagnostics();
    setDetails(diagnosticsText({ title: "Kel’s engine stopped", raw: frame.detail, at: frame.at, ...diagnostics }));
  };
  return <Modal visible className='kel-stopped-engine-modal' variant='standard'
    header={{ render: () => <div className='kel-startup-logo'><img src={kelMark} alt='' /><span>Kel</span></div> }}
    footer={null} closable={false} maskClosable={false} escToExit={false} focusLock autoFocus
    style={{ width: 560 }}>
    <div className='kel-stopped-engine-body'>
      <div className='kel-stopped-engine-titles'><h1>Kel’s engine stopped</h1><p>Your chats and files are safe. {frame.attempts > 0 ? `Kel tried to restart it ${frame.attempts} time${frame.attempts === 1 ? '' : 's'}.` : 'The engine did not recover.'}</p></div>
      <details onToggle={(event) => { if (event.currentTarget.open && !details) void readDetails(); }}>
        <summary>Technical details</summary><div className='kel-stopped-engine-code'><pre>{details || 'Reading diagnostics…'}</pre><button type='button' aria-label='Copy diagnostics' onClick={() => { void navigator.clipboard.writeText(details).then(() => setCopied(true)); }}>{copied ? 'Copied' : 'Copy'}</button></div>
      </details>
      <div className='kel-stopped-engine-actions'><KelButton variant='quiet' onClick={onReport}>Send report</KelButton><KelButton variant='primary' disabled={retrying} onClick={onRestart}>{retrying ? 'Restarting…' : 'Restart engine'}</KelButton></div>
    </div>
  </Modal>;
}
