import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT on every request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// Redirect to login on 401/403
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login:    (data) => api.post('/auth/login', data),
};

// Case API
export const caseAPI = {
  create:        (data) => api.post('/cases/create', data),
  getMyCases:    ()     => api.get('/cases/my-cases'),
  getById:       (id)   => api.get(`/cases/${id}`),
  confirmEntity: (id, payload) => api.post(`/cases/${id}/confirm-entity`, payload),
  deleteCase:    (id)   => api.delete(`/cases/${id}`),
};

// Session API
export const sessionAPI = {
  start:       (initialText, language = 'en') =>
                 api.post('/session/start', { initialText, language }),
  answer:      (sessionId, answerText) =>
                 api.post(`/session/${sessionId}/answer`, { answerText }),
  answerVoice: (sessionId, formData) =>
                 api.post(`/session/${sessionId}/answer-voice`, formData, {
                   headers: { 'Content-Type': 'multipart/form-data' },
                 }),
  getStatus:   (sessionId) => api.get(`/session/${sessionId}`),
  getSessions: ()           => api.get('/session'),
  delete:      (sessionId) => api.delete(`/session/${sessionId}`),
};

// Document API — generateBilingual posts the payload and gets back a PDF blob
export const documentAPI = {
  generateBilingual: (payload) =>
    api.post('/documents/generate-bilingual', payload, { responseType: 'blob' }),
};

export default api;
