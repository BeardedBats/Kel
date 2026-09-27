/**
 * CP-7 / ST-21 — a browser (WebUI) session shows no donor channel forms (Telegram, Lark, …);
 * it only says where remote access is managed.
 */
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key, i18n: { language: 'en-US' } }) }));
vi.mock('@/common/adapter/ipcBridge', () => {
  const invoke = vi.fn(async () => null);
  const endpoint = { invoke, on: vi.fn(() => () => undefined) };
  const ns = new Proxy({}, { get: () => endpoint });
  return { webui: ns, shell: ns };
});
vi.mock('@/common/config/configService', () => ({ configService: { get: () => undefined, set: vi.fn(), whenReady: async () => undefined } }));
vi.mock('@/renderer/components/base/AionModal', () => ({ default: () => null }));

import WebuiModalContent from '@renderer/components/settings/SettingsModal/contents/WebuiModalContent';

afterEach(cleanup);

describe('WebUI settings in a browser session', () => {
  it('explains that remote access is managed from the desktop, with no channel integrations', () => {
    render(<WebuiModalContent />);
    expect(screen.getByText('Remote access is managed from the desktop app.')).toBeTruthy();
    expect(screen.queryByText(/Telegram|Lark|DingTalk|WeCom|Weixin|WeChat|Slack|Discord/i)).toBeNull();
    expect(screen.queryByRole('switch')).toBeNull();
  });
});
