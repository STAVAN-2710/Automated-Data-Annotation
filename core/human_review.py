# core/human_review.py
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

class HumanReviewInterface:
    """Interface for retrieving and processing human reviews of annotations"""
    
    def __init__(self, annotation_store):
        """Initialize with an annotation store"""
        self.annotation_store = annotation_store
    
    def get_documents_for_review(self, limit: int = 10) -> List[Dict]:
        """Retrieve documents that need human review based on confidence scores"""
        return self.annotation_store.find_by_review_status(needs_review=True, limit=limit)
    
    def submit_correction(self, document_id: str, corrected_entities: List[Dict]) -> Dict:
        """Process human corrections and update annotation store"""
        # Update the annotation store with corrections
        result = self.annotation_store.update_after_review(document_id, corrected_entities)
        
        return result
    
    def get_review_statistics(self) -> Dict[str, Any]:
        """Get statistics on human reviews"""
        # Get all annotations
        needs_review = self.annotation_store.find_by_review_status(needs_review=True, limit=1000)
        reviewed = self.annotation_store.find_by_review_status(needs_review=False, limit=1000)
        
        return {
            "total_needing_review": len(needs_review),
            "total_reviewed": len(reviewed),
            "review_completion_rate": len(reviewed) / (len(needs_review) + len(reviewed)) if (len(needs_review) + len(reviewed)) > 0 else 0
        }

def _modify_entity_during_review(document_text, entity, new_text):
    """Update entity text and recalculate positions accurately."""
    # Store original values
    original_text = entity["text"]
    original_start = entity["start"]
    
    # Update the text
    entity["text"] = new_text
    
    # Recalculate positions based on new text length
    if original_text != new_text:
        # Find actual position in document
        new_start = document_text.find(new_text)
        if new_start >= 0:
            # Found exact text in document
            entity["start"] = new_start
            entity["end"] = new_start + len(new_text)
        else:
            # Text not found exactly - keep start but update end
            entity["end"] = original_start + len(new_text)
    
    # Reset validation status
    if "validation" in entity:
        entity["validation"] = {"valid": True, "issues": []}
    
    return entity

def _get_entity_context(document_text: str, entity: Dict[str, Any], context_size: int = 20) -> str:
    """Get surrounding context for an entity in the document."""
    start = max(0, entity.get("start", 0) - context_size)
    end = min(len(document_text), entity.get("end", 0) + context_size)
    
    context = document_text[start:end]
    
    # Highlight the entity within the context
    entity_start_in_context = entity.get("start", 0) - start
    entity_end_in_context = entity.get("end", 0) - start
    
    if 0 <= entity_start_in_context < entity_end_in_context <= len(context):
        highlighted = (
            context[:entity_start_in_context] + 
            "**" + context[entity_start_in_context:entity_end_in_context] + "**" + 
            context[entity_end_in_context:]
        )
        return highlighted
        
    return context

def calculate_correction_impact(original_entities: List[Dict], corrected_entities: List[Dict]) -> Dict[str, int]:
    """
    Calculate the impact of corrections on a set of entities.
    
    Args:
        original_entities: List of original entity dictionaries
        corrected_entities: List of corrected entity dictionaries
        
    Returns:
        Dictionary with impact statistics
    """
    # Track by text+type pairs rather than position
    orig_entities = {(e["type"], e["text"]): e for e in original_entities}
    corr_entities = {(e["type"], e["text"]): e for e in corrected_entities}
    
    # Calculate statistics
    shared_keys = orig_entities.keys() & corr_entities.keys()
    added = len(corr_entities) - len(shared_keys)
    removed = len(orig_entities) - len(shared_keys)
    modified = sum(1 for k in shared_keys if orig_entities[k] != corr_entities[k])
    
    return {
        "original_count": len(original_entities),
        "corrected_count": len(corrected_entities),
        "modified": modified,
        "added": added,
        "removed": removed
    }
