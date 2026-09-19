import React from 'react';
import { render, screen } from '@testing-library/react';
import { FinancialDashboard } from '../components/FinancialDashboard';
import useSWR from 'swr';

// Mock useSWR
jest.mock('swr');
const mockUseSWR = useSWR as jest.Mock;

describe('FinancialDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state when data is not yet loaded', () => {
    mockUseSWR.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: undefined,
    });

    render(<FinancialDashboard />);
    expect(screen.getByText('Syncing...')).toBeInTheDocument();
  });

  it('renders dynamic runway statistics and active budget jars when API data is fetched', () => {
    mockUseSWR.mockReturnValue({
      data: {
        days_remaining: 150,
        hours_remaining: 12,
        seconds_remaining: 12960000,
        burn_rate_per_day: 500,
        total_balance_thb: 75000,
        circuit_breaker_active: false,
        emergency_overdrive: false,
        budget_jars: [
          {
            name: "Cloud Run Infrastructure",
            percentage: 50,
            allocated_thb: 37500,
            description: "Backend API instances & async workers",
            color: "from-blue-600 to-sky-600",
          },
          {
            name: "TMD Radar & Weather APIs",
            percentage: 30,
            allocated_thb: 22500,
            description: "Radar image processing & storage",
            color: "from-sky-600 to-teal-600",
          },
          {
            name: "Emergency Reserve Jar",
            percentage: 20,
            allocated_thb: 15000,
            description: "Locked buffer for unexpected spikes",
            color: "from-emerald-600 to-teal-500",
          },
        ],
      },
      isLoading: false,
      error: undefined,
    });

    render(<FinancialDashboard />);

    // Verify stats
    expect(screen.getByText('150')).toBeInTheDocument();
    expect(screen.getByText('75,000.00')).toBeInTheDocument();
    expect(screen.getByText(/฿500\.00\/day/)).toBeInTheDocument();

    // Verify budget jars
    expect(screen.getByText('Cloud Run Infrastructure')).toBeInTheDocument();
    expect(screen.getByText('TMD Radar & Weather APIs')).toBeInTheDocument();
    expect(screen.getByText('Emergency Reserve Jar')).toBeInTheDocument();

    // Verify allocations
    expect(screen.getByText('฿37,500')).toBeInTheDocument();
    expect(screen.getByText('฿22,500')).toBeInTheDocument();
    expect(screen.getByText('฿15,000')).toBeInTheDocument();
  });
});
