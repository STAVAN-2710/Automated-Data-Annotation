import pymongo
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId

class AnnotationStore:
    """MongoDB storage for annotations with human review tracking"""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/", 
                 db_name: str = "annotation_db"):
        """Initialize connection to MongoDB"""
        self.client = pymongo.MongoClient(connection_string)
        self.db = self.client[db_name]
        self.annotations = self.db.annotations
        self.corrections = self.db.corrections
        
        # Create indexes for faster queries
        self.annotations.create_index("needs_human_review")
        self.corrections.create_index("document_id")
    
    def save_annotation(self, annotation: Dict[str, Any]) -> str:
        """Save an annotation to the database"""
        if "_id" not in annotation:
            result = self.annotations.insert_one(annotation)
            return str(result.inserted_id)
        else:
            self.annotations.replace_one({"_id": annotation["_id"]}, annotation)
            return str(annotation["_id"])
    
    def find_by_review_status(self, needs_review: bool = True, limit: int = 10) -> List[Dict]:
        """Find annotations by review status"""
        cursor = self.annotations.find({"needs_human_review": needs_review}).limit(limit)
        return list(cursor)
    
    def find_by_id(self, document_id: str) -> Optional[Dict]:
        """Find an annotation by ID"""
        return self.annotations.find_one({"_id": ObjectId(document_id)})
    
    def update_after_review(self, document_id: str, corrected_entities: List[Dict]) -> Dict:
        """Update annotation after human review"""
        # Find original annotation
        original = self.find_by_id(document_id)
        if not original:
            raise ValueError(f"Document with ID {document_id} not found")
        
        # Store correction record for active learning
        correction_record = {
            "document_id": ObjectId(document_id),
            "original_entities": original.get("entities", []),
            "corrected_entities": corrected_entities,
            "correction_timestamp": datetime.now(),
            "original_confidence": original.get("confidence_score", 0)
        }
        self.corrections.insert_one(correction_record)
        
        # Update the original annotation
        self.annotations.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {
                "entities": corrected_entities,
                "human_reviewed": True,
                "review_timestamp": datetime.now()
            }}
        )
        
        return {"status": "success", "document_id": document_id}
    
    def get_corrections(self, limit: int = 100) -> List[Dict]:
        """Retrieve correction records for active learning"""
        return list(self.corrections.find().limit(limit))
