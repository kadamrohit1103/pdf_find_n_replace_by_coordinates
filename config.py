import json
from pathlib import Path
from typing import Dict, List, Any
from exceptions import ErrorCode, UserFriendlyError

class ConfigLoader:
    """Handles loading and validating the configuration JSON."""
    
    @staticmethod
    def load(json_file: str) -> Dict[str, Any]:
        """Loads configuration from a JSON file."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            raise UserFriendlyError(
                error_code=ErrorCode.FILE_NOT_FOUND,
                user_message=f"Configuration file '{json_file}' not found",
                technical_details=f"Path: {Path(json_file).absolute()}",
                suggested_fix="Verify the JSON file path is correct and file exists"
            )
        except json.JSONDecodeError as e:
            raise UserFriendlyError(
                error_code=ErrorCode.INVALID_JSON,
                user_message="Configuration JSON file has invalid format",
                technical_details=f"JSON parsing error at line {e.lineno}: {e.msg}",
                suggested_fix="Check JSON syntax: use online JSON validator or fix formatting"
            )

    @staticmethod
    def validate(config: Dict[str, Any]):
        """Validates the structure and required fields of the configuration."""
        required_fields = ["input_file", "output_file", "replacements"]
        missing = [f for f in required_fields if f not in config]
        
        if missing:
            raise UserFriendlyError(
                error_code=ErrorCode.INVALID_JSON,
                user_message="Configuration missing required fields",
                technical_details=f"Missing fields: {', '.join(missing)}",
                suggested_fix=f"Ensure JSON contains all required fields: {required_fields}"
            )
            
        # Basic validation for replacements list
        if not isinstance(config["replacements"], list):
             raise UserFriendlyError(
                error_code=ErrorCode.INVALID_JSON,
                user_message="'replacements' must be a list",
                technical_details=f"Got type: {type(config['replacements']).__name__}",
                suggested_fix="Format 'replacements' as an array: [...]"
            )
            
        for idx, rep in enumerate(config["replacements"]):
            req_rep_fields = ["pages", "find_text", "replace_text", "coordinates"]
            missing_rep = [f for f in req_rep_fields if f not in rep]
            if missing_rep:
                raise UserFriendlyError(
                    error_code=ErrorCode.INVALID_JSON,
                    user_message=f"Replacement entry #{idx+1} missing required fields",
                    technical_details=f"Missing: {', '.join(missing_rep)} in item {idx}",
                    suggested_fix=f"Add missing fields to replacement entry: {req_rep_fields}"
                )
            
            # Validate coordinates
            coords = rep["coordinates"]
            req_coords = ["x0", "y0", "x1", "y1"]
            
            if isinstance(coords, dict):
                if not all(k in coords for k in req_coords):
                     raise UserFriendlyError(
                        error_code=ErrorCode.INVALID_COORDINATES,
                        user_message=f"Replacement entry #{idx+1} has invalid coordinates",
                        technical_details=f"Missing coordinate keys. Required: {req_coords}",
                        suggested_fix="Ensure coordinates object has x0, y0, x1, y1"
                    )
            elif isinstance(coords, (list, tuple)):
                if len(coords) != 4:
                    raise UserFriendlyError(
                        error_code=ErrorCode.INVALID_COORDINATES,
                        user_message=f"Replacement entry #{idx+1} has invalid coordinates",
                        technical_details=f"Coordinate list must have 4 values. Got {len(coords)}.",
                        suggested_fix="Format: [x0, y0, x1, y1]"
                    )
            else:
                 raise UserFriendlyError(
                    error_code=ErrorCode.INVALID_COORDINATES,
                    user_message=f"Replacement entry #{idx+1} has invalid coordinates format",
                    technical_details=f"Got type: {type(coords)}",
                    suggested_fix="Use dictionary {x0, ...} or list [x0, y0, x1, y1]"
                )
