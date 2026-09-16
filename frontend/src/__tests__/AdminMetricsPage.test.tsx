import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import AdminMetricsPage from "@/app/admin/metrics/page";

jest.mock("swr", () => {
  return jest.fn((key: string) => {
    if (typeof key === "string" && key.includes("/api/v1/metrics/monthly")) {
      return {
        data: {
          month: "2026-09",
          total_alerts: 45,
          true_alarms: 40,
          false_alarms_total: 5,
          false_alarms_user: 3,
          false_alarms_auto: 2,
          false_alarm_rate_pct: 11.1,
          daily_breakdown: [
            { date: "2026-09-01", total: 10, true_alarm: 9, false_alarm: 1 },
            { date: "2026-09-02", total: 15, true_alarm: 14, false_alarm: 1 },
            { date: "2026-09-03", total: 20, true_alarm: 17, false_alarm: 3 },
          ],
        },
        isLoading: false,
      };
    }
    if (typeof key === "string" && key.includes("/api/v1/metrics/yearly")) {
      return {
        data: {
          year: "2026",
          total_alerts: 540,
          true_alarms: 490,
          false_alarms_total: 50,
          false_alarms_user: 30,
          false_alarms_auto: 20,
          false_alarm_rate_pct: 9.3,
          monthly_breakdown: [
            { month: "2026-01", total: 50, true_alarm: 45, false_alarm: 5 },
            { month: "2026-02", total: 40, true_alarm: 36, false_alarm: 4 },
            { month: "2026-03", total: 60, true_alarm: 55, false_alarm: 5 },
            { month: "2026-04", total: 45, true_alarm: 40, false_alarm: 5 },
            { month: "2026-05", total: 70, true_alarm: 65, false_alarm: 5 },
            { month: "2026-06", total: 80, true_alarm: 72, false_alarm: 8 },
            { month: "2026-07", total: 95, true_alarm: 88, false_alarm: 7 },
            { month: "2026-08", total: 50, true_alarm: 45, false_alarm: 5 },
            { month: "2026-09", total: 50, true_alarm: 44, false_alarm: 6 },
            { month: "2026-10", total: 0, true_alarm: 0, false_alarm: 0 },
            { month: "2026-11", total: 0, true_alarm: 0, false_alarm: 0 },
            { month: "2026-12", total: 0, true_alarm: 0, false_alarm: 0 },
          ],
        },
        isLoading: false,
      };
    }
    if (typeof key === "string" && key.includes("/api/v1/metrics/cost/yearly")) {
      return {
        data: {
          year: "2026",
          total_cost_thb: 4200.0,
          monthly_cost_breakdown: [
            { month: "2026-01", external_cost_thb: 200.0, gcp_cost_thb: 0.0, total_cost_thb: 200.0 },
            { month: "2026-02", external_cost_thb: 200.0, gcp_cost_thb: 0.0, total_cost_thb: 200.0 },
            { month: "2026-03", external_cost_thb: 200.0, gcp_cost_thb: 0.0, total_cost_thb: 200.0 },
            { month: "2026-04", external_cost_thb: 200.0, gcp_cost_thb: 0.0, total_cost_thb: 200.0 },
            { month: "2026-05", external_cost_thb: 200.0, gcp_cost_thb: 0.0, total_cost_thb: 200.0 },
            { month: "2026-06", external_cost_thb: 200.0, gcp_cost_thb: 0.0, total_cost_thb: 200.0 },
            { month: "2026-07", external_cost_thb: 200.0, gcp_cost_thb: 0.0, total_cost_thb: 200.0 },
            { month: "2026-08", external_cost_thb: 200.0, gcp_cost_thb: 0.0, total_cost_thb: 200.0 },
            { month: "2026-09", external_cost_thb: 200.0, gcp_cost_thb: 150.0, total_cost_thb: 350.0 },
            { month: "2026-10", external_cost_thb: 0.0, gcp_cost_thb: 0.0, total_cost_thb: 0.0 },
            { month: "2026-11", external_cost_thb: 0.0, gcp_cost_thb: 0.0, total_cost_thb: 0.0 },
            { month: "2026-12", external_cost_thb: 0.0, gcp_cost_thb: 0.0, total_cost_thb: 0.0 },
          ],
        },
        isLoading: false,
      };
    }
    if (typeof key === "string" && key.includes("/api/v1/metrics/cost")) {
      return {
        data: {
          month: "2026-09",
          gcp_cost_thb: 150.0,
          external_cost_thb: 200.0,
          total_cost_thb: 350.0,
          proactive_count: 45,
          ondemand_count: 25,
          cost_per_proactive_alert: 5.0,
          cost_per_ondemand_query: 2.5,
          blended_cost_per_active_user: 12.5,
          mau_count: 28,
        },
        isLoading: false,
      };
    }
    return { data: null, isLoading: false };
  });
});

describe("AdminMetricsPage Charts", () => {
  it("renders metrics overview and view toggle buttons with Baht icons", () => {
    render(<AdminMetricsPage />);
    expect(screen.getByText(/Alert Accuracy & Unit Economics/i)).toBeInTheDocument();
    expect(screen.getByText("รายวัน (Daily)")).toBeInTheDocument();
    expect(screen.getByText("รายเดือน (Monthly)")).toBeInTheDocument();
    expect(screen.getByText("รายปี (Yearly)")).toBeInTheDocument();
    // Verify cost chart toggle exists
    expect(screen.getByText("ต้นทุนค่าใช้จ่าย (Cost)")).toBeInTheDocument();
  });

  it("switches between daily, monthly, and yearly chart tabs", () => {
    render(<AdminMetricsPage />);
    
    // Default is daily chart tab
    expect(screen.getByTestId("chart-daily")).toBeInTheDocument();

    // Switch to monthly tab
    const monthlyBtn = screen.getByText("รายเดือน (Monthly)");
    fireEvent.click(monthlyBtn);
    expect(screen.getByTestId("chart-monthly")).toBeInTheDocument();

    // Switch to yearly tab
    const yearlyBtn = screen.getByText("รายปี (Yearly)");
    fireEvent.click(yearlyBtn);
    expect(screen.getByTestId("chart-yearly")).toBeInTheDocument();
  });

  it("switches to cost chart tab and displays monthly cost bars", () => {
    render(<AdminMetricsPage />);
    const costBtn = screen.getByText("ต้นทุนค่าใช้จ่าย (Cost)");
    fireEvent.click(costBtn);
    expect(screen.getByTestId("chart-cost")).toBeInTheDocument();
  });
});
