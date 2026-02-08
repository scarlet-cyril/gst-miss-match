from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

# ==================== MODELS ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    role: Literal["ca", "gst_practitioner", "firm"] = "ca"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Literal["ca", "gst_practitioner", "firm"] = "ca"

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
    role: Literal["user", "assistant"] = "user"
    content: str
    metadata: Optional[Dict[str, Any]] = None
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

# ==================== AI CHAT SERVICE ====================

async def get_ai_response(user_message: str, client_id: str, user_id: str) -> str:
    try:
        api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not api_key:
            return "AI service is not configured. Please contact administrator."
        
        recent_messages = await db.chat_messages.find(
            {"client_id": client_id, "user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(10).to_list(10)
        
        context = f"You are Easy X, an AI financial assistant for Chartered Accountants. Current client: {client_id}.\n"
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
        
        return response
    except Exception as e:
        logging.error(f"AI chat failed: {e}")
        return f"I'm having trouble processing your request. Error: {str(e)}"

# ==================== ACCOUNTING LOGIC ====================

async def auto_post_invoice_to_ledger(invoice: Invoice, user_id: str):
    try:
        if invoice.invoice_type == "purchase":
            await db.ledger_entries.insert_one({
                "id": str(uuid.uuid4()),
                "client_id": invoice.client_id,
                "user_id": user_id,
                "account_name": "Purchase",
                "account_type": "expense",
                "debit": invoice.total_amount,
                "credit": 0.0,
                "description": f"Purchase invoice {invoice.invoice_number}",
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
                "reference_id": invoice.id,
                "reference_type": "invoice",
                "entry_date": invoice.invoice_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        else:
            await db.ledger_entries.insert_one({
                "id": str(uuid.uuid4()),
                "client_id": invoice.client_id,
                "user_id": user_id,
                "account_name": "Accounts Receivable",
                "account_type": "asset",
                "debit": invoice.total_amount,
                "credit": 0.0,
                "description": f"Sales invoice {invoice.invoice_number}",
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

@api_router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    client_id: str = Form(...),
    user_id: str = Depends(get_current_user)
):
    file_bytes = await file.read()
    
    ocr_text = extract_text_from_image(file_bytes)
    extracted = extract_invoice_fields(ocr_text)
    
    document = Document(
        client_id=client_id,
        user_id=user_id,
        filename=file.filename,
        file_type=file.content_type,
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
        content=ai_response
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