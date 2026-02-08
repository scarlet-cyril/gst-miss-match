import React, { useState } from 'react';
import { useClient } from '@/contexts/ClientContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FileText, Download, TrendingUp, Scale } from 'lucide-react';
import api from '@/services/api';
import { toast } from 'sonner';

export const ReportsTab = () => {
  const { selectedClient } = useClient();
  const [plReport, setPlReport] = useState(null);
  const [bsReport, setBsReport] = useState(null);
  const [plDates, setPlDates] = useState({ start: '', end: '' });
  const [bsDate, setBsDate] = useState('');
  const [loading, setLoading] = useState(false);

  const generatePL = async () => {
    try {
      setLoading(true);
      const response = await api.reports.profitLoss(
        selectedClient.id,
        plDates.start,
        plDates.end
      );
      setPlReport(response.data);
      toast.success('P&L report generated');
    } catch (error) {
      toast.error('Failed to generate P&L report');
    } finally {
      setLoading(false);
    }
  };

  const generateBS = async () => {
    try {
      setLoading(true);
      const response = await api.reports.balanceSheet(selectedClient.id, bsDate);
      setBsReport(response.data);
      toast.success('Balance Sheet generated');
    } catch (error) {
      toast.error('Failed to generate Balance Sheet');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="reports-tab">
      <div>
        <h2 className="text-2xl font-bold font-heading tracking-tight">Financial Reports</h2>
        <p className="text-sm text-muted-foreground">Generate P&L and Balance Sheet reports</p>
      </div>

      <Tabs defaultValue="pl" className="w-full">
        <TabsList>
          <TabsTrigger value="pl" data-testid="pl-report-tab">
            <TrendingUp className="w-4 h-4 mr-2" />
            Profit & Loss
          </TabsTrigger>
          <TabsTrigger value="bs" data-testid="bs-report-tab">
            <Scale className="w-4 h-4 mr-2" />
            Balance Sheet
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pl" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Generate Profit & Loss</CardTitle>
              <CardDescription>Select date range for the report</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="pl-start">Start Date</Label>
                  <Input
                    id="pl-start"
                    type="date"
                    data-testid="pl-start-date"
                    value={plDates.start}
                    onChange={(e) => setPlDates({ ...plDates, start: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pl-end">End Date</Label>
                  <Input
                    id="pl-end"
                    type="date"
                    data-testid="pl-end-date"
                    value={plDates.end}
                    onChange={(e) => setPlDates({ ...plDates, end: e.target.value })}
                  />
                </div>
              </div>
              <Button onClick={generatePL} disabled={loading} data-testid="generate-pl-button">
                <FileText className="w-4 h-4 mr-2" />
                {loading ? 'Generating...' : 'Generate Report'}
              </Button>
            </CardContent>
          </Card>

          {plReport && (
            <Card data-testid="pl-report-result">
              <CardHeader>
                <CardTitle>Profit & Loss Statement</CardTitle>
                <CardDescription>
                  {plReport.period?.start && plReport.period?.end
                    ? `${plReport.period.start} to ${plReport.period.end}`
                    : 'All time'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between items-center py-2 border-b">
                    <span className="font-medium">Total Income</span>
                    <span className="font-mono text-brand-emerald" data-testid="pl-income">
                      ₹{plReport.income.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b">
                    <span className="font-medium">Total Expenses</span>
                    <span className="font-mono text-brand-rose" data-testid="pl-expenses">
                      ₹{plReport.expenses.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-3 border-t-2 border-primary">
                    <span className="font-bold text-lg">Net Profit/Loss</span>
                    <span
                      className={`font-mono font-bold text-lg ${
                        plReport.profit >= 0 ? 'text-brand-emerald' : 'text-brand-rose'
                      }`}
                      data-testid="pl-profit"
                    >
                      ₹{plReport.profit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="bs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Generate Balance Sheet</CardTitle>
              <CardDescription>Select as-of date for the report</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="bs-date">As of Date</Label>
                <Input
                  id="bs-date"
                  type="date"
                  data-testid="bs-date"
                  value={bsDate}
                  onChange={(e) => setBsDate(e.target.value)}
                />
              </div>
              <Button onClick={generateBS} disabled={loading} data-testid="generate-bs-button">
                <FileText className="w-4 h-4 mr-2" />
                {loading ? 'Generating...' : 'Generate Report'}
              </Button>
            </CardContent>
          </Card>

          {bsReport && (
            <Card data-testid="bs-report-result">
              <CardHeader>
                <CardTitle>Balance Sheet</CardTitle>
                <CardDescription>
                  As of {bsReport.as_of_date || 'current date'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between items-center py-2 border-b">
                    <span className="font-medium">Total Assets</span>
                    <span className="font-mono" data-testid="bs-assets">
                      ₹{bsReport.assets.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b">
                    <span className="font-medium">Total Liabilities</span>
                    <span className="font-mono" data-testid="bs-liabilities">
                      ₹{bsReport.liabilities.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b">
                    <span className="font-medium">Total Equity</span>
                    <span className="font-mono" data-testid="bs-equity">
                      ₹{bsReport.equity.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ReportsTab;