import { defineConfig, devices } from '@playwright/test';

process.env.NEXT_PUBLIC_BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:3000';

export default defineConfig({
  testDir: './e2e',
  timeout: 90 * 1000, // เพิ่มเวลาให้แต่ละเทสต์รันได้สูงสุด 90 วินาที
  expect: {
    timeout: 15 * 1000, // เพิ่มเวลารอ expect() เป็น 15 วินาที
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 2,
  workers: process.env.CI ? 1 : 3,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3005',
    trace: 'on-first-retry',
    navigationTimeout: 60 * 1000, // เพิ่มเวลารอโหลดหน้าเว็บตอน page.goto เป็น 60 วินาที
    actionTimeout: 30 * 1000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'PORT=3005 npm run dev',
    url: 'http://localhost:3005',
    reuseExistingServer: false,
  },
});
