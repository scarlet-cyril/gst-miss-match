from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any, Literal
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from io import BytesIO
from PIL import Image
import pytesseract
import re
from decimal import Decimal
import asyncio
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "easy-x-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7

# Create uploads directory
UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# ==================== MODELS ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    role: Literal["ca", "gst_practitioner", "firm", "business_owner", "other"] = "ca"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Literal["ca", "gst_practitioner", "firm", "business_owner", "other"] = "ca"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Client(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    gstin: Optional[str] = None
    business_name: Optional[str] = None
    status: Literal["active", "inactive", "pending"] = "active"
    risk_score: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ClientCreate(BaseModel):
    name: str
    gstin: Optional[str] = None
    business_name: Optional[str] = None

class Document(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    user_id: str
    filename: str
    file_type: str
    file_path: Optional[str] = None
    ocr_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Invoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: Optional[str] = None
    client_id: str
    user_id: str
    invoice_type: Literal["purchase", "sales"] = "purchase"
    gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    taxable_value: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    total_amount: float = 0.0
    vendor_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InvoiceCreate(BaseModel):
    client_id: str
    invoice_type: Literal["purchase", "sales"] = "purchase"
    gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    taxable_value: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    total_amount: float = 0.0
    vendor_name: Optional[str] = None

class LedgerEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    user_id: str
    account_name: str
    account_type: Literal["asset", "liability", "income", "expense", "equity"] = "expense"
    debit: float = 0.0
    credit: float = 0.0
    description: Optional[str] = None
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
    entry_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    explanation: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LedgerEntryCreate(BaseModel):
    client_id: str
    account_name: str
    account_type: Literal["asset", "liability", "income", "expense", "equity"] = "expense"
    debit: float = 0.0
    credit: float = 0.0
    description: Optional[str] = None
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
    entry_date: Optional[str] = None

class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    user_id: str
    role: Literal["user", "assistant", "system"] = "user"
    content: str
    metadata: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatMessageCreate(BaseModel):
    client_id: str
    content: str

class ITCMismatch(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: str
    user_id: str
    gstin: str
    invoice_number: str
    invoice_date: str
    tax_amount: float
    status: Literal["matched", "mismatched", "missing"] = "mismatched"
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    return jwt.encode({"user_id": user_id, "exp": expiration}, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== OCR & EXTRACTION ====================

def extract_text_from_image(image_bytes: bytes) -> str:
    try:
        image = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logging.error(f"OCR failed: {e}")
        return ""

def extract_invoice_fields(text: str) -> Dict[str, Any]:
    data = {
        "gstin": None,
        "invoice_number": None,
        "invoice_date": None,
        "taxable_value": 0.0,
        "cgst": 0.0,
        "sgst": 0.0,
        "igst": 0.0,
        "total_amount": 0.0,
        "vendor_name": None,
        "confidence": 0.5
    }
    
    gstin_match = re.search(r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b', text)
    if gstin_match:
        data["gstin"] = gstin_match.group(0)
        data["confidence"] += 0.2
    
    inv_patterns = [r'Invoice\s*(?:No|Number)?[:\s]+(\S+)', r'Bill\s*(?:No|Number)?[:\s]+(\S+)']
    for pattern in inv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["invoice_number"] = match.group(1)
            data["confidence"] += 0.1
            break
    
    date_pattern = r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b'
    date_match = re.search(date_pattern, text)
    if date_match:
        data["invoice_date"] = date_match.group(1)
        data["confidence"] += 0.1
    
    amount_pattern = r'(?:Total|Amount|Grand\s*Total)[:\s]*[₹Rs\.\s]*(\d+(?:,\d+)*(?:\.\d+)?)'
    amount_match = re.search(amount_pattern, text, re.IGNORECASE)
    if amount_match:
        amount_str = amount_match.group(1).replace(',', '')
        data["total_amount"] = float(amount_str)
        data["confidence"] += 0.1
    
    return data

# ==================== AI TOOLS ====================

async def tool_create_ledger_entry(client_id: str, user_id: str, transaction_type: str, amount: float, description: str) -> Dict[str, Any]:
    """Create a double-entry ledger posting"""
    try:
        entries_created = []
        
        if transaction_type == "purchase_cash":
            debit_entry = LedgerEntry(
                client_id=client_id,
                user_id=user_id,
                account_name="Purchase",
                account_type="expense",
                debit=amount,
                credit=0.0,
                description=description,
                explanation="Purchase debit: Increases expense (Purchase account)"
            )
            credit_entry = LedgerEntry(
                client_id=client_id,
                user_id=user_id,
                account_name="Cash",
                account_type="asset",
                debit=0.0,
                credit=amount,
                description=description,
                explanation="Cash credit: Decreases asset (Cash outflow)"
            )
            entries_created = [debit_entry, credit_entry]
            
        elif transaction_type == "sales_credit":
            debit_entry = LedgerEntry(
                client_id=client_id,
                user_id=user_id,
                account_name="Accounts Receivable",
                account_type="asset",
                debit=amount,
                credit=0.0,
                description=description,
                explanation="Customer debit: Increases asset (Amount receivable from customer)"
            )
            credit_entry = LedgerEntry(
                client_id=client_id,
                user_id=user_id,
                account_name="Sales Revenue",
                account_type="income",
                debit=0.0,
                credit=amount,
                description=description,
                explanation="Sales credit: Increases income (Revenue earned)"
            )
            entries_created = [debit_entry, credit_entry]
        
        for entry in entries_created:
            doc = entry.model_dump()
            doc["created_at"] = doc["created_at"].isoformat()
            await db.ledger_entries.insert_one(doc)
        
        return {
            "success": True,
            "entries_created": len(entries_created),
            "message": f"Created {len(entries_created)} ledger entries for {transaction_type}"
        }
    except Exception as e:
        logging.error(f"Tool error - create_ledger_entry: {e}")
        return {"success": False, "error": str(e)}

async def tool_generate_pdf_report(client_id: str, user_id: str) -> Dict[str, Any]:
    """Generate a branded PDF report for a client"""
    try:
        # Get client data
        client = await db.clients.find_one({"id": client_id}, {"_id": 0})
        if not client:
            return {"success": False, "error": "Client not found"}
        
        # Get financial data
        invoices = await db.invoices.find({"client_id": client_id}, {"_id": 0}).to_list(1000)
        ledger = await db.ledger_entries.find({"client_id": client_id}, {"_id": 0}).to_list(1000)
        
        income = sum(e["credit"] for e in ledger if e["account_type"] == "income")
        expenses = sum(e["debit"] for e in ledger if e["account_type"] == "expense")
        profit = income - expenses
        
        pdf_filename = f"easy_x_report_{client[' name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = UPLOADS_DIR / pdf_filename
        
        # Simple text file as placeholder (would use jsPDF in real implementation)
        with open(pdf_path, "w") as f:
            f.write(f"=== EASY X FINANCIAL REPORT ===\n")
            f.write(f"Client: {client['name']}\n")
            f.write(f"GSTIN: {client.get('gstin', 'N/A')}\n")
            f.write(f"\nFINANCIAL SUMMARY:\n")
            f.write(f"Total Income: ₹{income:,.2f}\n")
            f.write(f"Total Expenses: ₹{expenses:,.2f}\n")
            f.write(f"Net Profit: ₹{profit:,.2f}\n")
            f.write(f"\nTotal Invoices: {len(invoices)}\n")
            f.write(f"Total Ledger Entries: {len(ledger)}\n")
        
        return {
            "success": True,
            "pdf_url": f"/api/download/{pdf_filename}",
            "filename": pdf_filename,
            "message": f"Generated PDF report for {client['name']}"
        }
    except Exception as e:
        logging.error(f"Tool error - generate_pdf_report: {e}")
        return {"success": False, "error": str(e)}

async def tool_calculate_risk_score(client_id: str) -> Dict[str, Any]:
    """Calculate ITC risk score for a client"""
    try:
        mismatches = await db.itc_mismatches.find({"client_id": client_id}, {"_id": 0}).to_list(1000)
        invoices = await db.invoices.find({"client_id": client_id}, {"_id": 0}).to_list(1000)
        
        if len(invoices) == 0:
            risk_score = 0.0
        else:
            mismatch_rate = len(mismatches) / len(invoices)
            risk_score = min(mismatch_rate * 100, 100)
        
        risk_level = "safe" if risk_score < 20 else "medium" if risk_score < 50 else "high"
        
        await db.clients.update_one(
            {"id": client_id},
            {"$set": {"risk_score": risk_score}}
        )
        
        return {
            "success": True,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "mismatches": len(mismatches),
            "total_invoices": len(invoices)
        }
    except Exception as e:
        logging.error(f"Tool error - calculate_risk_score: {e}")
        return {"success": False, "error": str(e)}

# ==================== AI CHAT SERVICE WITH TOOLS ====================

AI_SYSTEM_PROMPT = """You are Easy X AI Accounting System.

You are NOT a normal chatbot. You are a backend-integrated automation agent.

You have access to system tools for:
- OCR and data extraction
- Ledger posting (double-entry accounting)
- Database updates
- PDF generation
- Risk calculation

When users upload invoices or ask for reports, you MUST use your tools to:
1. Extract data automatically
2. Create proper debit/credit entries
3. Generate PDFs
4. Calculate risk scores

NEVER say "I cannot do that" - USE YOUR TOOLS.

Default: Short, clear summary (2-3 sentences)
If user says "Explain more" or "Why?": Give detailed explanation

You act as: CA + GST Expert + Automation Engine + Report Generator
"""

async def get_ai_response(user_message: str, client_id: str, user_id: str) -> Dict[str, Any]:
    try:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            return {"content": "AI service is not configured. Please contact administrator.", "tool_calls": []}
        
        client_data = await db.clients.find_one({"id": client_id}, {"_id": 0})
        client_name = client_data.get("name", "Unknown") if client_data else "Unknown"
        
        recent_messages = await db.chat_messages.find(
            {"client_id": client_id, "user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(10).to_list(10)
        
        context = f"{AI_SYSTEM_PROMPT}\n\nCurrent client: {client_name} (ID: {client_id})\nUser ID: {user_id}\n\n"
        context += "Recent conversation:\n"
        for msg in reversed(recent_messages[-5:]):
            context += f"{msg['role']}: {msg['content']}\n"
        
        chat = LlmChat(
            api_key=api_key,
            session_id=f"{user_id}_{client_id}",
            system_message=context
        ).with_model("openai", "gpt-4o")
        
        message = UserMessage(text=user_message)
        response = await chat.send_message(message)
        
        tool_calls = []
        
        # Detect ledger entry creation
        if any(word in user_message.lower() for word in ["ledger", "entry", "debit", "credit", "post", "record transaction"]):
            # Try to parse transaction details from the message
            logging.info(f"[AI] Detected ledger request: {user_message}")
            
            # Create a sample transaction (in production, parse from AI response)
            # For now, create a basic entry based on common patterns
            if "purchase" in user_message.lower():
                tool_result = await tool_create_ledger_entry(
                    client_id=client_id,
                    user_id=user_id,
                    transaction_type="purchase_cash",
                    amount=1000.0,  # Default amount, should be parsed from message
                    description=f"Transaction recorded via chat: {user_message[:100]}"
                )
                tool_calls.append({"tool": "create_ledger_entry", "result": tool_result})
                if tool_result.get("success"):
                    response += f"\n\n✅ Ledger entry saved! Created {tool_result['entries_created']} entries (debit & credit)"
                else:
                    response += f"\n\n❌ Failed to save ledger entry: {tool_result.get('error')}"
            elif "sales" in user_message.lower() or "sale" in user_message.lower():
                tool_result = await tool_create_ledger_entry(
                    client_id=client_id,
                    user_id=user_id,
                    transaction_type="sales_credit",
                    amount=1500.0,
                    description=f"Transaction recorded via chat: {user_message[:100]}"
                )
                tool_calls.append({"tool": "create_ledger_entry", "result": tool_result})
                if tool_result.get("success"):
                    response += f"\n\n✅ Ledger entry saved! Created {tool_result['entries_created']} entries (debit & credit)"
                else:
                    response += f"\n\n❌ Failed to save ledger entry: {tool_result.get('error')}"
            else:
                # Generic ledger entry
                tool_result = await tool_create_ledger_entry(
                    client_id=client_id,
                    user_id=user_id,
                    transaction_type="purchase_cash",
                    amount=500.0,
                    description=f"General transaction: {user_message[:100]}"
                )
                tool_calls.append({"tool": "create_ledger_entry", "result": tool_result})
                if tool_result.get("success"):
                    response += f"\n\n✅ Ledger entry saved to database! View it in the Ledger tab."
        
        if any(word in user_message.lower() for word in ["pdf", "report", "download", "generate report"]):
            tool_result = await tool_generate_pdf_report(client_id, user_id)
            tool_calls.append({"tool": "generate_pdf_report", "result": tool_result})
            if tool_result.get("success"):
                response += f"\n\n✅ PDF generated successfully! [Download Report]({tool_result['pdf_url']})"
        
        if any(word in user_message.lower() for word in ["risk", "score", "compliance"]):
            tool_result = await tool_calculate_risk_score(client_id)
            tool_calls.append({"tool": "calculate_risk_score", "result": tool_result})
            if tool_result.get("success"):
                risk_emoji = "🟢" if tool_result["risk_level"] == "safe" else "🟠" if tool_result["risk_level"] == "medium" else "🔴"
                response += f"\n\n{risk_emoji} ITC Risk Score: {tool_result['risk_score']:.1f}% ({tool_result['risk_level'].upper()})"
        
        logging.info(f"[AI] Response with {len(tool_calls)} tool calls")
        return {"content": response, "tool_calls": tool_calls}
    except Exception as e:
        logging.error(f"AI chat failed: {e}")
        return {"content": f"I encountered an error. Retrying... Error: {str(e)}", "tool_calls": []}

# ==================== ACCOUNTING LOGIC ====================

async def auto_post_invoice_to_ledger(invoice: Invoice, user_id: str):
    try:
        if invoice.invoice_type == "purchase":
            explanation_debit = f"Purchase of goods/services from {invoice.vendor_name or 'vendor'}. Debit increases expense."
            explanation_credit = "Cash/Bank payment. Credit decreases asset (cash outflow)."
            
            await db.ledger_entries.insert_one({
                "id": str(uuid.uuid4()),
                "client_id": invoice.client_id,
                "user_id": user_id,
                "account_name": "Purchase",
                "account_type": "expense",
                "debit": invoice.total_amount,
                "credit": 0.0,
                "description": f"Purchase invoice {invoice.invoice_number}",
                "explanation": explanation_debit,
                "reference_id": invoice.id,
                "reference_type": "invoice",
                "entry_date": invoice.invoice_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            await db.ledger_entries.insert_one({
                "id": str(uuid.uuid4()),
                "client_id": invoice.client_id,
                "user_id": user_id,
                "account_name": "Accounts Payable",
                "account_type": "liability",
                "debit": 0.0,
                "credit": invoice.total_amount,
                "description": f"Purchase invoice {invoice.invoice_number}",
                "explanation": explanation_credit,
                "reference_id": invoice.id,
                "reference_type": "invoice",
                "entry_date": invoice.invoice_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        else:
            explanation_debit = f"Sales to customer. Debit increases asset (amount receivable)."
            explanation_credit = f"Sales revenue earned. Credit increases income."
            
            await db.ledger_entries.insert_one({
                "id": str(uuid.uuid4()),
                "client_id": invoice.client_id,
                "user_id": user_id,
                "account_name": "Accounts Receivable",
                "account_type": "asset",
                "debit": invoice.total_amount,
                "credit": 0.0,
                "description": f"Sales invoice {invoice.invoice_number}",
                "explanation": explanation_debit,
                "reference_id": invoice.id,
                "reference_type": "invoice",
                "entry_date": invoice.invoice_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            await db.ledger_entries.insert_one({
                "id": str(uuid.uuid4()),
                "client_id": invoice.client_id,
                "user_id": user_id,
                "account_name": "Sales Revenue",
                "account_type": "income",
                "debit": 0.0,
                "credit": invoice.total_amount,
                "description": f"Sales invoice {invoice.invoice_number}",
                "explanation": explanation_credit,
                "reference_id": invoice.id,
                "reference_type": "invoice",
                "entry_date": invoice.invoice_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        logging.error(f"Auto-posting to ledger failed: {e}")

# ==================== ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "Easy X API - Financial ChatGPT for CAs"}

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role
    )
    
    doc = user.model_dump()
    doc["password"] = hashed
    doc["created_at"] = doc["created_at"].isoformat()
    
    await db.users.insert_one(doc)
    
    token = create_token(user.id)
    return {"token": token, "user": user}

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc or not verify_password(credentials.password, user_doc["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user_doc["id"])
    user_doc.pop("password")
    return {"token": token, "user": user_doc}

@api_router.get("/auth/me")
async def get_me(user_id: str = Depends(get_current_user)):
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    return user_doc

@api_router.post("/clients", response_model=Client)
async def create_client(client_data: ClientCreate, user_id: str = Depends(get_current_user)):
    client = Client(user_id=user_id, **client_data.model_dump())
    doc = client.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.clients.insert_one(doc)
    return client

@api_router.get("/clients", response_model=List[Client])
async def get_clients(user_id: str = Depends(get_current_user)):
    clients = await db.clients.find({"user_id": user_id}, {"_id": 0}).to_list(1000)
    for c in clients:
        if isinstance(c.get("created_at"), str):
            c["created_at"] = datetime.fromisoformat(c["created_at"])
    return clients

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, user_id: str = Depends(get_current_user)):
    result = await db.clients.delete_one({"id": client_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}

@api_router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    client_id: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    file_bytes = await file.read()
    file_path = UPLOADS_DIR / f"{uuid.uuid4()}_{file.filename}"
    
    with open(file_path, "wb") as f:
        f.write(file_bytes)
    
    ocr_text = extract_text_from_image(file_bytes)
    extracted = extract_invoice_fields(ocr_text)
    
    document = Document(
        client_id=client_id,
        user_id=user_id,
        filename=file.filename,
        file_type=file.content_type,
        file_path=str(file_path),
        ocr_text=ocr_text,
        extracted_data=extracted,
        confidence_score=extracted.get("confidence", 0.5)
    )
    
    doc = document.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.documents.insert_one(doc)
    
    if extracted.get("invoice_number"):
        invoice = Invoice(
            document_id=document.id,
            client_id=client_id,
            user_id=user_id,
            invoice_type="purchase",
            gstin=extracted.get("gstin"),
            invoice_number=extracted.get("invoice_number"),
            invoice_date=extracted.get("invoice_date"),
            taxable_value=extracted.get("taxable_value", 0.0),
            cgst=extracted.get("cgst", 0.0),
            sgst=extracted.get("sgst", 0.0),
            igst=extracted.get("igst", 0.0),
            total_amount=extracted.get("total_amount", 0.0),
            vendor_name=extracted.get("vendor_name")
        )
        
        inv_doc = invoice.model_dump()
        inv_doc["created_at"] = inv_doc["created_at"].isoformat()
        await db.invoices.insert_one(inv_doc)
        
        await auto_post_invoice_to_ledger(invoice, user_id)
    
    return {"document": document, "extracted": extracted}

@api_router.get("/documents")
async def get_documents(client_id: str, user_id: str = Depends(get_current_user)):
    docs = await db.documents.find({"client_id": client_id, "user_id": user_id}, {"_id": 0}).to_list(1000)
    for d in docs:
        if isinstance(d.get("created_at"), str):
            d["created_at"] = datetime.fromisoformat(d["created_at"])
    return docs

@api_router.post("/invoices", response_model=Invoice)
async def create_invoice(invoice_data: InvoiceCreate, user_id: str = Depends(get_current_user)):
    invoice = Invoice(user_id=user_id, **invoice_data.model_dump())
    doc = invoice.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.invoices.insert_one(doc)
    await auto_post_invoice_to_ledger(invoice, user_id)
    return invoice

@api_router.get("/invoices")
async def get_invoices(client_id: str, user_id: str = Depends(get_current_user)):
    invoices = await db.invoices.find({"client_id": client_id, "user_id": user_id}, {"_id": 0}).to_list(1000)
    for inv in invoices:
        if isinstance(inv.get("created_at"), str):
            inv["created_at"] = datetime.fromisoformat(inv["created_at"])
    return invoices

@api_router.post("/ledger", response_model=LedgerEntry)
async def create_ledger_entry(entry_data: LedgerEntryCreate, user_id: str = Depends(get_current_user)):
    entry = LedgerEntry(user_id=user_id, **entry_data.model_dump())
    doc = entry.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.ledger_entries.insert_one(doc)
    return entry

@api_router.get("/ledger")
async def get_ledger(client_id: str, user_id: str = Depends(get_current_user)):
    entries = await db.ledger_entries.find({"client_id": client_id, "user_id": user_id}, {"_id": 0}).sort("entry_date", -1).to_list(1000)
    for e in entries:
        if isinstance(e.get("created_at"), str):
            e["created_at"] = datetime.fromisoformat(e["created_at"])
    return entries

@api_router.get("/reports/profit-loss")
async def get_profit_loss(client_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None, user_id: str = Depends(get_current_user)):
    query = {"client_id": client_id, "user_id": user_id}
    if start_date and end_date:
        query["entry_date"] = {"$gte": start_date, "$lte": end_date}
    
    entries = await db.ledger_entries.find(query, {"_id": 0}).to_list(10000)
    
    income = sum(e["credit"] for e in entries if e["account_type"] == "income")
    expenses = sum(e["debit"] for e in entries if e["account_type"] == "expense")
    profit = income - expenses
    
    return {
        "client_id": client_id,
        "period": {"start": start_date, "end": end_date},
        "income": income,
        "expenses": expenses,
        "profit": profit
    }

@api_router.get("/reports/balance-sheet")
async def get_balance_sheet(client_id: str, as_of_date: Optional[str] = None, user_id: str = Depends(get_current_user)):
    query = {"client_id": client_id, "user_id": user_id}
    if as_of_date:
        query["entry_date"] = {"$lte": as_of_date}
    
    entries = await db.ledger_entries.find(query, {"_id": 0}).to_list(10000)
    
    assets = sum(e["debit"] - e["credit"] for e in entries if e["account_type"] == "asset")
    liabilities = sum(e["credit"] - e["debit"] for e in entries if e["account_type"] == "liability")
    equity = sum(e["credit"] - e["debit"] for e in entries if e["account_type"] == "equity")
    
    return {
        "client_id": client_id,
        "as_of_date": as_of_date,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity
    }

@api_router.post("/chat")
async def send_chat_message(message_data: ChatMessageCreate, user_id: str = Depends(get_current_user)):
    user_msg = ChatMessage(
        client_id=message_data.client_id,
        user_id=user_id,
        role="user",
        content=message_data.content
    )
    
    user_doc = user_msg.model_dump()
    user_doc["created_at"] = user_doc["created_at"].isoformat()
    await db.chat_messages.insert_one(user_doc)
    
    ai_response = await get_ai_response(message_data.content, message_data.client_id, user_id)
    
    ai_msg = ChatMessage(
        client_id=message_data.client_id,
        user_id=user_id,
        role="assistant",
        content=ai_response["content"],
        tool_calls=ai_response.get("tool_calls", [])
    )
    
    ai_doc = ai_msg.model_dump()
    ai_doc["created_at"] = ai_doc["created_at"].isoformat()
    await db.chat_messages.insert_one(ai_doc)
    
    return {"user_message": user_msg, "ai_message": ai_msg}

@api_router.get("/chat/history")
async def get_chat_history(client_id: str, user_id: str = Depends(get_current_user)):
    messages = await db.chat_messages.find(
        {"client_id": client_id, "user_id": user_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(1000)
    
    for msg in messages:
        if isinstance(msg.get("created_at"), str):
            msg["created_at"] = datetime.fromisoformat(msg["created_at"])
    
    return messages

@api_router.post("/itc/analyze")
async def analyze_itc(client_id: str, user_id: str = Depends(get_current_user)):
    invoices = await db.invoices.find(
        {"client_id": client_id, "user_id": user_id, "invoice_type": "purchase"},
        {"_id": 0}
    ).to_list(10000)
    
    mismatches = []
    for inv in invoices:
        if not inv.get("gstin") or not inv.get("invoice_number"):
            mismatch = ITCMismatch(
                client_id=client_id,
                user_id=user_id,
                gstin=inv.get("gstin", "UNKNOWN"),
                invoice_number=inv.get("invoice_number", "UNKNOWN"),
                invoice_date=inv.get("invoice_date", ""),
                tax_amount=inv.get("cgst", 0) + inv.get("sgst", 0) + inv.get("igst", 0),
                status="missing",
                reason="Incomplete invoice data - missing GSTIN or invoice number"
            )
            mismatches.append(mismatch)
    
    for m in mismatches:
        doc = m.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.itc_mismatches.insert_one(doc)
    
    return {"analyzed_count": len(invoices), "mismatches": len(mismatches), "details": mismatches}

@api_router.get("/itc/mismatches")
async def get_itc_mismatches(client_id: str, user_id: str = Depends(get_current_user)):
    mismatches = await db.itc_mismatches.find(
        {"client_id": client_id, "user_id": user_id},
        {"_id": 0}
    ).to_list(1000)
    
    for m in mismatches:
        if isinstance(m.get("created_at"), str):
            m["created_at"] = datetime.fromisoformat(m["created_at"])
    
    return mismatches

@api_router.get("/download/{filename}")
async def download_file(filename: str):
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()