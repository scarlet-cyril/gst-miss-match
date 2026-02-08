import React, { useState, useEffect } from 'react';
import { useClient } from '@/contexts/ClientContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowUpRight, ArrowDownRight, DollarSign, TrendingUp, FileText, Upload } from 'lucide-react';
import api from '@/services/api';
import { toast } from 'sonner';

export const DashboardTab = () => {
  const { selectedClient } = useClient();
  const [stats, setStats] = useState({
    income: 0,
    expenses: 0,
    profit: 0,
    invoices: 0,
    documents: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (selectedClient) {
      loadStats();
    }
  }, [selectedClient]);

  const loadStats = async () => {
    try {
      setLoading(true);
      const [plResponse, invoicesResponse, docsResponse] = await Promise.all([
        api.reports.profitLoss(selectedClient.id, '', ''),
        api.invoices.getAll(selectedClient.id),
        api.documents.getAll(selectedClient.id)
      ]);

      setStats({
        income: plResponse.data.income || 0,
        expenses: plResponse.data.expenses || 0,
        profit: plResponse.data.profit || 0,
        invoices: invoicesResponse.data.length || 0,
        documents: docsResponse.data.length || 0
      });
    } catch (error) {
      toast.error('Failed to load dashboard stats');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="dashboard-tab">
      <div>
        <h2 className="text-2xl font-bold font-heading tracking-tight" data-testid="client-dashboard-title">
          {selectedClient?.name}
        </h2>
        <p className="text-sm text-muted-foreground">
          {selectedClient?.business_name || 'Individual Client'}
          {selectedClient?.gstin && <span className="ml-2 font-mono">{selectedClient.gstin}</span>}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card data-testid="income-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Income</CardTitle>
            <ArrowUpRight className="w-4 h-4 text-brand-emerald" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono" data-testid="income-value">
              ₹{stats.income.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </CardContent>
        </Card>

        <Card data-testid="expenses-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Expenses</CardTitle>
            <ArrowDownRight className="w-4 h-4 text-brand-rose" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono" data-testid="expenses-value">
              ₹{stats.expenses.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </CardContent>
        </Card>

        <Card data-testid="profit-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Net Profit/Loss</CardTitle>
            <TrendingUp className="w-4 h-4 text-brand-indigo" />
          </CardHeader>
          <CardContent>
            <div
              className={`text-2xl font-bold font-mono ${
                stats.profit >= 0 ? 'text-brand-emerald' : 'text-brand-rose'
              }`}
              data-testid="profit-value"
            >
              ₹{stats.profit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </CardContent>
        </Card>

        <Card data-testid="invoices-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Invoices</CardTitle>
            <FileText className="w-4 h-4 text-brand-teal" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold" data-testid="invoices-count">{stats.invoices}</div>
          </CardContent>
        </Card>

        <Card data-testid="documents-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Documents</CardTitle>
            <Upload className="w-4 h-4 text-brand-amber" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold" data-testid="documents-count">{stats.documents}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
          <CardDescription>Common tasks for {selectedClient?.name}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              className="p-4 border border-border rounded-lg hover:bg-muted transition-colors text-left"
              data-testid="quick-action-upload"
            >
              <Upload className="w-5 h-5 mb-2 text-brand-indigo" />
              <div className="font-medium text-sm">Upload Invoice</div>
              <div className="text-xs text-muted-foreground">Add new document</div>
            </button>
            <button
              className="p-4 border border-border rounded-lg hover:bg-muted transition-colors text-left"
              data-testid="quick-action-report"
            >
              <FileText className="w-5 h-5 mb-2 text-brand-teal" />
              <div className="font-medium text-sm">Generate Report</div>
              <div className="text-xs text-muted-foreground">P&L or Balance Sheet</div>
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default DashboardTab;