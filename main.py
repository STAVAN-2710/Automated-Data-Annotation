# main.py
import json
from typing import List, Dict
import re

from core.annotation_engine import TextAnnotator
from core.rule_validator import RuleValidator
from core.review_router import ReviewRouter
from storage.file_store import FileStore
from utils.helpers import format_entity_for_display, _get_entity_context
from core.human_review import (_modify_entity_during_review, _get_entity_context, 
                              calculate_correction_impact)

def process_document(document: str, entity_types: List[str]) -> Dict:
    """
    Process a document through the annotation pipeline
    
    Args:
        document: Text document to annotate
        entity_types: List of entity types to extract
        
    Returns:
        Processed annotation with validation and routing
    """
    # Initialize components
    annotator = TextAnnotator()
    validator = RuleValidator()
    router = ReviewRouter()
    store = FileStore()
    
    # Clear any cached document data
    store.clear_document_cache()
    # Clear any cached document data
    if hasattr(store, 'clear_document_cache'):
        store.clear_document_cache()
    
    # Step 1: Generate initial annotations
    print("Generating annotations...")
    annotation = annotator.annotate_document(document, entity_types)
    
    # Step 2: Apply validation rules
    print("Validating annotations...")
    validated_annotation = validator.validate_annotations(annotation, document)
    
    # Step 3: Determine routing (auto-approve or human review)
    print("Determining routing...")
    routed_annotation = router.route_annotation(validated_annotation)
    
    # Step 4: Store the annotation
    document_id = store.save_annotation(routed_annotation)
    routed_annotation["_id"] = document_id
    # Store the current document ID for targeted review
    store.last_processed_id = document_id
    
    return routed_annotation

def demonstrate_human_review(document_id=None):
    """
    Interactive human review interface that allows targeted correction of flagged entities
    while implementing Snorkel AI's programmatic validation principles.
    """
    # Initialize components
    store = FileStore()
    
    if document_id:
        # Target a specific document
        doc = store.find_by_id(document_id)
    elif hasattr(store, 'last_processed_id') and store.last_processed_id:
        # Use the most recently processed document
        doc = store.find_by_id(store.last_processed_id)
    else:
        # Fall back to the previous behavior
        docs_for_review = store.find_by_review_status(needs_review=True, limit=1)
        doc = docs_for_review[0] if docs_for_review else None
    
    if not doc:
        print("No documents requiring human review")
        return
    
    document_id = str(doc["_id"])
    document_text = doc.get("document", "")

    # VERIFICATION STEP: Check if document contains expected content
    print("\n===== VERIFYING DOCUMENT CONTENT =====")
    first_50_chars = document_text[:50].strip() if document_text else ""
    print(f"Document begins with: '{first_50_chars}...'")
    
    if input("Is this the correct document? (y/n): ").lower() != 'y':
        print("Document verification failed - aborting review")
        return
    
    print("\n===== DOCUMENT REQUIRING REVIEW =====")
    print(f"Document ID: {document_id}")
    print(f"Document text:\n{document_text}")
    print(f"Confidence score: {doc.get('confidence_score', 0):.2f}")
    print(f"Review reason: {doc.get('review_reason', 'Unknown')}")
    
    # Identify problematic entities that need specific review
    entities = doc.get("entities", [])
    problematic_entities = []
    
    # Parse review reason to identify specific issues
    review_reason = doc.get("review_reason", "")
    issue_types = []
    
    if "validation issues" in review_reason.lower():
        # Extract specific entity types with issues
        issue_matches = re.findall(r"([A-Z]+): ([^;]+)", review_reason)
        issue_types = [entity_type for entity_type, _ in issue_matches]
    
    # Flag entities that need review based on validation issues
    for i, entity in enumerate(entities):
        needs_review = False
        validation = entity.get("validation", {})
        entity_type = entity.get("type", "")
        
        # Flag entity if it has validation issues or its type is mentioned in review reason
        if not validation.get("valid", True) or entity_type in issue_types:
            needs_review = True
            
        problematic_entities.append({
            "index": i,
            "entity": entity,
            "needs_review": needs_review
        })
    
    # Display original entities with flags for those needing review
    print("\nCurrent Entities:")
    for i, item in enumerate(problematic_entities):
        entity = item["entity"]
        flag = "[NEEDS REVIEW]" if item["needs_review"] else ""
        print(f"{i+1}. {format_entity_for_display(entity)} {flag}")
    
    # Create working copy of entities for modifications
    corrected_entities = entities.copy()
    
    # Interactive review options
    print("\n===== HUMAN REVIEW OPTIONS =====")
    print("1. Review and correct flagged entities")
    print("2. Add missing entities")
    print("3. Accept all entities as-is")
    print("4. Cancel review")
    
    while True:
        choice = input("\nSelect an option (1-4): ")
        
        if choice == "1":
            # Review flagged entities
            for item in problematic_entities:
                if item["needs_review"]:
                    entity = item["entity"]
                    entity_idx = item["index"]
                    
                    print(f"\nReviewing: {format_entity_for_display(entity)}")
                    print(f"Text context: \"{_get_entity_context(document_text, entity)}\"")
                    
                    action = input("Actions: (a)ccept, (m)odify, (d)elete, or (s)kip: ").lower()
                    
                    if action == 'm':
                        # Modify entity
                        print("Current values:")
                        print(f"- Type: {entity['type']}")
                        print(f"- Text: {entity['text']}")
                        print(f"- Start: {entity['start']}")
                        print(f"- End: {entity['end']}")
                        
                        # Only allow changing valid fields
                        new_type = input(f"New type (or press Enter to keep '{entity['type']}'): ")
                        if new_type:
                            corrected_entities[entity_idx]["type"] = new_type
                            
                        new_text = input(f"New text (or press Enter to keep '{entity['text']}'): ")
                        if new_text:
                            # Use the position recalculation function to update positions
                            corrected_entities[entity_idx] = _modify_entity_during_review(
                                document_text, 
                                corrected_entities[entity_idx], 
                                new_text
                            )
                    
                    elif action == 'd':
                        # Delete entity
                        corrected_entities.pop(entity_idx)
                        # Adjust indices for remaining entities
                        for item in problematic_entities:
                            if item["index"] > entity_idx:
                                item["index"] -= 1
                    
                    elif action == 's':
                        # Skip to next entity
                        continue
            
        elif choice == "2":
            # Add missing entities
            print("\nAdd missing entity:")
            valid_types = ["PATIENT", "DATE", "DOCTOR", "MED", "DOSAGE", "TEST", "RESULT", "FACILITY"]
            
            print("Valid entity types:", ", ".join(valid_types))
            entity_type = input("Entity type: ").upper()
            
            if entity_type not in valid_types:
                print(f"Invalid entity type. Must be one of: {', '.join(valid_types)}")
                continue
                
            entity_text = input("Entity text: ")
            
            # Find position in document
            start_pos = document_text.find(entity_text)
            if start_pos >= 0:
                end_pos = start_pos + len(entity_text)
                
                # Create new entity
                new_entity = {
                    "type": entity_type,
                    "text": entity_text,
                    "start": start_pos,
                    "end": end_pos,
                    "validation": {"valid": True, "issues": []}
                }
                
                corrected_entities.append(new_entity)
                print(f"Added: {format_entity_for_display(new_entity)}")
            else:
                print(f"Error: Could not find '{entity_text}' in document")
                continue
                
            add_another = input("Add another entity? (y/n): ").lower()
            if add_another != 'y':
                break
                
        elif choice == "3":
            # Accept all as-is
            print("Accepting all entities as currently shown")
            # Mark all entities as valid
            for entity in corrected_entities:
                if "validation" in entity:
                    entity["validation"]["valid"] = True
                    entity["validation"]["issues"] = []
            break
            
        elif choice == "4":
            # Cancel
            print("Review cancelled, no changes made")
            return
            
        else:
            print("Invalid option, please select 1-4")
            continue
            
        # Show option to continue or finish review
        print("\nCurrent corrected entities:")
        for i, entity in enumerate(corrected_entities):
            print(f"{i+1}. {format_entity_for_display(entity)}")
            
        if input("\nFinish review? (y/n): ").lower() == 'y':
            break
    
    # Submit corrections
    result = store.update_after_review(document_id, corrected_entities)
    
    print("\n===== CORRECTION SUBMITTED =====")
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Document ID: {result.get('document_id', 'unknown')}")
    
    # Show impact of corrections (useful for Snorkel AI's active learning approach)
    impact = calculate_correction_impact(entities, corrected_entities)
    print("\n===== CORRECTION IMPACT =====")
    print(f"Original entity count: {impact['original_count']}")
    print(f"Corrected entity count: {impact['corrected_count']}")
    print(f"Modified entities: {impact['modified']}")
    print(f"Added entities: {impact['added']}")
    print(f"Removed entities: {impact['removed']}")


# def demonstrate_human_review():
#     """Demonstrate the human review process"""
#     # Initialize components
#     store = FileStore()
    
#     # Get documents needing review
#     docs_for_review = store.find_by_review_status(needs_review=True, limit=1)
    
#     if not docs_for_review:
#         print("No documents requiring human review")
#         return
    
#     print("\n===== DOCUMENT REQUIRING REVIEW =====")
#     doc = docs_for_review[0]
#     document_id = str(doc["_id"])
#     print(f"Document ID: {document_id}")
#     print(f"Document: {doc.get('document', '')[:100]}...")
#     print(f"Confidence score: {doc.get('confidence_score', 0):.2f}")
#     print(f"Reason for review: {doc.get('review_reason', 'Unknown')}")
    
#     print("\nCurrent Entities:")
#     for entity in doc.get("entities", []):
#         print(f"- {format_entity_for_display(entity)}")
    
#     # Simulate a human correction (e.g., adding a missing entity)
#     corrected_entities = doc.get("entities", [])[:]  # Copy the list
    
#     # Example: Add a missing entity
#     new_entity = {
#         "type": "FACILITY", 
#         "text": "Boston Medical Center", 
#         "start": 250, 
#         "end": 271,
#         "validation": {"valid": True, "issues": []}
#     }
#     corrected_entities.append(new_entity)
    
#     # Submit the correction
#     store.update_after_review(document_id, corrected_entities)
    
#     print("\n===== CORRECTION SUBMITTED =====")
#     print(f"Status: success")
#     print(f"Document ID: {document_id}")

# def demonstrate_active_learning():
#     """Demonstrate the active learning component"""
#     # Initialize components
#     store = MemoryStore()
#     validator = RuleValidator()
#     active_learning = ActiveLearningController(store, validator)
    
#     # Analyze corrections (this would normally require several corrections in the DB)
#     analysis = active_learning.analyze_corrections(min_samples=1)  # Use 1 for demo purposes
    
#     print("\n===== ACTIVE LEARNING ANALYSIS =====")
#     if analysis.get("status") == "insufficient_data":
#         print(f"Insufficient data: {analysis.get('message', '')}")
#         return
    
#     print(f"Total corrections analyzed: {analysis.get('total_corrections_analyzed', 0)}")
    
#     # Print rule suggestions
#     print("\nRule Suggestions:")
#     for suggestion in analysis.get("rule_suggestions", []):
#         print(f"- Entity: {suggestion['entity_type']}, Issue: {suggestion['issue']}")
#         print(f"  Suggestion: {suggestion['suggestion']}")
    
#     # Print confidence calibration
#     print("\nConfidence Calibration:")
#     for bin_range, calibration in analysis.get("confidence_calibration", {}).items():
#         print(f"- Confidence range {bin_range}:")
#         print(f"  Samples: {calibration['samples']}, Error rate: {calibration['error_rate']:.2f}")
#         print(f"  Suggested calibration: {calibration['suggested_calibration']:.2f}")


def display_annotation_results(result: Dict) -> None:
    """Display annotation results in a readable format"""
    print("\n===== ANNOTATION RESULTS =====")
    print(f"Document: {result.get('document', '')[:100]}...")
    print(f"Model used: {result.get('model_name', 'unknown')}")
    print(f"Confidence score: {result.get('confidence_score', 0):.2f}")
    print(f"Validation score: {result.get('validation_score', 0):.2f}")
    print(f"Needs human review: {result.get('needs_human_review', True)}")
    
    if result.get("needs_human_review", True):
        print(f"Review reason: {result.get('review_reason', 'Unknown')}")
    
    print("\nEntities:")
    for entity in result.get("entities", []):
        print(f"- {format_entity_for_display(entity)}")

if __name__ == "__main__":
    # Example document to annotate
    example_document = """
    Patient Harsh Vardhan (DOB: 04/15/1975) was admitted on March 3, 2024, with
    complaints of knee pain. Dr. Elizabeth Chen ordered a CBC panel and troponin
    test. Results showed troponin levels of 0.08 ng/mL. Patient was prescribed
    Metoprolol 25mg twice daily.
    """
    
    # Entity types to extract
    entity_types = ["PATIENT", "DATE", "DOCTOR", "MED", "DOSAGE", "TEST", "RESULT", "FACILITY"]
    
    # Process the document
    result = process_document(example_document, entity_types)
    
    # Display results
    display_annotation_results(result)
    
    # Save to file (optional)
    with open("annotation_result.json", "w") as f:
        json.dump(result, f, indent=2)

    demonstrate_human_review(result.get("_id"))

    # Display storage statistics
    store = FileStore()
    stats = store.get_statistics()
    print("\n===== STORAGE STATISTICS =====")
    print(f"Total annotations: {stats['total_annotations']}")
    print(f"Auto-approved: {stats['auto_approved']} ({stats['auto_approval_rate']*100:.1f}%)")
    print(f"Needs review: {stats['needs_review']}")
    print(f"Total corrections: {stats['total_corrections']}")


# Patient Maria Garcia (DOB: 11/23/1982) was admitted on February 15, 2024, with 
# complaints of severe headache. Dr. James Wilson ordered a CT scan and blood panel. 
# Results showed normal CT findings and elevated WBC count of 11.2 K/μL. Patient was prescribed 
# Sumatriptan 50mg as needed and Ibuprofen 800mg three times daily.


# Patient Robert Johnson (DOB: 06/30/1968) was admitted on March 8, 2024, with 
# complaints of lower back pain. Dr. Sarah Ahmed ordered an MRI and urine analysis. 
# Results showed mild disc bulging at L4-L5 and normal urinalysis. Patient was prescribed 
# Cyclobenzaprine 10mg at bedtime and Naproxen 500mg twice daily.


# Patient Jennifer Wong (DOB: 09/12/1991) was admitted on February 27, 2024, with 
# complaints of persistent cough. Dr. Michael Rivera ordered a chest X-ray and sputum culture. 
# Results showed mild bronchial inflammation and negative bacterial growth. Patient was prescribed 
# Azithromycin 500mg once daily for 3 days and Benzonatate 200mg three times daily.
