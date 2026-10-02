import React from 'react';
import './settings.css';

/** A closed disclosure keeps technical choices available without crowding daily settings. */
const SettingsAdvanced: React.FC<{ children: React.ReactNode; testId: string }> = ({ children, testId }) => (
  <details className='kel-settings-advanced' data-testid={testId}>
    <summary>Advanced</summary>
    <div className='kel-settings-advanced__content'>{children}</div>
  </details>
);

export default SettingsAdvanced;
