import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { planWorkspaceRepairs } from '@/process/services/kel/repairWorkspacePaths';
import en from '@/renderer/services/i18n/locales/en-US/conversation.json';

const ENGINE = path.join('C:', 'Users', 'Nick', 'Desktop', 'Kel', 'Data', 'engine');

describe('planWorkspaceRepairs (FIX-0013: chats pointing at a removed data root)', () => {
  it('re-homes a Kel scratch folder from the removed KelV2Runs root under the current engine root', () => {
    const repairs = planWorkspaceRepairs(
      [
        {
          id: '7c8ac73d',
          extra: { workspace: 'C:\\Users\\Nick\\KelV2Runs\\prepared\\engine\\aion-workspaces\\9bea28ee-14cd-42be-b721-4cde34d1bf56' },
        },
      ],
      ENGINE,
      () => false
    );
    expect(repairs).toEqual([
      {
        id: '7c8ac73d',
        from: 'C:\\Users\\Nick\\KelV2Runs\\prepared\\engine\\aion-workspaces\\9bea28ee-14cd-42be-b721-4cde34d1bf56',
        to: path.join(ENGINE, 'aion-workspaces', '9bea28ee-14cd-42be-b721-4cde34d1bf56'),
      },
    ]);
  });

  it('leaves existing folders, folders the person chose, and non-Kel folders alone', () => {
    const repairs = planWorkspaceRepairs(
      [
        { id: 'a', extra: { workspace: 'D:\\gone\\aion-workspaces\\x' } },
        { id: 'b', extra: { workspace: 'D:\\gone\\aion-workspaces\\y', custom_workspace: true } },
        { id: 'c', extra: { workspace: 'D:\\Projects\\website' } },
        { id: 'd', extra: {} },
      ],
      ENGINE,
      (target) => target === 'D:\\gone\\aion-workspaces\\x'
    );
    expect(repairs).toEqual([]);
  });

  it('re-homes a missing acp-temp scratch folder', () => {
    const repairs = planWorkspaceRepairs([{ id: 't', extra: { workspace: 'E:\\old\\acp-temp-1a2b3c4d' } }], ENGINE, () => false);
    expect(repairs[0].to).toBe(path.join(ENGINE, 'aion-workspaces', 'acp-temp-1a2b3c4d'));
  });

  it('explains a missing chat folder in plain words with no path (JR-8/JR-16)', () => {
    const copy = en.agentError.codes.WORKSPACE_PATH_RUNTIME_UNAVAILABLE;
    expect(copy.title).toBe("Kel can't open this chat's folder");
    expect(copy.bodyWithPath).toBe('The folder this chat works in is missing. Choose a folder to keep going, or start a new chat.');
    expect(copy.bodyWithPath).not.toContain('{{workspacePath}}');
    expect(copy.title).not.toMatch(/agent|workspace/i);
  });
});
