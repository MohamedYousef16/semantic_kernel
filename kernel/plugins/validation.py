import json
import re
from datetime import datetime
from semantic_kernel.functions import kernel_function
from config import VALIDATION_PATTERNS

class ValidationPlugin:
    def __init__(self):
        pass
    
    @kernel_function(
        description="Validate user input based on field type and patterns",
        name="validate_field"
    )
    def validate_field(self, field_name: str, value: str) -> str:
        """Validate input using existing validation patterns"""
        is_valid, error_message = self._validate_input(field_name, value)
        
        return json.dumps({
            "is_valid": is_valid,
            "error_message": error_message,
            "field_name": field_name,
            "value": value.strip() if value else ""
        })
    
    def _validate_input(self, field_name: str, value: str) -> tuple[bool, str]:
        """
        Validate user input based on field type
        Returns: (is_valid, error_message)
        """
        if not value or not value.strip():
            return False, f"{field_name} مطلوب"
        
        value = value.strip()
        
        # Check if field has validation pattern
        if field_name in VALIDATION_PATTERNS:
            pattern = VALIDATION_PATTERNS[field_name]["pattern"]
            message = VALIDATION_PATTERNS[field_name]["message"]
            
            if not re.match(pattern, value):
                return False, message
        
        # Additional custom validations
        if "تاريخ" in field_name:
            try:
                date_obj = datetime.strptime(value, "%Y-%m-%d")
                if date_obj > datetime.now():
                    return False, "التاريخ لا يمكن أن يكون في المستقبل"
            except ValueError:
                return False, "تاريخ غير صحيح، استخدم صيغة YYYY-MM-DD"
        
        return True, ""