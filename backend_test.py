import requests
import sys
import json
from datetime import datetime, timedelta
import time

class EasyXAPITester:
    def __init__(self, base_url="https://gst-genius-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = None
        self.client_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, auth_required=True):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if auth_required and self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        if files:
            headers.pop('Content-Type', None)  # Let requests set it for multipart

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method == 'POST':
                if files:
                    response = requests.post(url, headers={k: v for k, v in headers.items() if k != 'Content-Type'}, data=data, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"   ✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.text else {}
                except:
                    return True, {}
            else:
                print(f"   ❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"   ❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health"""
        success, response = self.run_test(
            "API Health Check",
            "GET",
            "",
            200,
            auth_required=False
        )
        return success

    def test_register_user(self):
        """Test user registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        user_data = {
            "email": f"test_user_{timestamp}@example.com",
            "password": "TestPass123!",
            "name": f"Test User {timestamp}",
            "role": "ca"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=user_data,
            auth_required=False
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response.get('user', {}).get('id')
            print(f"   🔑 Token obtained: {self.token[:20]}...")
        
        return success, user_data

    def test_login(self, user_data):
        """Test user login"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={
                "email": user_data["email"],
                "password": user_data["password"]
            },
            auth_required=False
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response.get('user', {}).get('id')
        
        return success

    def test_get_profile(self):
        """Test getting user profile"""
        success, response = self.run_test(
            "Get User Profile",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_create_client(self):
        """Test creating a client"""
        client_data = {
            "name": "Test Company Ltd",
            "gstin": "27AABCU9603R1ZU",
            "business_name": "Test Business"
        }
        
        success, response = self.run_test(
            "Create Client",
            "POST",
            "clients",
            200,
            data=client_data
        )
        
        if success and 'id' in response:
            self.client_id = response['id']
            print(f"   📋 Client created with ID: {self.client_id}")
        
        return success

    def test_get_clients(self):
        """Test getting all clients"""
        success, response = self.run_test(
            "Get All Clients",
            "GET",
            "clients",
            200
        )
        return success

    def test_create_invoice(self):
        """Test creating an invoice"""
        if not self.client_id:
            print("   ⚠️ Skipping - No client ID available")
            return False

        invoice_data = {
            "client_id": self.client_id,
            "invoice_type": "purchase",
            "gstin": "27AABCU9603R1ZU",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-08-15",
            "taxable_value": 1000.0,
            "cgst": 90.0,
            "sgst": 90.0,
            "igst": 0.0,
            "total_amount": 1180.0,
            "vendor_name": "Test Vendor"
        }
        
        success, response = self.run_test(
            "Create Invoice",
            "POST",
            "invoices",
            200,
            data=invoice_data
        )
        return success

    def test_get_invoices(self):
        """Test getting invoices for a client"""
        if not self.client_id:
            print("   ⚠️ Skipping - No client ID available")
            return False

        success, response = self.run_test(
            "Get Invoices",
            "GET",
            "invoices",
            200,
            data={"client_id": self.client_id}
        )
        return success

    def test_get_ledger(self):
        """Test getting ledger entries"""
        if not self.client_id:
            print("   ⚠️ Skipping - No client ID available")
            return False

        success, response = self.run_test(
            "Get Ledger Entries",
            "GET",
            "ledger",
            200,
            data={"client_id": self.client_id}
        )
        return success

    def test_profit_loss_report(self):
        """Test profit & loss report generation"""
        if not self.client_id:
            print("   ⚠️ Skipping - No client ID available")
            return False

        success, response = self.run_test(
            "Generate P&L Report",
            "GET",
            "reports/profit-loss",
            200,
            data={
                "client_id": self.client_id,
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        )
        return success

    def test_balance_sheet_report(self):
        """Test balance sheet report generation"""
        if not self.client_id:
            print("   ⚠️ Skipping - No client ID available")
            return False

        success, response = self.run_test(
            "Generate Balance Sheet",
            "GET",
            "reports/balance-sheet",
            200,
            data={
                "client_id": self.client_id,
                "as_of_date": "2024-08-31"
            }
        )
        return success

    def test_chat_message(self):
        """Test AI chat functionality"""
        if not self.client_id:
            print("   ⚠️ Skipping - No client ID available")
            return False

        success, response = self.run_test(
            "Send Chat Message",
            "POST",
            "chat",
            200,
            data={
                "client_id": self.client_id,
                "content": "Hello, can you help me understand GST compliance?"
            }
        )
        
        if success:
            # Give AI time to respond
            time.sleep(2)
            
        return success

    def test_chat_history(self):
        """Test getting chat history"""
        if not self.client_id:
            print("   ⚠️ Skipping - No client ID available")
            return False

        success, response = self.run_test(
            "Get Chat History",
            "GET",
            "chat/history",
            200,
            data={"client_id": self.client_id}
        )
        return success

    def test_itc_analysis(self):
        """Test ITC mismatch analysis"""
        if not self.client_id:
            print("   ⚠️ Skipping - No client ID available")
            return False

        success, response = self.run_test(
            "Analyze ITC Mismatches",
            "POST",
            f"itc/analyze?client_id={self.client_id}",
            200,
            data={}
        )
        return success

    def test_get_itc_mismatches(self):
        """Test getting ITC mismatches"""
        if not self.client_id:
            print("   ⚠️ Skipping - No client ID available")
            return False

        success, response = self.run_test(
            "Get ITC Mismatches",
            "GET",
            "itc/mismatches",
            200,
            data={"client_id": self.client_id}
        )
        return success

def main():
    print("🚀 Starting Easy X API Tests...")
    print("=" * 60)
    
    tester = EasyXAPITester()
    
    # Test sequence
    tests = [
        ("Health Check", tester.test_health_check),
        ("User Registration", tester.test_register_user),
        ("User Profile", tester.test_get_profile),
        ("Create Client", tester.test_create_client),
        ("Get Clients", tester.test_get_clients),
        ("Create Invoice", tester.test_create_invoice),
        ("Get Invoices", tester.test_get_invoices),
        ("Get Ledger", tester.test_get_ledger),
        ("P&L Report", tester.test_profit_loss_report),
        ("Balance Sheet", tester.test_balance_sheet_report),
        ("Chat Message", tester.test_chat_message),
        ("Chat History", tester.test_chat_history),
        ("ITC Analysis", tester.test_itc_analysis),
        ("Get ITC Mismatches", tester.test_get_itc_mismatches),
    ]
    
    user_data = None
    
    for test_name, test_func in tests:
        try:
            if test_name == "User Registration":
                success, user_data = test_func()
            else:
                success = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} failed with exception: {e}")
            continue
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())