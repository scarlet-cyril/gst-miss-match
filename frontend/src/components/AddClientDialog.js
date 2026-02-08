import React, { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export const AddClientDialog = ({ open, onOpenChange, onSubmit }) => {
  const [formData, setFormData] = useState({
    name: '',
    gstin: '',
    business_name: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
    setFormData({ name: '', gstin: '', business_name: '' });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="add-client-dialog">
        <DialogHeader>
          <DialogTitle>Add New Client</DialogTitle>
          <DialogDescription>Create a new client to manage their finances</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="client-name">Client Name *</Label>
            <Input
              id="client-name"
              data-testid="client-name-input"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Raju Kumar"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="client-gstin">GSTIN</Label>
            <Input
              id="client-gstin"
              data-testid="client-gstin-input"
              value={formData.gstin}
              onChange={(e) => setFormData({ ...formData, gstin: e.target.value })}
              placeholder="e.g., 29ABCDE1234F1Z5"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="client-business">Business Name</Label>
            <Input
              id="client-business"
              data-testid="client-business-input"
              value={formData.business_name}
              onChange={(e) => setFormData({ ...formData, business_name: e.target.value })}
              placeholder="e.g., ABC Enterprises"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} data-testid="cancel-add-client">
              Cancel
            </Button>
            <Button type="submit" data-testid="submit-add-client">Add Client</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default AddClientDialog;