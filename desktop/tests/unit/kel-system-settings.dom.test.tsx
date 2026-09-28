/** FN-14: Full access has one home — Settings → Permissions — so System no longer repeats the card. */
import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';

vi.mock('@/renderer/components/settings/SettingsModal/contents/SystemModalContent', () => ({ default: () => <p>system settings</p> }));
vi.mock('@/renderer/components/kel/KelDataCard', () => ({ KelDataCard: () => <p>data and backup</p> }));
vi.mock('@/renderer/components/kel/KelAuthorityCard', () => ({ KelAuthorityCard: () => <p>Full access card</p> }));
vi.mock('@/renderer/pages/settings/components/SettingsPageWrapper', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

import SystemSettings from '@/renderer/pages/settings/SystemSettings';

afterEach(cleanup);

it('System shows data and system settings but not the Full access card', () => {
  render(<MemoryRouter initialEntries={['/settings/system']}><SystemSettings /></MemoryRouter>);
  expect(screen.getByText('data and backup')).toBeTruthy();
  expect(screen.queryByText('Full access card')).toBeNull();
});
