import axios from 'axios';

const API_BASE_URL = 'http://localhost:8080/api';
const NLP_BASE_URL = 'http://localhost:8000';

// Create axios instance for backend
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Create axios instance for NLP service
const nlpApi = axios.create({
  baseURL: NLP_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
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
  login: (data) => api.post('/auth/login', data),
};

// Case API
export const caseAPI = {
  create: (data) => api.post('/cases/create', data),
  getMyCases: () => api.get('/cases/my-cases'),
  getCaseById: (id) => api.get(`/cases/${id}`),
  confirmEntity: (caseId, fieldName) =>
    api.post(`/cases/${caseId}/confirm-entity`, { fieldName }),
};

// Session API (New)
export const sessionAPI = {
  start: (initialText, language = 'en') => api.post('/session/start', { initialText, language }),
  answer: (sessionId, answerText) => api.post(`/session/${sessionId}/answer`, { answerText }),
  answerVoice: (sessionId, formData) => api.post(`/session/${sessionId}/answer-voice`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  getStatus: (sessionId) => api.get(`/session/${sessionId}/status`),
};

// Document API
export const documentAPI = {
  verify: (data) => api.post('/documents/verify', data),
  generate: (data) => api.post('/documents/generate', data, {
    responseType: 'blob',
  }),
};

// NLP API
export const nlpAPI = {
  analyze: (text) => nlpApi.post('/analyze', { text }),
  classify: (text) => nlpApi.post('/classify', { text }),
  translate: (text, targetLanguage) =>
    nlpApi.post('/translate', { text, target_language: targetLanguage }),
};

export default api;
