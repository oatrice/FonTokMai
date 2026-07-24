import React from 'react';
import { render, screen } from '@testing-library/react';
import { GlassNavbar } from '../components/GlassNavbar';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: () => '/',
}));

describe('GlassNavbar', () => {
  it('renders the application title', () => {
    render(<GlassNavbar />);
    expect(screen.getByText('FonMaYang')).toBeInTheDocument();
  });

  it('renders navigation links', () => {
    render(<GlassNavbar />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('Jars')).toBeInTheDocument();
  });

  it('renders the live runway badge', () => {
    render(<GlassNavbar />);
    expect(screen.getByText('LIVE RUNWAY')).toBeInTheDocument();
  });
});
