import apiClient from './client';

export const authApi = {
  register: async (email, password, fullName) => {
    const res = await apiClient.post('/auth/register', { email, password, full_name: fullName });
    return res.data;
  },
  login: async (email, password) => {
    const res = await apiClient.post('/auth/login', { email, password });
    return res.data;
  },
  getMe: async () => {
    const res = await apiClient.get('/auth/me');
    return res.data;
  }
};
