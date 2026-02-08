import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useClient } from '@/contexts/ClientContext';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Users, Plus, LogOut, Menu, X } from 'lucide-react';
import api from '@/services/api';
import { toast } from 'sonner';
import ChatPanel from '@/components/ChatPanel';
import ClientWorkspace from '@/components/ClientWorkspace';
import AddClientDialog from '@/components/AddClientDialog';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const { selectedClient, setSelectedClient, clients, setClients } = useClient();
  const [showAddClient, setShowAddClient] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    loadClients();
  }, []);

  const loadClients = async () => {
    try {
      const response = await api.clients.getAll();
      setClients(response.data);
      if (response.data.length > 0 && !selectedClient) {
        setSelectedClient(response.data[0]);
      }
    } catch (error) {
      toast.error('Failed to load clients');
    }
  };

  const handleAddClient = async (clientData) => {
    try {
      const response = await api.clients.create(clientData);
      setClients([...clients, response.data]);
      setSelectedClient(response.data);
      setShowAddClient(false);
      toast.success('Client added successfully');
    } catch (error) {
      toast.error('Failed to add client');
    }
  };

  return (
    <div className="h-screen flex flex-col bg-background">
      <header className="h-14 border-b border-border flex items-center justify-between px-4 bg-card">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            data-testid="mobile-menu-button"
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </Button>
          <h1 className="text-xl font-bold font-heading" data-testid="app-title">Easy X</h1>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground hidden sm:inline" data-testid="user-name">{user?.name}</span>
          <Button variant="ghost" size="sm" onClick={logout} data-testid="logout-button">
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside
          className={`${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          } lg:translate-x-0 fixed lg:relative z-40 w-64 h-[calc(100vh-3.5rem)] border-r border-border bg-card transition-transform duration-200`}
          data-testid="client-sidebar"
        >
          <div className="h-full flex flex-col">
            <div className="p-4 border-b border-border">
              <Button
                onClick={() => setShowAddClient(true)}
                className="w-full"
                size="sm"
                data-testid="add-client-button"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Client
              </Button>
            </div>

            <ScrollArea className="flex-1 p-2">
              <div className="space-y-1">
                {clients.length === 0 ? (
                  <div className="text-center py-8 text-sm text-muted-foreground" data-testid="no-clients-message">
                    <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    No clients yet
                  </div>
                ) : (
                  clients.map((client) => (
                    <button
                      key={client.id}
                      onClick={() => {
                        setSelectedClient(client);
                        setSidebarOpen(false);
                      }}
                      data-testid={`client-item-${client.id}`}
                      className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                        selectedClient?.id === client.id
                          ? 'bg-primary text-primary-foreground'
                          : 'hover:bg-muted'
                      }`}
                    >
                      <div className="font-medium">{client.name}</div>
                      {client.gstin && (
                        <div className="text-xs opacity-80 font-mono">{client.gstin}</div>
                      )}
                    </button>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>
        </aside>

        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <main className="flex-1 flex overflow-hidden" data-testid="main-workspace">
          {!selectedClient ? (
            <div className="flex-1 flex items-center justify-center" data-testid="no-client-selected">
              <div className="text-center">
                <Users className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <p className="text-lg text-muted-foreground">Select or add a client to get started</p>
              </div>
            </div>
          ) : (
            <>
              <div className="hidden lg:block w-[400px] border-r border-border">
                <ChatPanel />
              </div>
              <div className="flex-1 overflow-auto">
                <ClientWorkspace />
              </div>
            </>
          )}
        </main>
      </div>

      <AddClientDialog
        open={showAddClient}
        onOpenChange={setShowAddClient}
        onSubmit={handleAddClient}
      />
    </div>
  );
}