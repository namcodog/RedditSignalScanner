import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

// 在每个测试后自动清理 DOM
afterEach(() => {
  cleanup();
});

// 在每个测试前清理所有 mock
beforeEach(() => {
  vi.clearAllMocks();
});
