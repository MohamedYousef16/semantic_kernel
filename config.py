import os
from enum import Enum

# Configuration
CHROMA_BASE_PATH = "chroma_data"
os.makedirs(CHROMA_BASE_PATH, exist_ok=True)
os.makedirs("temp", exist_ok=True)

# Database setup
DATABASE_URL = "mysql+pymysql://root:password@localhost:3306/service_requests_db"

class RequestStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

VALIDATION_PATTERNS = {
    "الاسم الكامل": {
        "pattern": r"^[\u0600-\u06FF\u0750-\u077F\s]{2,50}$",
        "message": "يجب أن يحتوي الاسم على حروف عربية فقط ويكون بين 2-50 حرف"
    },
    "رقم الهوية": {
        "pattern": r"^\d{10}$",
        "message": "رقم الهوية يجب أن يكون 10 أرقام"
    },
    "رقم الجوال": {
        "pattern": r"^(05|5)\d{8}$",
        "message": "رقم الجوال يجب أن يبدأ بـ 05 ويحتوي على 10 أرقام"
    },
    "البريد الإلكتروني": {
        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "message": "البريد الإلكتروني غير صحيح"
    },
    "تاريخ الميلاد": {
        "pattern": r"^\d{4}-\d{2}-\d{2}$",
        "message": "تاريخ الميلاد يجب أن يكون بصيغة YYYY-MM-DD"
    },
    "العنوان": {
        "pattern": r"^[\u0600-\u06FF\u0750-\u077F\s\d,.-]{5,100}$",
        "message": "العنوان يجب أن يكون بين 5-100 حرف"
    }
}