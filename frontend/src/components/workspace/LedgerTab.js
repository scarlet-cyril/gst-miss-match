import React, { useState, useEffect } from 'react';
import { useClient } from '@/contexts/ClientContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { RefreshCw, Info } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import api from '@/services/api';
import { toast } from 'sonner';

export const LedgerTab = () => {
  const { selectedClient } = useClient();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedClient) {
      loadLedger();
    }
  }, [selectedClient]);

  const loadLedger = async () => {
    try {
      setLoading(true);
      console.log('[Ledger] Loading entries for client:', selectedClient.id);
      const response = await api.ledger.getAll(selectedClient.id);
      console.log('[Ledger] Loaded entries:', response.data);
      setEntries(response.data);
      if (response.data.length > 0) {
        toast.success(`Loaded ${response.data.length} ledger entries`);
      }
    } catch (error) {
      console.error('[Ledger] Error loading:', error);
      toast.error('Failed to load ledger: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="ledger-tab">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold font-heading tracking-tight">Ledger Entries</h2>
          <p className="text-sm text-muted-foreground">Double-entry accounting ledger for {selectedClient?.name}</p>
        </div>
        <Button onClick={loadLedger} disabled={loading} size="sm" variant="outline" data-testid="refresh-ledger-button">
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Entries</CardTitle>
          <CardDescription>
            Debit and credit entries for {selectedClient?.name}
            {entries.length > 0 && <span className="ml-2 text-primary font-semibold">({entries.length} entries)</span>}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-sm text-muted-foreground">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
              Loading ledger entries...
            </div>
          ) : entries.length === 0 ? (
            <div className="text-center py-8" data-testid="no-entries-message">
              <div className="text-sm text-muted-foreground mb-2">No ledger entries yet.</div>
              <div className="text-xs text-muted-foreground">
                Try: Upload invoices to auto-generate entries, or ask the AI chat to "create a ledger entry".
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Account</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Debit (₹)</TableHead>
                    <TableHead className="text-right">Credit (₹)</TableHead>
                    <TableHead className="text-center">Info</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {entries.map((entry) => (
                    <TableRow key={entry.id} data-testid={`ledger-entry-${entry.id}`}>
                      <TableCell className="font-mono text-sm">{entry.entry_date}</TableCell>
                      <TableCell className="font-medium">{entry.account_name}</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium capitalize bg-muted">
                          {entry.account_type}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                        {entry.description || '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {entry.debit > 0 ? entry.debit.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {entry.credit > 0 ? entry.credit.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : '-'}
                      </TableCell>
                      <TableCell className="text-center">
                        {entry.explanation && (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-6 w-6">
                                  <Info className="w-3 h-3" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs">
                                <p className="text-xs">{entry.explanation}</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default LedgerTab;
