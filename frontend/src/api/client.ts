/** Axios instance configured for LunaYield API */

import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Response interceptor to normalize error shape
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Ensure error.response?.data?.detail exists for typed error handling
    if (error.response?.data?.detail) {
      error.userMessage = error.response.data.detail;
    } else if (error.message) {
      error.userMessage = error.message;
    } else {
      error.userMessage = 'An unexpected error occurred';
    }
    return Promise.reject(error);
  }
);

export default apiClient;