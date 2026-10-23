import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the sign-in screen', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: 'ChamaScore' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument();
});
