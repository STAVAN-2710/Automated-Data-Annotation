# core/review_router.py
from typing import Dict, List
from config.settings import CONFIDENCE_THRESHOLD, VALIDATION_THRESHOLD

class ReviewRouter:
    """Routes annotations to human reviewers based on confidence thresholds."""
    
    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD, 
                validation_threshold: float = VALIDATION_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.validation_threshold = validation_threshold
    
    def route_annotation(self, validated_annotation: Dict) -> Dict:
        """Determine if annotation needs human review based on confidence and validation scores."""
        confidence_score = validated_annotation.get("confidence_score", 0)
        validation_score = validated_annotation.get("validation_score", 0)
        
        # Check for validation issues
        entities = validated_annotation.get("entities", [])
        invalid_entities = [e for e in entities if not e.get("validation", {}).get("valid", True)]
        
        needs_review = (confidence_score < self.confidence_threshold or 
                        validation_score < self.validation_threshold or
                        len(invalid_entities) > 0)
        
        # Enhance annotation with routing decision
        validated_annotation["needs_human_review"] = needs_review
        validated_annotation["review_reason"] = self._get_review_reason(
            confidence_score, validation_score, invalid_entities)
        
        return validated_annotation
    
    def _get_review_reason(self, confidence_score: float, validation_score: float, 
                          invalid_entities: List[Dict]) -> str:
        """Generate a reason for human review."""
        reasons = []
        
        if confidence_score < self.confidence_threshold:
            reasons.append(f"Low confidence score ({confidence_score:.2f})")
            
        if validation_score < self.validation_threshold:
            reasons.append(f"Low validation score ({validation_score:.2f})")
            
        if invalid_entities:
            entity_issues = []
            for entity in invalid_entities:
                issues = entity.get("validation", {}).get("issues", [])
                entity_issues.append(f"{entity.get('type')}: {', '.join(issues)}")
            
            reasons.append(f"Validation issues: {'; '.join(entity_issues)}")
            
        return " | ".join(reasons) if reasons else "No issues found"
