/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import type { Theme } from '@/common/theme/types';
import { ipcBridge } from '@/common';
import { useThemeContext } from '@renderer/hooks/context/ThemeContext.tsx';
import { iconColors } from '@renderer/styles/colors';
import { Button, Input, Radio } from '@arco-design/web-react';
import AionModal from '@renderer/components/base/AionModal.tsx';
import { UploadOne, Delete } from '@icon-park/react';
import CodeMirror from '@uiw/react-codemirror';
import { css as cssLang } from '@codemirror/lang-css';
import { EditorView } from '@codemirror/view';
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { CSSProperties } from 'react';
import { injectBackgroundCssBlock } from './backgroundUtils.ts';

/** CodeMirror 编辑器样式 / CodeMirror editor styles */
const CODE_MIRROR_STYLE: CSSProperties = {
  fontSize: '13px',
  border: '1px solid var(--color-border-2)',
  borderRadius: '6px',
  overflow: 'hidden',
} as const;

/** CodeMirror 基础配置 / CodeMirror basic setup */
const CODE_MIRROR_BASIC_SETUP = {
  lineNumbers: true,
  foldGutter: true,
  dropCursor: false,
  allowMultipleSelections: false,
} as const;

interface CssThemeModalProps {
  visible: boolean;
  theme: Theme | null;
  onClose: () => void;
  onSave: (theme: Omit<Theme, 'id' | 'created_at' | 'updated_at' | 'builtin'>) => void;
  onDelete?: () => void;
}

/**
 * CSS 主题编辑弹窗 / CSS Theme Edit Modal
 * 用于添加或编辑 CSS 皮肤主题 / For adding or editing CSS skin themes
 */
const CssThemeModal: React.FC<CssThemeModalProps> = ({ visible, theme, onClose, onSave, onDelete }) => {
  const { t } = useTranslation();
  const { theme: colorTheme } = useThemeContext();
  const [name, setName] = useState('');
  const [cover, setCover] = useState<string>('');
  const [css, setCss] = useState('');
  const [appearance, setAppearance] = useState<'light' | 'dark'>(colorTheme === 'dark' ? 'dark' : 'light');

  const applyBackgroundImageToCss = useCallback((imageDataUrl: string) => {
    if (!imageDataUrl) return;
    setCss((prevCss) => injectBackgroundCssBlock(prevCss, imageDataUrl));
  }, []);

  // 编辑模式时加载主题数据 / Load theme data in edit mode
  useEffect(() => {
    if (theme) {
      setName(theme.name);
      setCover(theme.cover || '');
      setCss(theme.css || '');
      setAppearance(theme.appearance ?? 'light');
    } else {
      setName('Midnight');
      setCover('');
      setCss('');
      setAppearance(colorTheme === 'dark' ? 'dark' : 'light');
    }
  }, [theme, visible, colorTheme]);

  /**
   * 处理封面图片上传 / Handle cover image upload
   */
  const handleCoverUpload = useCallback(async () => {
    try {
      const files = await ipcBridge.dialog.showOpen.invoke({
        properties: ['openFile'],
        filters: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'] }],
      });

      if (files && files[0]) {
        // 使用 IPC 读取图片并转换为 base64 / Use IPC to read image and convert to base64
        const base64 = await ipcBridge.fs.getImageBase64.invoke({ path: files[0] });
        if (base64) {
          setCover(base64);
          applyBackgroundImageToCss(base64);
        }
      }
    } catch (error) {
      console.error('Failed to upload cover:', error);
    }
  }, [applyBackgroundImageToCss]);

  /**
   * 处理保存 / Handle save
   */
  const handleSave = useCallback(() => {
    if (!name.trim()) {
      return;
    }
    onSave({
      name: name.trim(),
      cover: cover || undefined,
      css,
      appearance,
      tokens: undefined,
    });
  }, [name, cover, css, appearance, onSave]);

  const isEditing = !!theme;

  return (
    <AionModal
      variant='standard'
      className='kel-shell-theme-modal'
      visible={visible}
      header={{
        title: isEditing ? 'Edit theme' : 'Add theme',
        showClose: true,
      }}
      onCancel={onClose}
      style={{ width: 560 }}
      unmountOnExit
      footer={{
        render: () => (
          <div className='flex justify-between items-center'>
            <div>
              {onDelete && (
                <Button type='text' icon={<Delete theme='outline' size='14' />} onClick={onDelete}>
                  {t('common.delete')}
                </Button>
              )}
            </div>
            <div className='flex gap-10px'>
              <Button onClick={onClose} className='px-20px min-w-80px' style={{ borderRadius: 8 }}>
                {t('common.cancel')}
              </Button>
              <Button
                type='primary'
                onClick={handleSave}
                disabled={!name.trim()}
                className='px-20px min-w-80px'
                style={{ borderRadius: 8 }}
              >
                {isEditing ? 'Save changes' : 'Save theme'}
              </Button>
            </div>
          </div>
        ),
      }}
    >
      <div className='kel-shell-theme-form'>
        <div className='kel-shell-theme-form-top'>
          <label className='kel-shell-theme-form-name'>
            <span>Name</span>
            <Input value={name} onChange={setName} aria-label='Theme name' placeholder='Theme name' />
          </label>
          <div className='kel-shell-theme-form-base'>
            <span>Based on</span>
            <Radio.Group value={appearance} onChange={(val: 'light' | 'dark') => setAppearance(val)}>
              <Radio value='light'>Light</Radio>
              <Radio value='dark'>Dark</Radio>
            </Radio.Group>
          </div>
        </div>
        <button type='button' className='kel-shell-theme-form-upload' onClick={() => void handleCoverUpload()}>
          <UploadOne theme='outline' size='16' fill={iconColors.secondary} />
          {cover ? 'Change background image' : 'Add a background image (optional)'}
        </button>
        <label className='kel-shell-theme-form-css'>
          <span>Custom CSS</span>
          <CodeMirror
            value={css}
            theme={colorTheme}
            extensions={[cssLang(), EditorView.lineWrapping]}
            onChange={setCss}
            placeholder={'.kel-sidebar {\n  background: #140f33;\n}'}
            basicSetup={CODE_MIRROR_BASIC_SETUP}
            style={CODE_MIRROR_STYLE}
            height='80px'
          />
        </label>
      </div>
    </AionModal>
  );
};

export default CssThemeModal;
