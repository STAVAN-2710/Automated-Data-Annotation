# core/rule_validator.py
import re
from typing import Dict, List, Any

class RuleValidator:
    """Rule-based validation of annotations with domain-specific constraints."""
    
    def __init__(self):
        self.validation_rules = {
            "PATIENT": self._validate_patient,
            "DATE": self._validate_date,
            "DOCTOR": self._validate_doctor,
            "MED": self._validate_medication,
            "DOSAGE": self._validate_dosage,
            "TEST": self._validate_test,
            "RESULT": self._validate_result
        }
    
    def validate_annotations(self, annotation: Dict, document: str) -> Dict:
        """Apply validation rules to annotations and enrich with validation metadata."""
        validated_entities = []
        validation_score = 1.0
        
        for entity in annotation.get("entities", []):
            validation_result = self._validate_entity(entity, document)
            entity["validation"] = validation_result
            validated_entities.append(entity)
            
            # Adjust overall validation score
            if not validation_result["valid"]:
                validation_score *= 0.8
        
        return {
            "document": annotation.get("document", ""),
            "entities": validated_entities,
            "confidence_score": annotation.get("confidence_score", 0),
            "validation_score": validation_score,
            "model_name": annotation.get("model_name", "")
        }
    
    def _validate_entity(self, entity: Dict, document: str) -> Dict:
        """Apply entity-specific validation rules."""
        entity_type = entity.get("type", "")
        validator = self.validation_rules.get(entity_type)
        
        if not validator:
            return {"valid": True, "issues": []}
        
        return validator(entity, document)
    
    def _validate_patient(self, entity: Dict, document: str) -> Dict:
        """Validate patient names."""
        text = entity.get("text", "")
        
        issues = []
        valid = True
        
        # Check for proper name format (First Last)
        if not re.match(r"^[A-Z][a-z]+(\s[A-Z][a-z]+)+$", text):
            issues.append("Patient name format is invalid")
            valid = False
            
        return {"valid": valid, "issues": issues}
    
    def _validate_doctor(self, entity: Dict, document: str) -> Dict:
        """Validate doctor names."""
        text = entity.get("text", "")
        
        issues = []
        valid = True
        
        # Check for doctor name format (Dr. First Last)
        if not re.match(r"^Dr\.\s[A-Z][a-z]+(\s[A-Z][a-z]+)+$", text) and not re.match(r"^[A-Z][a-z]+(\s[A-Z][a-z]+)+,\s[A-Z]{2,}$", text):
            issues.append("Doctor name format is unusual")
            valid = False
            
        return {"valid": valid, "issues": issues}
    
    def _validate_date(self, entity: Dict, document: str) -> Dict:
        """Validate date formats."""
        text = entity.get("text", "")
        
        issues = []
        valid = True
        
        # Check for common date formats
        date_patterns = [
            r"\d{1,2}/\d{1,2}/\d{4}",  # MM/DD/YYYY
            r"\d{1,2}-\d{1,2}-\d{4}",  # MM-DD-YYYY
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s\d{1,2},?\s\d{4}"  # Month DD, YYYY
        ]
        
        if not any(re.match(pattern, text) for pattern in date_patterns):
            issues.append("Date format is invalid")
            valid = False
            
        return {"valid": valid, "issues": issues}
    
    def _validate_medication(self, entity: Dict, document: str) -> Dict:
        """Validate medication names."""
        text = entity.get("text", "")
        
        issues = []
        valid = True
        
        # Basic medication name validation (capitalized, reasonable length)
        if not text[0].isupper() or len(text) < 3:
            issues.append("Medication name format is suspicious")
            valid = False
            
        return {"valid": valid, "issues": issues}
    
    def _validate_dosage(self, entity: Dict, document: str) -> Dict:
        """Validate medication dosage information."""
        text = entity.get("text", "")
        
        issues = []
        valid = True
        
        # Check for dosage pattern
        if not re.search(r"\d+\s*mg|\d+\s*mcg|\d+\s*ml", text, re.IGNORECASE):
            issues.append("Missing dosage amount")
            valid = False
            
        if not re.search(r"daily|twice|once|every", text, re.IGNORECASE):
            issues.append("Missing frequency information")
            valid = False
            
        return {"valid": valid, "issues": issues}
    
    def _validate_test(self, entity: Dict, document: str) -> Dict:
        """Validate medical test format."""
        text = entity.get("text", "")
        
        issues = []
        valid = True
        
        # Simple validation for test names
        if len(text) < 3:
            issues.append("Test name too short")
            valid = False
            
        return {"valid": valid, "issues": issues}
    
    def _validate_result(self, entity: Dict, document: str) -> Dict:
        """Validate test result format."""
        text = entity.get("text", "")
        
        issues = []
        valid = True
        
        # Check for value and unit pattern
        if not re.search(r"\d+\.?\d*\s*[a-zA-Z]+/[a-zA-Z]+|\d+\.?\d*\s*[a-zA-Z]+", text):
            issues.append("Test result missing value or unit")
            valid = False
            
        return {"valid": valid, "issues": issues}
