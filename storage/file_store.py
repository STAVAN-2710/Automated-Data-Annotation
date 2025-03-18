# storage/file_store.py
import copy
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
import json
from datetime import datetime

class FileStore:
    """File-based storage for annotations with human review tracking"""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize file-based storage system"""
        self.data_dir = Path(data_dir)
        self.annotations_dir = self.data_dir / "annotations"
        self.corrections_dir = self.data_dir / "corrections"
        
        # Create directories if they don't exist
        self.annotations_dir.mkdir(parents=True, exist_ok=True)
        self.corrections_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory caches for faster access
        self._annotations_cache = {}
        self._corrections_cache = {}
        
        # Load existing data into cache
        self._load_cache()
    
    def _load_cache(self):
        """Load existing annotations and corrections into memory"""
        # Load annotations
        for file_path in self.annotations_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    annotation = json.load(f)
                    self._annotations_cache[file_path.stem] = annotation
            except Exception as e:
                print(f"Error loading annotation {file_path}: {e}")
        
        # Load corrections
        for file_path in self.corrections_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    correction = json.load(f)
                    self._corrections_cache[file_path.stem] = correction
            except Exception as e:
                print(f"Error loading correction {file_path}: {e}")
    
    def save_annotation(self, annotation: Dict[str, Any]) -> str:
        """Save an annotation to the file system"""
        # Generate ID if not provided
        if "_id" not in annotation:
            annotation["_id"] = str(uuid.uuid4())
        
        # Add timestamp if not present
        if "timestamp" not in annotation:
            annotation["timestamp"] = datetime.now().isoformat()
        
        # Save to file
        file_path = self.annotations_dir / f"{annotation['_id']}.json"
        with open(file_path, "w") as f:
            json.dump(annotation, f, indent=2)
        
        # Update cache
        self._annotations_cache[annotation["_id"]] = annotation
        self.last_processed_id = annotation["_id"]
        
        return annotation["_id"]
    
    def find_by_review_status(self, needs_review: bool = True, limit: int = 10) -> List[Dict]:
        """Find annotations by review status with prioritization for recent documents."""
        import copy
        
        matching_annotations = []
        
        # Step 1: Collect all annotations matching the review status
        for annotation_id, annotation in self._annotations_cache.items():
            if annotation.get("needs_human_review", False) == needs_review:
                # Create a deep copy to avoid modifying cache directly
                annotation_copy = copy.deepcopy(annotation)
                matching_annotations.append(annotation_copy)
        
        # Step 2: Sort annotations by timestamp (newest first)
        matching_annotations.sort(
            key=lambda x: x.get("timestamp", ""), 
            reverse=True  # Most recent first
        )
        
        # Step 3: Apply limit after sorting
        results = matching_annotations[:limit]
        
        # Step 4: Check for original states (before human correction)
        for annotation in results:
            document_id = annotation.get("_id")
            if document_id:
                original_corrections = self._get_original_annotation(document_id)
                if original_corrections:
                    # Use original entities for review
                    annotation["entities"] = original_corrections["original_entities"]
        
        return results


    def _get_original_annotation(self, document_id: str) -> Optional[Dict]:
        """Get the original document state before corrections."""
        for correction_id, correction in self._corrections_cache.items():
            if correction.get("document_id") == document_id:
                return correction
        return None
        
    def find_by_id(self, document_id: str) -> Optional[Dict]:
        """Find an annotation by ID"""
        return self._annotations_cache.get(document_id)
    
    def update_after_review(self, document_id: str, corrected_entities: List[Dict]) -> Dict:
        """Update annotation after human review"""
        # Find original annotation
        original = self.find_by_id(document_id)
        if not original:
            raise ValueError(f"Document with ID {document_id} not found")
        
        # Store correction record for active learning
        correction_id = str(uuid.uuid4())
        correction_record = {
            "_id": correction_id,
            "document_id": document_id,
            "original_entities": original.get("entities", []),
            "corrected_entities": corrected_entities,
            "correction_timestamp": datetime.now().isoformat(),
            "original_confidence": original.get("confidence_score", 0)
        }
        
        # Save correction to file
        correction_path = self.corrections_dir / f"{correction_id}.json"
        with open(correction_path, "w") as f:
            json.dump(correction_record, f, indent=2)
        
        # Update cache
        self._corrections_cache[correction_id] = correction_record
        
        # Update the original annotation
        original["entities"] = corrected_entities
        original["human_reviewed"] = True
        original["review_timestamp"] = datetime.now().isoformat()
        
        # Save updated annotation
        self.save_annotation(original)
        
        return {"status": "success", "document_id": document_id}
    
    def get_corrections(self, limit: int = 100) -> List[Dict]:
        """Retrieve correction records for active learning"""
        return list(self._corrections_cache.values())[:limit]
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the annotation storage"""
        total_annotations = len(self._annotations_cache)
        total_corrections = len(self._corrections_cache)
        
        needs_review = sum(1 for a in self._annotations_cache.values() 
                          if a.get("needs_human_review", False))
        auto_approved = total_annotations - needs_review
        
        return {
            "total_annotations": total_annotations,
            "total_corrections": total_corrections,
            "needs_review": needs_review,
            "auto_approved": auto_approved,
            "auto_approval_rate": auto_approved / total_annotations if total_annotations > 0 else 0
        }

    def clear_document_cache(self):
        """Clear any cached annotation data when processing a new document."""
        self._current_document_cache = None
        self._current_entities_cache = None