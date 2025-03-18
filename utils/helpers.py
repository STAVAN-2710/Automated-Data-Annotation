# utils/helpers.py
import json
import re
from typing import Dict, Any, Optional

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from text that might contain markdown or other content

    Args:
        text: Text possibly containing JSON

    Returns:
        Extracted JSON as dict or None if extraction failed
    """
    # First try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks with json tag
    json_code_block_pattern = r"``````"
    match = re.search(json_code_block_pattern, text, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Try extracting from any code blocks
    code_block_pattern = r"``````"
    match = re.search(code_block_pattern, text, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Try extracting JSON directly from curly braces (first to last brace)
    try:
        start_idx = text.find('{')
        end_idx = text.rfind('}') + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_str = text[start_idx:end_idx]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return None


def format_entity_for_display(entity: Dict[str, Any], include_validation: bool = True) -> str:
    """
    Format an entity for display
    
    Args:
        entity: Entity dictionary
        include_validation: Whether to include validation info
        
    Returns:
        Formatted string representation
    """
    base_info = f"{entity['type']}: '{entity['text']}' ({entity['start']}:{entity['end']})"
    
    if include_validation and "validation" in entity:
        validation = entity["validation"]
        if not validation.get("valid", True):
            issues = ", ".join(validation.get("issues", []))
            return f"{base_info} [INVALID: {issues}]"
        return f"{base_info} [VALID]"
    
    return base_info

def _get_entity_context(document_text, entity, context_size=20):
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
