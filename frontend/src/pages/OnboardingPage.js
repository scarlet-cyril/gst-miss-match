import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { UserCircle, Briefcase, Building2, Users } from 'lucide-react';

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [selectedRole, setSelectedRole] = useState('');
  const [customRole, setCustomRole] = useState('');

  const roles = [
    {
      id: 'ca',
      title: 'Chartered Accountant (CA)',
      icon: Briefcase,
      description: 'Professional CA managing multiple clients'
    },
    {
      id: 'gst_practitioner',
      title: 'GST Practitioner',
      icon: Building2,
      description: 'GST compliance and filing specialist'
    },
    {
      id: 'business_owner',
      title: 'Individual / Business Owner',
      icon: UserCircle,
      description: 'Managing your own business finances'
    },
    {
      id: 'firm',
      title: 'Accounting Firm',
      icon: Users,
      description: 'Multi-user accounting firm'
    }
  ];

  const handleContinue = () => {
    const roleToSave = selectedRole === 'other' ? customRole : selectedRole;
    localStorage.setItem('userRole', roleToSave);
    navigate('/auth');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-3xl shadow-2xl" data-testid="onboarding-screen">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            <div className="w-20 h-20 bg-primary rounded-full flex items-center justify-center mx-auto">
              <UserCircle className="w-12 h-12 text-white" />
            </div>
          </div>
          <CardTitle className="text-3xl font-bold font-heading">Welcome to Easy X</CardTitle>
          <CardDescription className="text-lg">The Financial Cockpit for Modern CAs</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-center">
            <h3 className="text-xl font-semibold mb-2">Who are you?</h3>
            <p className="text-sm text-muted-foreground">Select your role to personalize your experience</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {roles.map((role) => {
              const Icon = role.icon;
              return (
                <button
                  key={role.id}
                  data-testid={`role-${role.id}`}
                  onClick={() => setSelectedRole(role.id)}
                  className={`p-6 border-2 rounded-lg text-left transition-all hover:shadow-md ${
                    selectedRole === role.id
                      ? 'border-primary bg-primary/5 shadow-md'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-lg ${
                      selectedRole === role.id ? 'bg-primary text-white' : 'bg-muted'
                    }`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold mb-1">{role.title}</h4>
                      <p className="text-xs text-muted-foreground">{role.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="space-y-2">
            <button
              data-testid="role-other"
              onClick={() => setSelectedRole('other')}
              className={`w-full p-4 border-2 rounded-lg text-left transition-all hover:shadow-md ${
                selectedRole === 'other'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded ${
                  selectedRole === 'other' ? 'bg-primary text-white' : 'bg-muted'
                }`}>
                  <Users className="w-5 h-5" />
                </div>
                <span className="font-medium">Others (Specify)</span>
              </div>
            </button>
            
            {selectedRole === 'other' && (
              <Input
                placeholder="Enter your role..."
                value={customRole}
                onChange={(e) => setCustomRole(e.target.value)}
                data-testid="custom-role-input"
                className="mt-2"
              />
            )}
          </div>

          <Button
            onClick={handleContinue}
            disabled={!selectedRole || (selectedRole === 'other' && !customRole)}
            className="w-full h-12 text-lg"
            data-testid="continue-button"
          >
            Continue to Easy X
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}