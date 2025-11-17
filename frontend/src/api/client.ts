/**
 * API Client for MindShift Backend
 */
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired, redirect to login
          localStorage.removeItem('access_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async login(email: string, password: string) {
    const response = await this.client.post('/api/auth/login', { email, password });
    return response.data;
  }

  async register(data: {
    email: string;
    password: string;
    full_name: string;
    organization_name: string;
    organization_domain: string;
  }) {
    const response = await this.client.post('/api/auth/register', data);
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.client.get('/api/auth/me');
    return response.data;
  }

  // AI Coach
  async sendMessage(message: string, conversationId?: number, persona?: string) {
    const response = await this.client.post('/api/coach/chat', {
      message,
      conversation_id: conversationId,
      persona,
    });
    return response.data;
  }

  async getConversations(limit = 20, offset = 0) {
    const response = await this.client.get('/api/coach/conversations', {
      params: { limit, offset },
    });
    return response.data;
  }

  async getConversationMessages(conversationId: number) {
    const response = await this.client.get(`/api/coach/conversations/${conversationId}/messages`);
    return response.data;
  }

  async getIntervention(interventionType: string) {
    const response = await this.client.get(`/api/coach/interventions/${interventionType}`);
    return response.data;
  }

  async deleteConversation(conversationId: number) {
    const response = await this.client.delete(`/api/coach/conversations/${conversationId}`);
    return response.data;
  }

  // Burnout
  async predictBurnout() {
    const response = await this.client.post('/api/burnout/predict');
    return response.data;
  }

  async getBurnoutHistory(days = 90) {
    const response = await this.client.get('/api/burnout/history', {
      params: { days },
    });
    return response.data;
  }

  async submitCheckIn(data: {
    mood: number;
    energy: number;
    stress: number;
    sleep: number;
    workload: number;
    notes?: string;
  }) {
    const response = await this.client.post('/api/burnout/check-in', data);
    return response.data;
  }

  async getTeamAnalytics(departmentId?: number) {
    const response = await this.client.get('/api/burnout/analytics/team', {
      params: { department_id: departmentId },
    });
    return response.data;
  }
}

export const apiClient = new APIClient();
export default apiClient;
