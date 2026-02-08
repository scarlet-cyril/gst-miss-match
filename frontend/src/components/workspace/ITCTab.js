import React, { useState, useEffect } from 'react';
import { useClient } from '@/contexts/ClientContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import api from '@/services/api';
import { toast } from 'sonner';

export const ITCTab = () => {
  const { selectedClient } = useClient();
  const [mismatches, setMismatches] = useState([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedClient) {
      loadMismatches();
    }
  }, [selectedClient]);

  const loadMismatches = async () => {
    try {
      setLoading(true);
      const response = await api.itc.getMismatches(selectedClient.id);
      setMismatches(response.data);
    } catch (error) {
      toast.error('Failed to load ITC mismatches');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    try {
      setAnalyzing(true);
      const response = await api.itc.analyze(selectedClient.id);
      toast.success(`Analyzed ${response.data.analyzed_count} invoices. Found ${response.data.mismatches} issues.`);
      await loadMismatches();
    } catch (error) {
      toast.error('Failed to analyze ITC');
    } finally {
      setAnalyzing(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'matched':
        return <CheckCircle className="w-4 h-4 text-brand-emerald" />;
      case 'mismatched':
        return <AlertTriangle className="w-4 h-4 text-brand-amber" />;
      case 'missing':
        return <XCircle className="w-4 h-4 text-brand-rose" />;
      default:
        return null;
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="itc-tab">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold font-heading tracking-tight">ITC Mismatch Detection</h2>
          <p className="text-sm text-muted-foreground">Identify input tax credit issues</p>
        </div>
        <Button onClick={handleAnalyze} disabled={analyzing} data-testid="analyze-itc-button">
          {analyzing ? 'Analyzing...' : 'Run Analysis'}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Mismatch Summary</CardTitle>
          <CardDescription>Issues found in purchase invoices for {selectedClient?.name}</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-sm text-muted-foreground">Loading...</div>
          ) : mismatches.length === 0 ? (
            <div className="text-center py-8 text-sm text-muted-foreground" data-testid="no-mismatches-message">
              No mismatches found. Run analysis to detect issues.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>GSTIN</TableHead>
                    <TableHead>Invoice No</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Tax Amount</TableHead>
                    <TableHead>Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mismatches.map((mismatch) => (
                    <TableRow key={mismatch.id} data-testid={`itc-mismatch-${mismatch.id}`}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(mismatch.status)}
                          <Badge
                            variant={mismatch.status === 'matched' ? 'default' : 'destructive'}
                            className="capitalize"
                          >
                            {mismatch.status}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{mismatch.gstin}</TableCell>
                      <TableCell className="font-mono text-sm">{mismatch.invoice_number}</TableCell>
                      <TableCell className="font-mono text-sm">{mismatch.invoice_date || '-'}</TableCell>
                      <TableCell className="text-right font-mono">
                        ₹{mismatch.tax_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-xs">
                        {mismatch.reason || 'No reason provided'}
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

export default ITCTab;