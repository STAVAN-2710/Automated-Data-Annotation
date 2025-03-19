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

def calculate_correction_impact(original_entities, corrected_entities):
    """Calculate the impact of corrections with improved entity modification detection."""
    # Track matched entities to avoid double-counting
    matched_orig = set()
    matched_corr = set()
    modified = 0
    
    # Step 1: Match by position first (exact same position)
    orig_by_pos = {(e.get("start", 0), e.get("end", 0)): i for i, e in enumerate(original_entities)}
    corr_by_pos = {(e.get("start", 0), e.get("end", 0)): i for i, e in enumerate(corrected_entities)}
    
    for pos, orig_idx in orig_by_pos.items():
        if pos in corr_by_pos:
            corr_idx = corr_by_pos[pos]
            # Check if content changed despite same position
            orig = original_entities[orig_idx]
            corr = corrected_entities[corr_idx]
            if (orig.get("type") != corr.get("type") or orig.get("text") != corr.get("text")):
                modified += 1
            
            # Mark as matched to avoid recounting
            matched_orig.add(orig_idx)
            matched_corr.add(corr_idx)
    
    # Step 2: Try to match by type and text
    for i, orig in enumerate(original_entities):
        if i in matched_orig:
            continue
            
        orig_type = orig.get("type", "")
        orig_text = orig.get("text", "")
        
        for j, corr in enumerate(corrected_entities):
            if j in matched_corr:
                continue
                
            corr_type = corr.get("type", "")
            corr_text = corr.get("text", "")
            
            # Check if same type with similar text
            if orig_type == corr_type:
                # Different comparison strategies based on entity type
                if orig_type in ["DOSAGE", "MED", "DATE"]:
                    # For dosage, medication, dates - check if one text contains the other
                    if (orig_text in corr_text or corr_text in orig_text or
                            similar_text(orig_text, corr_text)):
                        modified += 1
                        matched_orig.add(i)
                        matched_corr.add(j)
                        break
                else:
                    # For other types, look for position proximity
                    orig_start = orig.get("start", 0)
                    corr_start = corr.get("start", 0)
                    
                    # If positions are reasonably close (within 50 chars)
                    if abs(orig_start - corr_start) <= 50:
                        modified += 1
                        matched_orig.add(i)
                        matched_corr.add(j)
                        break
    
    # Step 3: Try to match by overlapping positions
    for i, orig in enumerate(original_entities):
        if i in matched_orig:
            continue
            
        orig_start = orig.get("start", 0)
        orig_end = orig.get("end", 0)
        
        for j, corr in enumerate(corrected_entities):
            if j in matched_corr:
                continue
                
            corr_start = corr.get("start", 0)
            corr_end = corr.get("end", 0)
            
            # Check for position overlap
            if (orig_start <= corr_end and corr_start <= orig_end):
                modified += 1
                matched_orig.add(i)
                matched_corr.add(j)
                break
    
    # Calculate remaining counts
    added = len(corrected_entities) - len(matched_corr)
    removed = len(original_entities) - len(matched_orig)
    
    return {
        "original_count": len(original_entities),
        "corrected_count": len(corrected_entities),
        "modified": modified,
        "added": added,
        "removed": removed
    }

def similar_text(text1, text2):
    """Helper function to check if texts are similar enough to be the same entity."""
    # Check for common words
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    common_words = words1.intersection(words2)
    
    # If they share at least half of their words, consider them similar
    return len(common_words) >= min(len(words1), len(words2)) / 2

# def calculate_correction_impact(original_entities: List[Dict], corrected_entities: List[Dict]) -> Dict[str, int]:
#     """
#     Calculate the impact of corrections on a set of entities.
    
#     Args:
#         original_entities: List of original entity dictionaries
#         corrected_entities: List of corrected entity dictionaries
        
#     Returns:
#         Dictionary with impact statistics
#     """
#     # Track by text+type pairs rather than position
#     orig_entities = {(e["type"], e["text"]): e for e in original_entities}
#     corr_entities = {(e["type"], e["text"]): e for e in corrected_entities}
    
#     # Calculate statistics
#     shared_keys = orig_entities.keys() & corr_entities.keys()
#     added = len(corr_entities) - len(shared_keys)
#     removed = len(orig_entities) - len(shared_keys)
#     modified = sum(1 for k in shared_keys if orig_entities[k] != corr_entities[k])
    
#     return {
#         "original_count": len(original_entities),
#         "corrected_count": len(corrected_entities),
#         "modified": modified,
#         "added": added,
#         "removed": removed
#     }
