import React, { useState, useEffect } from 'react';
import { useClient } from '@/contexts/ClientContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import api from '@/services/api';
import { toast } from 'sonner';

export const DocumentsTab = () => {
  const { selectedClient } = useClient();
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (selectedClient) {
      loadDocuments();
    }
  }, [selectedClient]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const response = await api.documents.getAll(selectedClient.id);
      setDocuments(response.data);
    } catch (error) {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('client_id', selectedClient.id);

    try {
      setUploading(true);
      const response = await api.documents.upload(formData);
      toast.success('Document uploaded and processed successfully');
      
      if (response.data.extracted?.confidence) {
        const confidence = response.data.extracted.confidence;
        if (confidence < 0.7) {
          toast.warning(`OCR confidence is low (${(confidence * 100).toFixed(0)}%). Please verify extracted data.`);
        }
      }
      
      await loadDocuments();
    } catch (error) {
      toast.error('Failed to upload document');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="documents-tab">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold font-heading tracking-tight">Documents</h2>
          <p className="text-sm text-muted-foreground">Upload and manage invoices</p>
        </div>
        <div>
          <input
            type="file"
            id="file-upload"
            accept="image/*,.pdf"
            className="hidden"
            onChange={handleFileUpload}
            disabled={uploading}
            data-testid="file-upload-input"
          />
          <Button
            onClick={() => document.getElementById('file-upload').click()}
            disabled={uploading}
            data-testid="upload-document-button"
          >
            <Upload className="w-4 h-4 mr-2" />
            {uploading ? 'Uploading...' : 'Upload Document'}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Uploaded Documents</CardTitle>
          <CardDescription>All documents for {selectedClient?.name}</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-sm text-muted-foreground">Loading...</div>
          ) : documents.length === 0 ? (
            <div className="text-center py-8" data-testid="no-documents-message">
              <FileText className="w-12 h-12 mx-auto mb-3 text-muted-foreground opacity-50" />
              <p className="text-sm text-muted-foreground">No documents uploaded yet</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Filename</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Invoice #</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {documents.map((doc) => (
                    <TableRow key={doc.id} data-testid={`document-${doc.id}`}>
                      <TableCell className="font-medium">{doc.filename}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{doc.file_type}</Badge>
                      </TableCell>
                      <TableCell>
                        {doc.confidence_score ? (
                          <div className="flex items-center gap-2">
                            {doc.confidence_score >= 0.7 ? (
                              <CheckCircle className="w-4 h-4 text-brand-emerald" />
                            ) : (
                              <AlertCircle className="w-4 h-4 text-brand-amber" />
                            )}
                            <span className="text-sm">{(doc.confidence_score * 100).toFixed(0)}%</span>
                          </div>
                        ) : (
                          '-'
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {doc.extracted_data?.invoice_number || '-'}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {doc.extracted_data?.total_amount
                          ? `₹${doc.extracted_data.total_amount.toLocaleString('en-IN')}`
                          : '-'}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {doc.extracted_data?.invoice_date || '-'}
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

export default DocumentsTab;