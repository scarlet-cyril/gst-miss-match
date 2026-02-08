import React, { createContext, useContext, useState } from 'react';

const ClientContext = createContext(null);

export const ClientProvider = ({ children }) => {
  const [selectedClient, setSelectedClient] = useState(null);
  const [clients, setClients] = useState([]);

  return (
    <ClientContext.Provider value={{ selectedClient, setSelectedClient, clients, setClients }}>
      {children}
    </ClientContext.Provider>
  );
};

export const useClient = () => {
  const context = useContext(ClientContext);
  if (!context) {
    throw new Error('useClient must be used within ClientProvider');
  }
  return context;
};