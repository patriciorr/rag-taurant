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

export const createReservation = async (reservation) => {
  const response = await api.post('/reservations/', reservation);
  return response.data;
};

const reservationHeaders = ({ email, phone }) => ({
  'X-Reservation-Email': email,
  'X-Reservation-Phone': phone,
});

export const getReservation = async (reservationId, contact) => {
  const response = await api.get(`/reservations/${encodeURIComponent(reservationId)}`, {
    headers: reservationHeaders(contact),
  });
  return response.data;
};

export const updateReservation = async (reservationId, update, contact) => {
  const response = await api.patch(`/reservations/${encodeURIComponent(reservationId)}`, update, {
    headers: reservationHeaders(contact),
  });
  return response.data;
};

export const cancelReservation = async (reservationId, contact) => {
  await api.delete(`/reservations/${encodeURIComponent(reservationId)}`, {
    headers: reservationHeaders(contact),
  });
};

export const sendChatMessage = async (message, sessionId) => {
  const response = await api.post('/chat/', {
    message,
    session_id: sessionId,
  });
  return response.data;
};