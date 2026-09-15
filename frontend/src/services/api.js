// frontend/src/services/api.js
import axios from 'axios';

// En Docker usamos '/api/v1' (proxy Nginx). Si ejecutas Vite local fuera de Docker, usará 'http://localhost:8000/api/v1'
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getMenu = async () => {
  const response = await api.get('/menu/');
  return response.data;
};

export const sendChatMessage = async (message, sessionId = 'user_session_1') => {
  const response = await api.post('/chat/', {
    message,
    session_id: sessionId,
  });
  return response.data;
};