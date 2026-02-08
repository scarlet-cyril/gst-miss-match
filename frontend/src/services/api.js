import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const api = {
  clients: {
    getAll: () => axios.get(`${API}/clients`),
    create: (data) => axios.post(`${API}/clients`, data),
    delete: (clientId) => axios.delete(`${API}/clients/${clientId}`),
  },
  documents: {
    upload: (formData) => axios.post(`${API}/documents/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    getAll: (clientId) => axios.get(`${API}/documents?client_id=${clientId}`),
  },
  invoices: {
    getAll: (clientId) => axios.get(`${API}/invoices?client_id=${clientId}`),
    create: (data) => axios.post(`${API}/invoices`, data),
  },
  ledger: {
    getAll: (clientId) => axios.get(`${API}/ledger?client_id=${clientId}`),
    create: (data) => axios.post(`${API}/ledger`, data),
  },
  reports: {
    profitLoss: (clientId, startDate, endDate) => 
      axios.get(`${API}/reports/profit-loss?client_id=${clientId}&start_date=${startDate}&end_date=${endDate}`),
    balanceSheet: (clientId, asOfDate) => 
      axios.get(`${API}/reports/balance-sheet?client_id=${clientId}&as_of_date=${asOfDate}`),
  },
  chat: {
    send: (data) => axios.post(`${API}/chat`, data),
    getHistory: (clientId) => axios.get(`${API}/chat/history?client_id=${clientId}`),
  },
  itc: {
    analyze: (clientId) => axios.post(`${API}/itc/analyze?client_id=${clientId}`),
    getMismatches: (clientId) => axios.get(`${API}/itc/mismatches?client_id=${clientId}`),
  },
};

export default api;