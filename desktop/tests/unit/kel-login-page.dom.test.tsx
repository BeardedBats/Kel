/**
 * CP-12 / D-61 — the WebUI sign-in page never stores the password (the session cookie carries
 * "Keep me signed in"), deletes a password an older build stored, has no language picker and speaks
 * in plain Kel words rather than donor marketing copy.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import loginStrings from '@/renderer/services/i18n/locales/en-US/login.json';

const login = vi.fn(async () => ({ success: true }));
vi.mock('@renderer/hooks/context/AuthContext', () => ({ useAuth: () => ({ status: 'unauthenticated', login }) }));
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key.split('.').slice(1).reduce<unknown>((node, part) => (node as Record<string, unknown>)?.[part], loginStrings) ?? key,
  }),
}));

import LoginPage, { LEGACY_REMEMBERED_PASSWORD_KEY, REMEMBERED_USERNAME_KEY, REMEMBER_ME_KEY } from '@renderer/pages/login';

beforeEach(() => localStorage.clear());
afterEach(cleanup);

const renderPage = () => render(<MemoryRouter><LoginPage /></MemoryRouter>);

describe('WebUI sign-in page', () => {
  it('deletes a password an older build stored and keeps only the username', () => {
    localStorage.setItem(REMEMBER_ME_KEY, 'true');
    localStorage.setItem(REMEMBERED_USERNAME_KEY, 'bGVr'.split('').reverse().join(''));
    localStorage.setItem(LEGACY_REMEMBERED_PASSWORD_KEY, 'c2VjcmV0'.split('').reverse().join(''));
    renderPage();
    expect(localStorage.getItem(LEGACY_REMEMBERED_PASSWORD_KEY)).toBeNull();
    expect((screen.getByLabelText('Password') as HTMLInputElement).value).toBe('');
  });

  it('signs in with "Keep me signed in" without storing the password', async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'nick' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'hunter2' } });
    fireEvent.click(screen.getByLabelText('Keep me signed in'));
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await waitFor(() => expect(login).toHaveBeenCalledWith({ username: 'nick', password: 'hunter2', remember: true }));
    await waitFor(() => expect(localStorage.getItem(REMEMBER_ME_KEY)).toBe('true'));
    const stored = Object.keys(localStorage).map((key) => `${key}=${localStorage.getItem(key)}`).join('\n');
    expect(stored).not.toContain('hunter2');
    expect(localStorage.getItem(LEGACY_REMEMBERED_PASSWORD_KEY)).toBeNull();
  });

  it('has no language picker and no donor marketing copy', () => {
    const view = renderPage();
    expect(view.container.querySelector('select')).toBeNull();
    expect(view.container.textContent).not.toMatch(/Transform your command-line AI|Modern & Efficient|Welcome back/);
    expect(view.container.textContent).toContain('Sign in to use Kel from this browser.');
  });
});
