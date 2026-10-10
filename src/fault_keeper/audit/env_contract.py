"""AEC-VS: Environment Contract Synthesizer & Validator."""

from __future__ import annotations
import os
import re
from typing import Dict, List, Any, Optional


class EnvContract:
    """Environment variable contract definition."""
    
    def __init__(self, name: str, required: bool = True, pattern: str = None):
        """Initialize contract.
        
        Args:
            name: Environment variable name (e.g., "DATABASE_URL")
            required: Whether variable must be set
            pattern: Regex pattern for validation
        """
        self.name = name
        self.required = required
        self.pattern = re.compile(pattern) if pattern else None

    def validate(self, value: Optional[str]) -> tuple[bool, List[str]]:
        """Validate environment variable value.
        
        Args:
            value: Variable value to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if value is None:
            if self.required:
                errors.append(f"Required env var {self.name} is not set")
            return False, errors
        
        if self.pattern and not self.pattern.match(value):
            errors.append(
                f"{self.name} value '{value}' doesn't match pattern '{self.pattern.pattern}'"
            )
            return False, errors
        
        return True, errors


def parse_env_contract(env_content: str) -> Dict[str, EnvContract]:
    """Parse environment contract from string.
    
    Expected format (YAML-like):
        DATABASE_URL:
          required: true
          pattern: "^postgres://.*$"
        
        API_KEY:
          required: true
          pattern: "^[A-Za-z0-9]{32}$"
        
        LOG_LEVEL:
          required: false
          pattern: "(DEBUG|INFO|WARNING|ERROR)"
    
    Args:
        env_content: Contract definition string
        
    Returns:
        Dictionary mapping variable names to EnvContract instances
    """
    contracts = {}
    
    # Simple parser for YAML-like format
    lines = env_content.strip().split('\n')
    current_var = None
    
    for line in lines:
        line = line.strip()
        
        if not line or line.startswith('#'):
            continue
        
        # Variable definition
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*$', line)
        if match:
            current_var = match.group(1)
            contracts[current_var] = EnvContract(current_var)
            continue
        
        # Property definition
        if current_var and ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"\'')
            
            if key == 'required':
                contracts[current_var].required = value.lower() == 'true'
            elif key == 'pattern':
                contracts[current_var].pattern = re.compile(value)
    
    return contracts


def validate_env_contract(
    env_content: str,
    env_vars: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Validate environment variables against contract.
    
    Args:
        env_content: Contract definition string
        env_vars: Dictionary of environment variables {name: value}
                   If None, uses os.environ
        
    Returns:
        Dictionary with validation results:
            - valid: bool
            - missing_keys: list[str]
            - invalid_values: list[dict]
            - warnings: list[str]
    """
    contracts = parse_env_contract(env_content)
    
    result = {
        "valid": True,
        "missing_keys": [],
        "invalid_values": [],
        "warnings": []
    }
    
    # Get environment variables
    if env_vars is None:
        env_vars = dict(os.environ)
    
    # Check each contract
    for name, contract in contracts.items():
        value = env_vars.get(name)
        
        is_valid, errors = contract.validate(value)
        
        if not is_valid:
            result["valid"] = False
            result["missing_keys"].append(name) if contract.required else None
            result["invalid_values"].append({
                "name": name,
                "errors": errors
            })
    
    return result


def validate_env_file(env_path: str) -> Dict[str, Any]:
    """Validate .env file against its contract.
    
    Args:
        env_path: Path to .env file
        
    Returns:
        Validation result dictionary
    """
    try:
        with open(env_path, 'r') as f:
            env_content = f.read()
            
        # Parse contract from same file (simplified)
        contracts = parse_env_contract(env_content)
        
        env_vars = dict(os.environ)
        result = validate_env_contract(env_content, env_vars)
        
        return result
        
    except FileNotFoundError:
        return {
            "valid": False,
            "missing_keys": ["FILE_NOT_FOUND"],
            "invalid_values": [],
            "warnings": [f"File not found: {env_path}"]
        }


if __name__ == "__main__":
    # Test contract validation
    contract = """
DATABASE_URL:
  required: true
  pattern: "^postgres://.*$"
  
API_KEY:
  required: true
  pattern: "^[A-Za-z0-9]{32}$"
  
LOG_LEVEL:
  required: false
  pattern: "(DEBUG|INFO|WARNING|ERROR)"
"""
    
    env_vars = {
        "DATABASE_URL": "postgres://localhost:5432/mydb",
        "API_KEY": "abc123def456ghi789jkl012mno345pq",
        "LOG_LEVEL": "INFO"
    }
    
    result = validate_env_contract(contract, env_vars)
    print(f"Valid: {result['valid']}")
    print(f"Missing keys: {result['missing_keys']}")
    print(f"Invalid values: {result['invalid_values']}")