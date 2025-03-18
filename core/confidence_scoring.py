# core/confidence_scoring.py
from typing import List, Dict
from collections import Counter
import numpy as np

from config.settings import CONFIDENCE_WEIGHTS

def calculate_confidence_score(annotations: List[Dict], document: str) -> float:
    """
    Calculate confidence score based on multiple annotation runs.
    
    Args:
        annotations: List of annotation results from multiple runs
        document: Original document text
        
    Returns:
        Confidence score between 0 and 1
    """
    if not annotations:
        return 0.0
    
    # Format score - structure conformity
    format_score = sum(1.0 for ann in annotations if "entities" in ann) / len(annotations)
    
    # Position score - validate entity positions
    position_scores = []
    for annotation in annotations:
        entities = annotation.get("entities", [])
        if not entities:
            continue
            
        valid_positions = sum(1 for e in entities 
                            if 0 <= e.get("start", 0) < e.get("end", 0) <= len(document)
                            and document[e.get("start", 0):e.get("end", 0)] == e.get("text", ""))
        
        position_scores.append(valid_positions / len(entities) if entities else 0.0)
    
    position_score = sum(position_scores) / len(position_scores) if position_scores else 0.0
    
    # Consistency score - agreement between runs
    entity_keys = []
    for annotation in annotations:
        for entity in annotation.get("entities", []):
            entity_keys.append((entity["type"], entity["text"]))
    
    # Count occurrence of each entity
    entity_counts = Counter(entity_keys)
    
    # Calculate average consistency across entities
    max_count = len(annotations)
    consistency_scores = [count / max_count for count in entity_counts.values()]
    
    consistency_score = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.5
    
    # Final weighted score
    final_score = (
        CONFIDENCE_WEIGHTS["format"] * format_score +
        CONFIDENCE_WEIGHTS["position"] * position_score +
        CONFIDENCE_WEIGHTS["rules"] * consistency_score
    )
    
    return min(max(final_score, 0.0), 1.0)  # Clamp between 0 and 1


def calculate_entity_confidence(entity: Dict, document: str, domain_rules: Dict = None) -> float:
    """
    Calculate confidence score for a single entity based on domain rules.
    
    Args:
        entity: The entity to evaluate
        document: Original document text
        domain_rules: Optional domain-specific validation rules
        
    Returns:
        Entity-specific confidence score
    """
    confidence = 1.0
    
    # Basic position validation
    start, end = entity.get("start", 0), entity.get("end", 0)
    if not (0 <= start < end <= len(document)):
        return 0.2  # Severely penalize invalid positions
    
    # Text match validation
    text_at_position = document[start:end]
    if text_at_position != entity.get("text", ""):
        return 0.3  # Severely penalize text mismatch
    
    # Apply domain-specific rules if available
    if domain_rules and entity.get("type") in domain_rules:
        rule_func = domain_rules[entity.get("type")]
        rule_result = rule_func(entity.get("text", ""))
        if not rule_result:
            confidence *= 0.7  # Moderately penalize rule violations
    
    # Context analysis
    surrounding_context = document[max(0, start-50):min(len(document), end+50)]
    
    # Check if entity appears in typical context
    entity_type = entity.get("type", "")
    if entity_type == "DOSAGE" and "mg" not in entity.get("text", ""):
        confidence *= 0.8
    
    
    return confidence