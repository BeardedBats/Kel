import React from 'react';
import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import type { TMessage } from '@/common/chat/chatLib';
import type { KelHandoff } from '@renderer/components/kel/kelApi';
import { HANDOFF_STATE_EVENT, lastHandoffViews, resetHandoffMemory } from '@renderer/components/kel/workCards/handoffMemory';
import { useHandoffFailureOwner } from '@renderer/pages/conversation/Messages/components/KelEngineFailureCard';

afterEach(() => { cleanup(); resetHandoffMemory(); });

it('keeps a failure visible until its live card loads the same error', () => {
  const messages = [
    { id:'user', conversation_id:'chat', type:'text', position:'right', content:{content:'Do this'} },
    { id:'work', conversation_id:'chat', type:'acp_tool_call', position:'left', content:{update:{tool_call_id:'kel-work:submission'}} },
    { id:'failure', conversation_id:'chat', type:'text', position:'left', content:{content:"I wasn't able to get that started — timed out. You can retry it from the card above."} },
  ] as TMessage[];
  const Probe = () => <div>{useHandoffFailureOwner(messages,'failure','timed out') ? 'Work card owns error' : 'Standalone error visible'}</div>;
  render(<Probe />);
  expect(screen.getByText('Standalone error visible')).toBeTruthy();
  act(() => {
    lastHandoffViews.set('submission',{phase:'failed_to_start',error:'timed out'} as KelHandoff);
    window.dispatchEvent(new Event(HANDOFF_STATE_EVENT));
  });
  expect(screen.getByText('Work card owns error')).toBeTruthy();
  act(() => {
    lastHandoffViews.set('submission',{phase:'failed_to_start',error:'a different failure'} as KelHandoff);
    window.dispatchEvent(new Event(HANDOFF_STATE_EVENT));
  });
  expect(screen.getByText('Standalone error visible')).toBeTruthy();
});
