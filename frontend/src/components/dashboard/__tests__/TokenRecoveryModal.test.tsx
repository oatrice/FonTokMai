import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TokenRecoveryModal } from '../TokenRecoveryModal';

// Mock the global fetch
global.fetch = jest.fn();

describe('TokenRecoveryModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('does not render when isOpen is false', () => {
    render(<TokenRecoveryModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByText(/Zero-PII Token Recovery/i)).not.toBeInTheDocument();
  });

  it('renders the form inputs when isOpen is true', () => {
    render(<TokenRecoveryModal {...defaultProps} />);
    expect(screen.getByText(/Zero-PII Token Recovery/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Transaction Hash/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Timestamp/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Amount/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Recover Token/i })).toBeInTheDocument();
  });

  it('shows error message on API failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => ({ detail: 'Recovery failed. Invalid details.' }),
    });

    render(<TokenRecoveryModal {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(/Transaction Hash/i), { target: { value: '0x123' } });
    fireEvent.change(screen.getByLabelText(/Timestamp/i), { target: { value: '1690000000' } });
    fireEvent.change(screen.getByLabelText(/Amount/i), { target: { value: '500' } });

    fireEvent.click(screen.getByRole('button', { name: /Recover Token/i }));

    expect(screen.getByRole('button', { name: /Recovering.../i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Recovery failed. Invalid details./i)).toBeInTheDocument();
    });

    expect(global.fetch).toHaveBeenCalledWith('/api/v1/auth/recover', expect.objectContaining({
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tx_hash: '0x123',
        timestamp: '1690000000',
        amount: '500',
      }),
    }));
  });

  it('shows recovered token on API success', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ token: 'Fon-1234-5678' }),
    });

    render(<TokenRecoveryModal {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(/Transaction Hash/i), { target: { value: '0x123' } });
    fireEvent.change(screen.getByLabelText(/Timestamp/i), { target: { value: '1690000000' } });
    fireEvent.change(screen.getByLabelText(/Amount/i), { target: { value: '500' } });

    fireEvent.click(screen.getByRole('button', { name: /Recover Token/i }));

    await waitFor(() => {
      expect(screen.getByText(/Your recovered access token:/i)).toBeInTheDocument();
      expect(screen.getByText('Fon-1234-5678')).toBeInTheDocument();
    });
  });

  it('calls onClose when close button or overlay is clicked', () => {
    render(<TokenRecoveryModal {...defaultProps} />);
    
    // Assuming there's a close button in the modal header
    fireEvent.click(screen.getByRole('button', { name: /Close/i }));
    
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });
});
