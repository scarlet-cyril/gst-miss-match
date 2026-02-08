import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MessageSquare, LayoutDashboard, BookOpen, AlertTriangle, FileText, FolderOpen } from 'lucide-react';
import ChatTab from '@/components/workspace/ChatTab';
import DashboardTab from '@/components/workspace/DashboardTab';
import LedgerTab from '@/components/workspace/LedgerTab';
import ITCTab from '@/components/workspace/ITCTab';
import ReportsTab from '@/components/workspace/ReportsTab';
import DocumentsTab from '@/components/workspace/DocumentsTab';

export const ClientWorkspace = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="h-full" data-testid="client-workspace">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
        <div className="border-b border-border bg-card px-4">
          <TabsList className="h-12 bg-transparent">
            <TabsTrigger value="dashboard" className="gap-2" data-testid="tab-dashboard">
              <LayoutDashboard className="w-4 h-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </TabsTrigger>
            <TabsTrigger value="chat" className="gap-2 lg:hidden" data-testid="tab-chat">
              <MessageSquare className="w-4 h-4" />
              <span className="hidden sm:inline">Chat</span>
            </TabsTrigger>
            <TabsTrigger value="ledger" className="gap-2" data-testid="tab-ledger">
              <BookOpen className="w-4 h-4" />
              <span className="hidden sm:inline">Ledger</span>
            </TabsTrigger>
            <TabsTrigger value="itc" className="gap-2" data-testid="tab-itc">
              <AlertTriangle className="w-4 h-4" />
              <span className="hidden sm:inline">ITC</span>
            </TabsTrigger>
            <TabsTrigger value="reports" className="gap-2" data-testid="tab-reports">
              <FileText className="w-4 h-4" />
              <span className="hidden sm:inline">Reports</span>
            </TabsTrigger>
            <TabsTrigger value="documents" className="gap-2" data-testid="tab-documents">
              <FolderOpen className="w-4 h-4" />
              <span className="hidden sm:inline">Documents</span>
            </TabsTrigger>
          </TabsList>
        </div>

        <div className="flex-1 overflow-auto bg-muted/20">
          <TabsContent value="dashboard" className="mt-0 h-full">
            <DashboardTab />
          </TabsContent>
          <TabsContent value="chat" className="mt-0 h-full lg:hidden">
            <ChatTab />
          </TabsContent>
          <TabsContent value="ledger" className="mt-0 h-full">
            <LedgerTab />
          </TabsContent>
          <TabsContent value="itc" className="mt-0 h-full">
            <ITCTab />
          </TabsContent>
          <TabsContent value="reports" className="mt-0 h-full">
            <ReportsTab />
          </TabsContent>
          <TabsContent value="documents" className="mt-0 h-full">
            <DocumentsTab />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
};

export default ClientWorkspace;