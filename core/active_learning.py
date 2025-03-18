# core/active_learning.py
from typing import List, Dict, Any
from collections import defaultdict

class ActiveLearningController:
    """Controller for analyzing human corrections and improving the system"""
    
    def __init__(self, annotation_store, rule_validator):
        """Initialize with storage and validator components"""
        self.annotation_store = annotation_store
        self.rule_validator = rule_validator
    
    def analyze_corrections(self, min_samples: int = 10) -> Dict[str, Any]:
        """Analyze patterns in human corrections to improve system"""
        corrections = self.annotation_store.get_corrections(limit=100)
        
        if len(corrections) < min_samples:
            return {"status": "insufficient_data", "message": f"Need at least {min_samples} corrections"}
            
        # Identify entity types with high correction rates
        entity_corrections = self._aggregate_entity_corrections(corrections)
        
        # Generate rule improvement suggestions
        rule_suggestions = self._generate_rule_suggestions(entity_corrections)
        
        # Calculate confidence calibration factors
        confidence_calibration = self._calculate_confidence_calibration(corrections)
        
        return {
            "entity_correction_rates": entity_corrections,
            "rule_suggestions": rule_suggestions,
            "confidence_calibration": confidence_calibration,
            "total_corrections_analyzed": len(corrections)
        }
    
    def _aggregate_entity_corrections(self, corrections: List[Dict]) -> Dict[str, Dict]:
        """Aggregate statistics on entity corrections by type"""
        entity_stats = defaultdict(lambda: {"total": 0, "added": 0, "removed": 0, "modified": 0})
        
        for correction in corrections:
            original_entities = {(e["type"], e["text"]): e for e in correction.get("original_entities", [])}
            corrected_entities = {(e["type"], e["text"]): e for e in correction.get("corrected_entities", [])}
            
            # Find entities that were added, removed, or modified
            for key in set(original_entities.keys()) | set(corrected_entities.keys()):
                entity_type = key[0]
                
                entity_stats[entity_type]["total"] += 1
                
                if key in corrected_entities and key not in original_entities:
                    entity_stats[entity_type]["added"] += 1
                elif key in original_entities and key not in corrected_entities:
                    entity_stats[entity_type]["removed"] += 1
                elif key in original_entities and key in corrected_entities:
                    # Check if positions were modified
                    orig = original_entities[key]
                    corr = corrected_entities[key]
                    if orig["start"] != corr["start"] or orig["end"] != corr["end"]:
                        entity_stats[entity_type]["modified"] += 1
        
        # Calculate correction rates
        for entity_type, stats in entity_stats.items():
            if stats["total"] > 0:
                stats["correction_rate"] = (stats["added"] + stats["removed"] + stats["modified"]) / stats["total"]
                
        return dict(entity_stats)
    
    def _generate_rule_suggestions(self, entity_stats: Dict[str, Dict]) -> List[Dict]:
        """Generate suggestions for rule improvements based on correction patterns"""
        suggestions = []
        
        for entity_type, stats in entity_stats.items():
            if stats.get("correction_rate", 0) > 0.3:  # High correction rate
                if stats.get("added", 0) > stats.get("removed", 0):
                    suggestions.append({
                        "entity_type": entity_type,
                        "issue": "under_identification",
                        "suggestion": f"Consider relaxing validation rules for {entity_type}"
                    })
                elif stats.get("removed", 0) > stats.get("added", 0):
                    suggestions.append({
                        "entity_type": entity_type,
                        "issue": "over_identification",
                        "suggestion": f"Consider stricter validation rules for {entity_type}"
                    })
                if stats.get("modified", 0) > 0:
                    suggestions.append({
                        "entity_type": entity_type,
                        "issue": "boundary_detection",
                        "suggestion": f"Improve span detection for {entity_type}"
                    })
        
        return suggestions
    
    def _calculate_confidence_calibration(self, corrections: List[Dict]) -> Dict[str, Dict]:
        """Calculate calibration factors for confidence scores based on corrections"""
        confidence_bins = [0.0, 0.7, 0.8, 0.9, 0.95, 1.0]
        calibration = {}
        
        for i in range(len(confidence_bins) - 1):
            bin_start = confidence_bins[i]
            bin_end = confidence_bins[i+1]
            bin_key = f"{bin_start:.2f}-{bin_end:.2f}"
            
            bin_corrections = [c for c in corrections 
                              if bin_start <= c.get("original_confidence", 0) < bin_end]
            
            if bin_corrections:
                # Calculate error rate for this confidence bin
                error_counts = 0
                for correction in bin_corrections:
                    orig_ents = correction.get("original_entities", [])
                    corr_ents = correction.get("corrected_entities", [])
                    if orig_ents != corr_ents:
                        error_counts += 1
                
                error_rate = error_counts / len(bin_corrections)
                calibration[bin_key] = {
                    "samples": len(bin_corrections),
                    "error_rate": error_rate,
                    "suggested_calibration": 1.0 - error_rate
                }
        
        return calibration
