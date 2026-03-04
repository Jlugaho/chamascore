import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  register: (data: any) => api.post('/api/v1/auth/register', data),
  login: (data: any) => api.post('/api/v1/auth/login', data),
  me: () => api.get('/api/v1/auth/me'),
};

export const groupsApi = {
  list: () => api.get('/api/v1/groups'),
  create: (data: any) => api.post('/api/v1/groups', data),
  get: (id: string) => api.get(`/api/v1/groups/${id}`),
};

export const contributionsApi = {
  list: (groupId: string) => api.get(`/api/v1/contributions/group/${groupId}`),
  create: (data: any) => api.post('/api/v1/contributions', data),
};

export const loansApi = {
  list: (groupId: string) => api.get(`/api/v1/loans/group/${groupId}`),
  apply: (data: any) => api.post('/api/v1/loans/apply', data),
  approve: (loanId: string, approved: boolean) =>
    api.post(`/api/v1/loans/${loanId}/approve?approved=${approved}`),
};

export const meetingsApi = {
  list: (groupId: string) => api.get(`/api/v1/meetings/group/${groupId}`),
  create: (data: any) => api.post('/api/v1/meetings', data),
};

export const scoreApi = {
  get: (groupId: string) => api.get(`/api/v1/credit-scores/group/${groupId}`),
};

export default api;