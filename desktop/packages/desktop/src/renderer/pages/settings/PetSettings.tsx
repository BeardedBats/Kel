import ShellSourceCardHeader from '@renderer/components/kel/ShellSourceCardHeader';
/**
 * @license
 * Copyright 2025 AionUi (aionui.com)
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useCallback, useEffect, useState } from 'react';
import { Message, Radio, Switch } from '@arco-design/web-react';
import { useTranslation } from 'react-i18next';
import { systemSettings } from '@/common/adapter/ipcBridge';
import { configService } from '@/common/config/configService';
import { isElectronDesktop } from '@/renderer/utils/platform';
import SettingsPageWrapper from './components/SettingsPageWrapper';
import PreferenceRow from '@/renderer/components/settings/SettingsModal/contents/SystemModalContent/PreferenceRow';
import AionScrollArea from '@/renderer/components/base/AionScrollArea';
import { useSettingsViewMode } from '@/renderer/components/settings/SettingsModal/settingsViewContext';

const PetSettings: React.FC = () => {
  const [enabled, setEnabled] = useState(false);
  const [enabledResolved, setEnabledResolved] = useState(false);
  const [size, setSize] = useState(280);
  const [dnd, setDnd] = useState(false);
  const [confirmEnabled, setConfirmEnabled] = useState(true);
  const { t } = useTranslation();
  const viewMode = useSettingsViewMode();
  const isPageMode = viewMode === 'page';
  const isDesktop = isElectronDesktop();

  useEffect(() => {
    let active = true;
    setSize(configService.get('pet.size') ?? 280);
    setDnd(configService.get('pet.dnd') ?? false);
    setConfirmEnabled(configService.get('pet.confirmEnabled') ?? true);
    systemSettings.getPetEnabled
      .invoke()
      .then((value) => {
        if (!active) return;
        setEnabled(value);
        setEnabledResolved(true);
      })
      .catch(() => {
        // IPC failure: fall back to the locked default (OFF); never fall back to ON,
        // which would reintroduce the "UI lies" state this fix eliminates.
        if (!active) return;
        setEnabled(false);
        setEnabledResolved(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleEnabledChange = useCallback((checked: boolean) => {
    setEnabled(checked);
    configService.setLocal('pet.enabled', checked);
    let settled = false;
    const settle = async () => {
      // The toggle must never sit ON when the pet cannot actually be created (RA-MINOR-003):
      // re-read the authoritative state and settle the UI + stored value on the truth, with a
      // reason when an enable was refused. A reload must not contradict what was just shown.
      if (settled) return;
      settled = true;
      try {
        const actual = await systemSettings.getPetEnabled.invoke();
        const on = Boolean(actual);
        setEnabled(on);
        configService.setLocal('pet.enabled', on);
        if (checked && !on) {
          // HVRA-SUG-002: one refusal explanation per attempt — the stable message id collapses any
          // duplicate emission (a second identical toast updates the first instead of stacking).
          Message.error({
            id: 'pet-enable-refused',
            content: 'The desktop pet is not available in this build, so it stays off.',
          });
        }
      } catch {
        setEnabled(false);
        configService.setLocal('pet.enabled', false);
        if (checked) {
          Message.error({ id: 'pet-enable-failed', content: 'The desktop pet could not be turned on.' });
        }
      }
    };
    systemSettings.setPetEnabled.invoke({ enabled: checked }).then(settle).catch(settle);
    // The donor bridge dispatcher can swallow a refused handler without settling its promise;
    // reconcile on a deadline so the toggle can never sit ON against the real state.
    window.setTimeout(() => {
      void settle();
    }, 900);
  }, []);

  const handleSizeChange = useCallback(
    (val: number) => {
      const prevSize = size;
      setSize(val);
      configService.setLocal('pet.size', val);
      systemSettings.setPetSize.invoke({ size: val }).catch(() => {
        setSize(prevSize);
        configService.setLocal('pet.size', prevSize);
      });
    },
    [size]
  );

  const handleDndChange = useCallback((checked: boolean) => {
    setDnd(checked);
    configService.setLocal('pet.dnd', checked);
    systemSettings.setPetDnd.invoke({ dnd: checked }).catch(() => {
      setDnd(!checked);
      configService.setLocal('pet.dnd', !checked);
    });
  }, []);

  const handleConfirmEnabledChange = useCallback((checked: boolean) => {
    setConfirmEnabled(checked);
    configService.setLocal('pet.confirmEnabled', checked);
    systemSettings.setPetConfirmEnabled.invoke({ enabled: checked }).catch(() => {
      setConfirmEnabled(!checked);
      configService.setLocal('pet.confirmEnabled', !checked);
    });
  }, []);

  if (!isDesktop) {
    return (
      <SettingsPageWrapper>
        <AionScrollArea className='flex-1 min-h-0 pb-16px' disableOverflow={isPageMode}>
          <div className='space-y-16px'>
            <div className='px-[12px] md:px-[32px] py-16px bg-2 rd-16px'>
              <p className='m-0 text-13px text-t-secondary'>{t('pet.desktopOnly')}</p>
            </div>
          </div>
        </AionScrollArea>
      </SettingsPageWrapper>
    );
  }

  const preferenceItems = [
    {
      key: 'enabled',
      label: t('pet.enable'),
      component: (
        <Switch
          checked={enabled}
          loading={!enabledResolved}
          disabled={!enabledResolved}
          onChange={handleEnabledChange}
        />
      ),
    },
    {
      key: 'size',
      label: t('pet.size'),
      component: (
        <Radio.Group value={size} onChange={handleSizeChange} disabled={!enabled}>
          <Radio value={200}>{t('pet.sizeSmall', { px: 200 })}</Radio>
          <Radio value={280}>{t('pet.sizeMedium', { px: 280 })}</Radio>
          <Radio value={360}>{t('pet.sizeLarge', { px: 360 })}</Radio>
        </Radio.Group>
      ),
    },
    {
      key: 'dnd',
      label: t('pet.dnd'),
      description: t('pet.dndDescription'),
      component: <Switch checked={dnd} onChange={handleDndChange} disabled={!enabled} />,
    },
    {
      key: 'confirmBubble',
      label: t('pet.confirmBubble'),
      description: t('pet.confirmBubbleDescription'),
      component: <Switch checked={confirmEnabled} onChange={handleConfirmEnabledChange} disabled={!enabled} />,
    },
  ];

  return (
    <SettingsPageWrapper>
      <AionScrollArea className='flex-1 min-h-0 pb-16px' disableOverflow={isPageMode}>
        <div className='space-y-16px'>
          <div className='kel-shell-settings-card kel-shell-pet-card px-[12px] md:px-[32px] py-16px bg-2 rd-16px space-y-12px'>
            <ShellSourceCardHeader title='Desktop Pet' /><div className='w-full flex flex-col divide-y divide-border-2'>
              {preferenceItems.map((item) => item.key === 'size' ? <React.Fragment key='size'>
                <div className='kel-desktop-only'><PreferenceRow label={item.label}>{item.component}</PreferenceRow></div>
                <select className='kel-phone-only kel-shell-pet-size' aria-label='Pet Size' value={size} disabled={!enabled} onChange={(event) => handleSizeChange(Number(event.target.value))}>
                  <option value={200}>… Small</option><option value={280}>… Medium</option><option value={360}>… Large</option>
                </select>
              </React.Fragment> : (
                <PreferenceRow key={item.key} label={item.label}>
                  {item.component}
                </PreferenceRow>
              ))}
            </div>
          </div>
        </div>
      </AionScrollArea>
    </SettingsPageWrapper>
  );
};

export default PetSettings;
