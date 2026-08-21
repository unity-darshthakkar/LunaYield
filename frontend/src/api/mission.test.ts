/** API client tests */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from './client';
import * as missionApi from './mission';

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}));

describe('API Client', () => {
  let mockGet: ReturnType<typeof vi.fn>;
  let mockPost: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    const axiosInstance = apiClient;
    mockGet = vi.fn();
    mockPost = vi.fn();
    (axiosInstance as unknown as { get: typeof mockGet; post: typeof mockPost }).get = mockGet;
    (axiosInstance as unknown as { get: typeof mockGet; post: typeof mockPost }).post = mockPost;
  });

  describe('getMissionState', () => {
    it('returns mission data on success', async () => {
      const mockMission = {
        mission_id: 'luna-mission-001',
        label: 'Test Mission',
        status: 'IDLE',
        elapsed_s: 0,
        resources: {
          battery_pct: 100,
          storage_pct: 0,
          temperature_c: -40,
          comm_window_remaining_s: 7200,
          op_time_remaining_s: 28800,
        },
        original_route: { waypoints: [] },
        active_route: { waypoints: [] },
        candidate_plans: [],
        anomaly_active: false,
        audit_trail: [],
      };
      mockGet.mockResolvedValue({ data: mockMission });

      const result = await missionApi.getMissionState();

      expect(result).toEqual(mockMission);
      expect(mockGet).toHaveBeenCalledWith('/mission/state');
    });
  });

  describe('getScenario', () => {
    it('returns scenario data on success', async () => {
      const mockScenario = {
        mission_id: 'luna-mission-001',
        label: 'Test Mission',
        waypoints: [
          { id: 'wp-1', x: 0.1, y: 0.1, label: 'Base', is_science_target: false },
        ],
      };
      mockGet.mockResolvedValue({ data: mockScenario });

      const result = await missionApi.getScenario();

      expect(result).toEqual(mockScenario);
      expect(mockGet).toHaveBeenCalledWith('/scenario');
    });
  });

  describe('startMission', () => {
    it('posts to start endpoint', async () => {
      const mockMission = { status: 'RUNNING' } as missionApi.Mission;
      mockPost.mockResolvedValue({ data: mockMission });

      const result = await missionApi.startMission();

      expect(result).toEqual(mockMission);
      expect(mockPost).toHaveBeenCalledWith('/mission/start');
    });
  });

  describe('pauseMission', () => {
    it('posts to pause endpoint', async () => {
      const mockMission = { status: 'PAUSED' } as missionApi.Mission;
      mockPost.mockResolvedValue({ data: mockMission });

      const result = await missionApi.pauseMission();

      expect(result).toEqual(mockMission);
      expect(mockPost).toHaveBeenCalledWith('/mission/pause');
    });
  });

  describe('approvePlan', () => {
    it('posts to plan approve endpoint with encoded plan ID', async () => {
      const mockPlan = { plan_id: 'plan-a-001', label: 'Test' } as missionApi.CandidatePlan;
      mockPost.mockResolvedValue({ data: mockPlan });

      const result = await missionApi.approvePlan('plan-a-001');

      expect(result).toEqual(mockPlan);
      expect(mockPost).toHaveBeenCalledWith('/plans/plan-a-001/approve');
    });
  });
});
