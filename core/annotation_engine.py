# core/annotation_engine.py
import json
from typing import Dict, List, Any, Optional
import time
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from config.settings import ANNOTATION_RUNS, ENTITY_DESCRIPTIONS
from models.model_provider import ModelProvider
from utils.helpers import extract_json_from_text
import logging

logging.basicConfig(level=logging.INFO)

class TextAnnotator:
    """
    LangChain-powered annotation engine with consistency scoring
    """
    
    def __init__(self):
        self.model_provider = ModelProvider()
        self.output_parser = StrOutputParser()
    
    def annotate_document(self, document: str, entity_types: List[str]) -> Dict:
        """
        Annotate a document with entity annotations using LangChain.
        
        Args:
            document: Text document to annotate
            entity_types: List of entity types to extract
            
        Returns:
            Dictionary containing annotations with confidence scores
        """
        # Select model based on document complexity
        model = self.model_provider.select_model_for_document(document)
        
        # Generate prompt
        system_message, human_message = self._create_annotation_prompt(document, entity_types)
        
        # Run multiple annotation passes for consistency scoring
        annotations = []
        
        for _ in range(ANNOTATION_RUNS):
            try:
                # Use LangChain's messaging format instead of direct API call
                messages = [system_message, human_message]
                response = model.invoke(messages)
                
                # Extract content from LangChain response
                response_text = self.output_parser.invoke(response)

                # Parse and validate the response
                parsed_result = self._parse_annotation_response(response_text, document)
                # logging.info(f"Raw GPT Response:\n{parsed_result}")

                if parsed_result:
                    annotations.append(parsed_result)
            except Exception as e:
                print(f"Error in annotation run: {e}")
        
        # Calculate consensus annotations
        final_annotations = self._calculate_consensus_annotations(annotations)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(annotations, document)
        
        return {
            "document": document,
            "entities": final_annotations,
            "confidence_score": confidence_score,
            "model_name": model.model_name,
            "timestamp": time.time()
        }
    
    def _create_annotation_prompt(self, document: str, entity_types: List[str]):
        """
        Create LangChain message objects for annotation prompt.
        
        Returns:
            Tuple of (SystemMessage, HumanMessage)
        """
        # Format entity types with descriptions
        entity_list = "\n".join([f"- {etype}: {ENTITY_DESCRIPTIONS.get(etype, 'No description')}" 
                            for etype in entity_types])
        
        # Create example annotation
        example_doc = "Patient John Smith (DOB: 04/15/1975) visited Dr. Maria Rodriguez on January 15, 2024."
        example_entities = [
            {"type": "PATIENT", "text": "John Smith", "start": 8, "end": 18},
            {"type": "DATE", "text": "04/15/1975", "start": 25, "end": 35},
            {"type": "DOCTOR", "text": "Dr. Maria Rodriguez", "start": 44, "end": 63},
            {"type": "DATE", "text": "January 15, 2024", "start": 67, "end": 84}
        ]
        
        # Pre-format the example JSON to avoid f-string issues
        example_json = json.dumps({"entities": example_entities}, indent=2)
        
        # System message for context
        system_content = '''You are an expert text annotator that extracts entities from medical documents with high precision.
        You are an expert annotator. Please identify and label the following entities in this medical document:
        - PATIENT: Patient name
        - DATE: Any dates mentioned
        - DOCTOR: Healthcare provider name
        - MED: Medication name
        - DOSAGE: Medication dosage information
        - TEST: Medical tests ordered
        - RESULT: Test results'''
        
        # Human message with the task details
        human_content = f"""
        Extract and annotate the following entity types from the provided document:
        
        {entity_list}

        You are an expert medical annotator trained to identify entities in medical records. Your task is to extract and label the following entities:
        - PATIENT: Full name of the patient.
        - DATE: Any dates mentioned in MM/DD/YYYY or Month DD, YYYY format.
        - DOCTOR: Name of healthcare providers with titles like Dr.
        - MED: Medication names (e.g., Metoprolol).
        - DOSAGE: Dosage information (e.g., 25mg twice daily).
        - TEST: Medical tests ordered or performed.
        - RESULT: Test results including values and units.
        - FACILITY: Name of medical facilities.

        Format your response as valid JSON with this structure:
        {{
        "entities": [
            {{"type": "ENTITY_TYPE", "text": "extracted text", "start": start_position, "end": end_position}},
            ...
        ]
        }}

        Here are some examples:

        Example 1:
        Medical record:
        "Patient Maria Garcia visited Dr. Wong on January 15, 2024 for her annual checkup."
        Response:
        {{
        "entities": [
            {{"type": "PATIENT", "text": "Maria Garcia", "start": 8, "end": 20}},
            {{"type": "DOCTOR", "text": "Dr. Wong", "start": 28, "end": 36}},
            {{"type": "DATE", "text": "January 15, 2024", "start": 40, "end": 50}}
        ]
        }}

        Example 2:
        Medical record:
        "John Doe was prescribed Lisinopril 10mg once daily on March 3, 2024."
        Response:
        {{
        "entities": [
            {{"type": "PATIENT", "text": "John Doe", "start": 0, "end": 8}},
            {{"type": "MED", "text": "Lisinopril", "start": 22, "end": 32}},
            {{"type": "DOSAGE", "text": "10mg once daily", "start": 33, "end": 48}},
            {{"type": "DATE", "text": "March 3, 2024", "start": 52, "end": 64}}
        ]
        }}

                
        Format your response as a valid JSON object with the following structure:
        {{{{
        "entities": [
            {{"type": "ENTITY_TYPE", "text": "extracted text", "start": starting_character_position, "end": ending_character_position}},
            ...
        ]
        }}}}
        
        Example:
        Document: "{example_doc}"
        
        Response:
        {example_json}
        
        Now annotate this document:
        "{document}"
        
        Provide ONLY the JSON output with no additional text.
        """
        
        return SystemMessage(content=system_content), HumanMessage(content=human_content)
    
    def _parse_annotation_response(self, response_text: str, document: str) -> Optional[Dict]:
        """
        Parse and validate LLM response into structured annotations.
        """
        try:
            # Extract JSON from the response
            annotation = extract_json_from_text(response_text)
            # logging.info(f"Text from json:\n{annotation}")

            
            if not annotation or "entities" not in annotation:
                return {"entities": []}
            
            # Validate entity positions
            valid_entities = []
            for entity in annotation.get("entities", []):
                logging.info(f"\nText entities:\n{entity}")


                start = entity.get("start", 0)
                end = entity.get("end", 0)
                
                if 0 <= start < end <= len(document):
                    # Verify text matches position
                    # text_at_position = document[start:end]
                    # if text_at_position == entity.get("text"):
                    valid_entities.append(entity)

            # logging.info(f"Text in valid:\n{valid_entities}")
            
            annotation["entities"] = valid_entities
            return annotation
            
        except Exception as e:
            print(f"Error parsing annotation response: {e}")
            return {"entities": []}
    
    def _calculate_consensus_annotations(self, annotations: List[Dict]) -> List[Dict]:
        """Calculate consensus entities from multiple annotation runs."""
        if not annotations:
            return []
        
        # Use the first annotation as base if only one exists
        if len(annotations) == 1:
            return annotations[0].get("entities", [])
        
        # Extract all entities from all annotations
        all_entities = []
        for annotation in annotations:
            all_entities.extend(annotation.get("entities", []))
        
        # Group similar entities (same type and similar text spans)
        from collections import defaultdict
        grouped_entities = defaultdict(list)
        
        for entity in all_entities:
            key = (entity["type"], entity["text"])
            grouped_entities[key].append(entity)
        
        # Select consensus entities (appearing in majority of runs)
        consensus_threshold = len(annotations) / 2
        consensus_entities = []
        
        for entity_group in grouped_entities.values():
            if len(entity_group) >= consensus_threshold:
                # Use the entity with the median position
                sorted_group = sorted(entity_group, key=lambda x: x.get("start", 0))
                consensus_entities.append(sorted_group[len(sorted_group) // 2])
        
        return consensus_entities
    
    def _calculate_confidence_score(self, annotations: List[Dict], document: str) -> float:
        """Calculate overall confidence score based on annotation consistency."""
        if not annotations:
            return 0.0
        
        if len(annotations) == 1:
            # Single run confidence is based on position validation only
            entities = annotations[0].get("entities", [])
            if not entities:
                return 0.5
            
            # Check positions
            valid_positions = sum(1 for e in entities 
                                if 0 <= e.get("start", 0) < e.get("end", 0) <= len(document)
                                and document[e.get("start", 0):e.get("end", 0)] == e.get("text", ""))
            
            return valid_positions / len(entities) if entities else 0.5
        
        # For multiple runs - calculate consistency
        from collections import Counter
        
        # Extract entity keys from all annotations
        entity_keys = []
        for annotation in annotations:
            for entity in annotation.get("entities", []):
                entity_keys.append((entity["type"], entity["text"]))
        
        # Count occurrences
        key_counts = Counter(entity_keys)
        
        # Calculate consistency as average agreement rate
        max_count = len(annotations)
        consistency_scores = [count / max_count for count in key_counts.values()]
        
        avg_consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.5
        
        return avg_consistency
