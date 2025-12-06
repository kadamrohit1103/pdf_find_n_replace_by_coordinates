class ErrorCode:
    """Standardized error codes."""
    FILE_NOT_FOUND = "ERR_001"
    INVALID_JSON = "ERR_002"
    FONT_NOT_FOUND = "ERR_003"
    INVALID_COORDINATES = "ERR_004"
    PAGE_OUT_OF_RANGE = "ERR_005"
    TEXT_NOT_FOUND = "ERR_006"
    OVERLAPPING_TEXT_DETECTED = "ERR_007"
    PERMISSION_DENIED = "ERR_008"
    PDF_CORRUPTED = "ERR_009"
    REPLACEMENT_FAILED = "ERR_010"
    FONT_LOAD_FAILED = "ERR_011"

class UserFriendlyError(Exception):
    """Custom exception with error code, message, and resolution."""
    def __init__(self, error_code: str, user_message: str, 
                 technical_details: str, suggested_fix: str):
        self.error_code = error_code
        self.user_message = user_message
        self.technical_details = technical_details
        self.suggested_fix = suggested_fix
        super().__init__(self.user_message)
    
    def format_message(self) -> str:
        return f"""
ERROR [{self.error_code}]: {self.user_message}

TECHNICAL DETAILS:
{self.technical_details}

SUGGESTED FIX:
{self.suggested_fix}
"""
