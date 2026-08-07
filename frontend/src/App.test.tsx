import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders the LunaYield Mission Lab heading', () => {
    render(<App />);
    expect(screen.getByText('LunaYield Mission Lab')).toBeInTheDocument();
  });
});