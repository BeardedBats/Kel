import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ShellComposerMetrics from '@renderer/components/kel/ShellComposerMetrics';

describe('Conversation footer usage', () => {
  it('shows nothing until the conversation has reported usage', () => {
    const { container } = render(<ShellComposerMetrics />);
    expect(container.innerHTML).toBe('');
    expect(screen.queryByLabelText('Conversation usage')).toBeNull();
  });
  it('keeps missing parts of a report unknown instead of inventing screenshot values', () => {
    render(<ShellComposerMetrics usage={{ total_tokens: 10 }} />);
    expect(screen.getByTitle('Reported session cost').textContent).toBe('—');
    expect(screen.getByTitle('Reported tokens').textContent).toBe('10 tokens');
    expect(screen.getByTitle('Reported cached input share').textContent).toBe('— cache');
    expect(screen.getByTitle('Reported context remaining').textContent).toBe('— remaining');
  });
  it('uses reported cost and input counters with the supplied context window', () => {
    render(<ShellComposerMetrics usage={{ total_tokens: 1400, breakdown: { input_tokens: 500, cached_read_tokens: 390 }, cost: { amount: 0.02, currency: 'USD' } }} contextLimit={3684} />);
    expect(screen.getByTitle('Reported session cost').textContent).toBe('$0.02');
    expect(screen.getByTitle('Reported tokens').textContent).toBe('1.4K tokens');
    expect(screen.getByTitle('Reported cached input share').textContent).toBe('78% cache');
    expect(screen.getByTitle('Reported context remaining').textContent).toBe('62% remaining');
  });
  it('requires a window for percentages and preserves a reported zero cost', () => {
    const { rerender } = render(<ShellComposerMetrics usage={{ total_tokens: 1500, breakdown: { input_tokens: 0, cached_read_tokens: 0 }, cost: { amount: 0, currency: 'USD' } }} />);
    expect(screen.getByTitle('Reported session cost').textContent).toBe('$0.00');
    expect(screen.getByTitle('Reported cached input share').textContent).toBe('— cache');
    expect(screen.getByTitle('Reported context remaining').textContent).toBe('— remaining');
    rerender(<ShellComposerMetrics usage={{ total_tokens: 1500 }} contextLimit={1000} />);
    expect(screen.getByTitle('Reported context remaining').textContent).toBe('0% remaining');
  });
});
