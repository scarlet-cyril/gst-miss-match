import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useClient } from '@/contexts/ClientContext';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Users, Plus, LogOut, Menu, X, Trash2, AlertCircle, FileText } from 'lucide-react';
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
  const [clientToDelete, setClientToDelete] = useState(null);
  const [clientStats, setClientStats] = useState({});

  useEffect(() => {
    loadClients();
  }, []);

  useEffect(() => {
    if (clients.length > 0) {
      loadAllClientStats();
    }
  }, [clients]);

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

  const loadAllClientStats = async () => {
    const stats = {};
    for (const client of clients) {
      try {
        const [invoicesRes, itcRes] = await Promise.all([
          api.invoices.getAll(client.id),
          api.itc.getMismatches(client.id)
        ]);
        stats[client.id] = {
          pendingInvoices: invoicesRes.data.length,
          itcAlerts: itcRes.data.length,
          status: client.status || 'active'
        };
      } catch (error) {
        stats[client.id] = {
          pendingInvoices: 0,
          itcAlerts: 0,
          status: 'active'
        };
      }
    }
    setClientStats(stats);
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

  const handleDeleteClick = (client, e) => {
    e.stopPropagation();
    setClientToDelete(client);
  };

  const handleDeleteConfirm = async () => {
    if (!clientToDelete) return;

    try {
      await api.clients.delete(clientToDelete.id);
      
      const updatedClients = clients.filter(c => c.id !== clientToDelete.id);
      setClients(updatedClients);
      
      if (selectedClient?.id === clientToDelete.id) {
        setSelectedClient(updatedClients.length > 0 ? updatedClients[0] : null);
      }
      
      toast.success('Client deleted successfully');
      setClientToDelete(null);
    } catch (error) {
      toast.error('Failed to delete client');
    }
  };

  const getStatusBadge = (clientId) => {
    const stats = clientStats[clientId];
    if (!stats) return null;

    if (stats.itcAlerts > 0) {
      return (
        <div className="flex items-center gap-1 text-xs text-red-600">
          <AlertCircle className="w-3 h-3" />
          <span>ITC alerts: {stats.itcAlerts}</span>
        </div>
      );
    }

    if (stats.pendingInvoices > 0) {
      return (
        <div className="flex items-center gap-1 text-xs text-amber-600">
          <FileText className="w-3 h-3" />
          <span>{stats.pendingInvoices} invoices pending</span>
        </div>
      );
    }

    return (
      <div className="text-xs text-green-600">
        ✓ All clear
      </div>
    );
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
              <div className="space-y-2">
                {clients.length === 0 ? (
                  <div className="text-center py-8 text-sm text-muted-foreground" data-testid="no-clients-message">
                    <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    No clients yet
                  </div>
                ) : (
                  clients.map((client) => (
                    <div
                      key={client.id}
                      data-testid={`client-item-${client.id}`}
                      className={`group relative rounded-lg border transition-all ${
                        selectedClient?.id === client.id
                          ? 'bg-primary/10 border-primary shadow-sm'
                          : 'border-border hover:border-primary/50 hover:bg-muted/50'
                      }`}
                    >
                      <button
                        onClick={() => {
                          setSelectedClient(client);
                          setSidebarOpen(false);
                        }}
                        className="w-full text-left p-3 pr-10"
                      >
                        <div className="font-medium text-sm mb-1">{client.name}</div>
                        {client.gstin && (
                          <div className="text-xs text-muted-foreground font-mono mb-1">{client.gstin}</div>
                        )}
                        {getStatusBadge(client.id)}
                      </button>
                      
                      <button
                        onClick={(e) => handleDeleteClick(client, e)}
                        data-testid={`delete-client-${client.id}`}
                        className="absolute top-3 right-3 p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-950 text-red-600 hover:text-red-700 transition-colors"
                        title="Delete client"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
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

      <AlertDialog open={!!clientToDelete} onOpenChange={() => setClientToDelete(null)}>
        <AlertDialogContent data-testid="delete-confirmation-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Client</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{clientToDelete?.name}</strong>?
              <br />
              <span className="text-red-600 font-medium">This action cannot be undone.</span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="cancel-delete-button">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              data-testid="confirm-delete-button"
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Yes, Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}