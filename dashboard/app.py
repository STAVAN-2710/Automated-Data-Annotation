# # dashboard/app.py
# import streamlit as st
# import pandas as pd
# import plotly.express as px
# import json
# import os
# import sys
# import re
# from datetime import datetime

# # Add the parent directory to path to import from other modules
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# # Import your existing modules
# from storage.memory_store import MemoryStore
# from core.human_review import (
#     _modify_entity_during_review, 
#     _get_entity_context,
#     calculate_correction_impact
# )
# from utils.helpers import format_entity_for_display
# # Import your process_document function
# from main import process_document

# # Page configuration
# st.set_page_config(
#     page_title="Advanced Text Annotation Framework",
#     page_icon="📝",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Initialize data store
# store = MemoryStore()

# def document_annotation_page():
#     """Interactive document annotation interface with review capabilities."""
#     st.title("Document Annotation and Review")
    
#     # Document input area
#     document = st.text_area(
#         "Enter medical document text to annotate:",
#         height=200,
#         placeholder="Example: Patient John Smith (DOB: 04/15/1975) was admitted on March 3, 2024, with complaints of chest pain..."
#     )
    
#     # Entity type selection
#     entity_types = ["PATIENT", "DATE", "DOCTOR", "MED", "DOSAGE", "TEST", "RESULT", "FACILITY"]
#     selected_types = st.multiselect("Select entity types to extract:", entity_types, default=entity_types)
    
#     # Annotation trigger
#     if st.button("Annotate Document") and document and selected_types:
#         # Process the document using your existing pipeline
#         with st.spinner("Processing document..."):
#             result = process_document(document, selected_types)
            
#             # Store result in session state for review access
#             st.session_state.last_result = result
            
#             # Display annotation results
#             display_annotation_results(result)
            
#             # Show review option if needed
#             if result.get("needs_human_review", False):
#                 if st.button("Begin Human Review"):
#                     st.session_state.show_review = True
#                     st.experimental_rerun()
#             else:
#                 st.success("Document annotated successfully! No human review required.")
    
#     # Show review interface if requested
#     if "show_review" in st.session_state and st.session_state.show_review:
#         if "last_result" in st.session_state:
#             document_id = st.session_state.last_result.get("_id")
#             if document_id:
#                 display_human_review(document_id)

# def display_annotation_results(result):
#     """Display annotation results in Streamlit."""
#     st.subheader("Annotation Results")
    
#     # Create metrics row
#     col1, col2, col3, col4 = st.columns(4)
#     with col1:
#         st.metric("Model Used", result.get("model_name", "unknown"))
#     with col2:
#         st.metric("Confidence Score", f"{result.get('confidence_score', 0):.2f}")
#     with col3:
#         st.metric("Validation Score", f"{result.get('validation_score', 0):.2f}")
#     with col4:
#         needs_review = "Yes" if result.get("needs_human_review", True) else "No"
#         st.metric("Needs Review", needs_review)
    
#     # Show review reason if needed
#     if result.get("needs_human_review", False):
#         st.warning(f"Review reason: {result.get('review_reason', 'Unknown')}")
    
#     # Display entities table
#     st.subheader("Extracted Entities")
    
#     # Create entity table
#     entity_data = []
#     for entity in result.get("entities", []):
#         entity_data.append({
#             "Type": entity.get("type", ""),
#             "Text": entity.get("text", ""),
#             "Position": f"{entity.get('start', 0)}:{entity.get('end', 0)}",
#             "Valid": "✅" if entity.get("validation", {}).get("valid", True) else "❌",
#             "Issues": ", ".join(entity.get("validation", {}).get("issues", [])) if not entity.get("validation", {}).get("valid", True) else ""
#         })
    
#     if entity_data:
#         st.dataframe(pd.DataFrame(entity_data), use_container_width=True)
    
#     # Show highlighted document
#     st.subheader("Document with Highlighted Entities")
#     highlighted_text = highlight_entities_in_text(result.get("document", ""), result.get("entities", []))
#     st.markdown(highlighted_text, unsafe_allow_html=True)

# def display_human_review(document_id):
#     """Interactive human review interface within Streamlit."""
#     st.subheader("Human Review Interface")
    
#     # Get annotation from storage
#     annotation = store.find_by_id(document_id)
    
#     if not annotation:
#         st.error("Could not retrieve annotation data.")
#         return
    
#     document_text = annotation.get("document", "")
#     entities = annotation.get("entities", [])
    
#     # Document verification
#     st.info(f"Document begins with: '{document_text[:50]}...'")
#     is_correct = st.radio("Is this the correct document?", ["Yes", "No"], index=0)
    
#     if is_correct == "No":
#         st.warning("Document verification failed - returning to annotation")
#         st.session_state.show_review = False
#         return
    
#     # Initialize review state
#     if "corrected_entities" not in st.session_state:
#         st.session_state.corrected_entities = entities.copy()
    
#     # Flag problematic entities
#     problematic_entities = []
#     review_reason = annotation.get("review_reason", "")
    
#     # Extract types with issues from review reason
#     issue_types = []
#     if "validation issues" in review_reason.lower():
#         issue_matches = re.findall(r"([A-Z]+): ([^;]+)", review_reason)
#         issue_types = [entity_type for entity_type, _ in issue_matches]
    
#     # Mark entities that need review
#     for i, entity in enumerate(entities):
#         needs_review = False
#         validation = entity.get("validation", {})
#         entity_type = entity.get("type", "")
        
#         # Flag entity if it has validation issues or its type is mentioned in review reason
#         if not validation.get("valid", True) or entity_type in issue_types:
#             needs_review = True
            
#         problematic_entities.append({
#             "index": i,
#             "entity": entity,
#             "needs_review": needs_review
#         })
    
#     # Display all entities with flags
#     st.write("### Current Entities")
#     entity_table_data = []
#     for i, item in enumerate(problematic_entities):
#         entity = item["entity"]
#         flag = "[NEEDS REVIEW]" if item["needs_review"] else ""
#         entity_table_data.append({
#             "Index": i+1,
#             "Type": entity.get("type", ""),
#             "Text": entity.get("text", ""),
#             "Position": f"{entity.get('start', 0)}:{entity.get('end', 0)}",
#             "Status": "❌ Needs Review" if item["needs_review"] else "✅ Valid"
#         })
    
#     st.dataframe(pd.DataFrame(entity_table_data), use_container_width=True)
    
#     # Review options
#     st.write("### Review Options")
#     review_option = st.radio(
#         "Select review option:",
#         ["Review and correct flagged entities", "Add missing entities", "Accept all entities as-is", "Cancel review"],
#         key="review_option"
#     )
    
#     if review_option == "Review and correct flagged entities":
#         # Show entities needing review
#         for i, item in enumerate(problematic_entities):
#             if item["needs_review"]:
#                 entity = item["entity"]
#                 entity_idx = item["index"]
                
#                 st.markdown(f"**Reviewing: {entity.get('type')}: '{entity.get('text')}' ({entity.get('start')}:{entity.get('end')})**")
                
#                 # Show context
#                 context = _get_entity_context(document_text, entity)
#                 st.markdown(f"**Context:** {context}", unsafe_allow_html=True)
                
#                 # Actions
#                 action = st.radio(
#                     "Action:",
#                     ["Accept as-is", "Modify", "Delete", "Skip"],
#                     key=f"action_{i}"
#                 )
                
#                 if action == "Modify":
#                     # Show current values
#                     st.write("Current values:")
#                     st.write(f"- Type: {entity['type']}")
#                     st.write(f"- Text: {entity['text']}")
#                     st.write(f"- Start: {entity['start']}")
#                     st.write(f"- End: {entity['end']}")
                    
#                     # Fields for modification
#                     new_type = st.text_input(f"New type (or keep '{entity['type']}')", 
#                                             value=entity['type'], key=f"type_{i}")
#                     new_text = st.text_input(f"New text (or keep '{entity['text']}')", 
#                                           value=entity['text'], key=f"text_{i}")
                    
#                     if st.button("Apply Modification", key=f"apply_{i}"):
#                         # Update type
#                         if new_type != entity['type']:
#                             st.session_state.corrected_entities[entity_idx]["type"] = new_type
                        
#                         # Update text and recalculate positions
#                         if new_text != entity['text']:
#                             st.session_state.corrected_entities[entity_idx] = _modify_entity_during_review(
#                                 document_text,
#                                 st.session_state.corrected_entities[entity_idx],
#                                 new_text
#                             )
#                         st.success("Entity updated!")
                
#                 elif action == "Delete":
#                     if st.button(f"Confirm deletion", key=f"delete_{i}"):
#                         # Remove entity from corrected list
#                         del st.session_state.corrected_entities[entity_idx]
#                         st.success(f"Entity '{entity['text']}' deleted!")
#                         st.experimental_rerun()
                
#                 st.markdown("---")
    
#     elif review_option == "Add missing entities":
#         with st.form("add_entity_form"):
#             st.write("### Add Missing Entity")
            
#             entity_type = st.selectbox(
#                 "Entity type:",
#                 ["PATIENT", "DATE", "DOCTOR", "MED", "DOSAGE", "TEST", "RESULT", "FACILITY"]
#             )
#             entity_text = st.text_input("Entity text:")
            
#             submitted = st.form_submit_button("Add Entity")
#             if submitted and entity_text:
#                 # Find position in text
#                 start_pos = document_text.find(entity_text)
#                 if start_pos >= 0:
#                     end_pos = start_pos + len(entity_text)
#                     new_entity = {
#                         "type": entity_type,
#                         "text": entity_text,
#                         "start": start_pos,
#                         "end": end_pos,
#                         "validation": {"valid": True, "issues": []}
#                     }
#                     st.session_state.corrected_entities.append(new_entity)
#                     st.success(f"Added new entity: {entity_type} - '{entity_text}'")
#                 else:
#                     st.error(f"Could not find '{entity_text}' in document.")
    
#     elif review_option == "Accept all entities as-is":
#         st.write("All entities will be accepted as currently shown.")
        
#         # Mark all entities as valid
#         for entity in st.session_state.corrected_entities:
#             if "validation" in entity:
#                 entity["validation"]["valid"] = True
#                 entity["validation"]["issues"] = []
    
#     elif review_option == "Cancel review":
#         if st.button("Confirm cancellation"):
#             st.warning("Review cancelled, no changes made")
#             st.session_state.show_review = False
#             del st.session_state.corrected_entities
#             return
    
#     # Display current corrected entities
#     if "corrected_entities" in st.session_state:
#         st.write("### Current Corrected Entities")
#         corrected_table = []
#         for i, entity in enumerate(st.session_state.corrected_entities):
#             corrected_table.append({
#                 "Index": i+1,
#                 "Type": entity.get("type", ""),
#                 "Text": entity.get("text", ""),
#                 "Position": f"{entity.get('start', 0)}:{entity.get('end', 0)}",
#                 "Valid": "✅" if entity.get("validation", {}).get("valid", True) else "❌"
#             })
        
#         st.dataframe(pd.DataFrame(corrected_table), use_container_width=True)
    
#     # Submit corrections button
#     if st.button("Submit Review"):
#         # Submit to storage
#         result = store.update_after_review(document_id, st.session_state.corrected_entities)
        
#         # Calculate impact
#         impact = calculate_correction_impact(entities, st.session_state.corrected_entities)
        
#         # Display success message
#         st.success("Corrections submitted successfully!")
        
#         # Show impact of corrections
#         st.write("### Correction Impact")
#         impact_cols = st.columns(5)
#         with impact_cols[0]:
#             st.metric("Original Count", impact['original_count'])
#         with impact_cols[1]:
#             st.metric("Corrected Count", impact['corrected_count'])
#         with impact_cols[2]:
#             st.metric("Modified", impact['modified'])
#         with impact_cols[3]:
#             st.metric("Added", impact['added'])
#         with impact_cols[4]:
#             st.metric("Removed", impact['removed'])
        
#         # Reset review state
#         st.session_state.show_review = False
#         del st.session_state.corrected_entities
        
#         if st.button("Annotate Another Document"):
#             st.experimental_rerun()

# def highlight_entities_in_text(text, entities):
#     """Create HTML with highlighted entities in the text."""
#     # Convert the text to HTML with proper escaping
#     import html
#     html_text = html.escape(text)
    
#     # Create spans for each entity, starting from the end to avoid position changes
#     sorted_entities = sorted(entities, key=lambda x: x.get("start", 0), reverse=True)
    
#     for entity in sorted_entities:
#         entity_type = entity.get("type", "")
#         start = entity.get("start", 0)
#         end = entity.get("end", 0)
#         is_valid = entity.get("validation", {}).get("valid", True)
        
#         # Select color based on entity type
#         color_map = {
#             "PATIENT": "#FF9999",
#             "DATE": "#99FF99",
#             "DOCTOR": "#9999FF",
#             "MED": "#FFFF99",
#             "DOSAGE": "#FF99FF",
#             "TEST": "#99FFFF",
#             "RESULT": "#FFCC99",
#             "FACILITY": "#99CCFF"
#         }
        
#         background_color = color_map.get(entity_type, "#DDDDDD")
        
#         # Add border if invalid
#         border_style = "border: 1px solid red;" if not is_valid else ""
        
#         # Create the span
#         span = f'<span style="background-color: {background_color}; {border_style}" title="{entity_type}">{html_text[start:end]}</span>'
        
#         # Replace the text with the span
#         html_text = html_text[:start] + span + html_text[end:]
    
#     # Wrap in a div with styling
#     return f'<div style="font-family: monospace; white-space: pre-wrap; line-height: 1.5;">{html_text}</div>'

# def display_annotations_explorer():
#     """Display annotation history and allow browsing previous annotations."""
#     st.title("Annotation Explorer")
    
#     # Get all annotations
#     annotations = []
#     for annotation_id, annotation in store._annotations_cache.items():
#         annotations.append({
#             "id": annotation_id,
#             "timestamp": annotation.get("timestamp", ""),
#             "model_name": annotation.get("model_name", ""),
#             "confidence_score": annotation.get("confidence_score", 0),
#             "validation_score": annotation.get("validation_score", 0),
#             "needs_human_review": annotation.get("needs_human_review", True),
#             "entity_count": len(annotation.get("entities", [])),
#             "document_preview": annotation.get("document", "")[:100] + "..."
#         })
    
#     if not annotations:
#         st.warning("No annotations found. Process some documents first!")
#         return
    
#     # Convert to DataFrame and sort by timestamp
#     df = pd.DataFrame(annotations)
#     if "timestamp" in df.columns:
#         df["timestamp"] = pd.to_datetime(df["timestamp"])
#         df = df.sort_values("timestamp", ascending=False)
    
#     # Display annotations table
#     st.dataframe(df, use_container_width=True)
    
#     # Select annotation to view details
#     selected_id = st.selectbox("Select annotation to view details:", df["id"].tolist())
    
#     if selected_id:
#         # Get full annotation
#         annotation = store.find_by_id(selected_id)
        
#         if annotation:
#             # Display document and results
#             st.subheader("Document Text")
#             st.text_area("Full Document", annotation.get("document", ""), height=150)
            
#             # Display entity table
#             st.subheader("Extracted Entities")
#             entity_data = []
#             for entity in annotation.get("entities", []):
#                 entity_data.append({
#                     "Type": entity.get("type", ""),
#                     "Text": entity.get("text", ""),
#                     "Position": f"{entity.get('start', 0)}:{entity.get('end', 0)}",
#                     "Valid": "✅" if entity.get("validation", {}).get("valid", True) else "❌",
#                     "Issues": ", ".join(entity.get("validation", {}).get("issues", [])) if not entity.get("validation", {}).get("valid", True) else ""
#                 })
            
#             if entity_data:
#                 st.dataframe(pd.DataFrame(entity_data), use_container_width=True)
            
#             # Show highlighted document
#             st.subheader("Document with Highlighted Entities")
#             highlighted_text = highlight_entities_in_text(annotation.get("document", ""), annotation.get("entities", []))
#             st.markdown(highlighted_text, unsafe_allow_html=True)

# def display_statistics():
#     """Display annotation statistics and metrics dashboard."""
#     st.title("Annotation Statistics Dashboard")
    
#     # Get statistics from store
#     stats = {
#         "total_annotations": len(store._annotations_cache),
#         "auto_approved": sum(1 for a in store._annotations_cache.values() if not a.get("needs_human_review", True)),
#         "needs_review": sum(1 for a in store._annotations_cache.values() if a.get("needs_human_review", True)),
#         "total_corrections": len(store._corrections_cache)
#     }
    
#     # Calculate derived statistics
#     stats["auto_approval_rate"] = stats["auto_approved"] / stats["total_annotations"] if stats["total_annotations"] > 0 else 0
    
#     # Display key metrics
#     st.subheader("Key Metrics")
#     col1, col2, col3, col4 = st.columns(4)
    
#     with col1:
#         st.metric("Total Annotations", stats["total_annotations"])
#     with col2:
#         st.metric("Auto-Approved", f"{stats['auto_approved']} ({stats['auto_approval_rate']*100:.1f}%)")
#     with col3:
#         st.metric("Needs Review", stats["needs_review"])
#     with col4:
#         st.metric("Total Corrections", stats["total_corrections"])
    
#     # Get entity statistics
#     all_entities = []
#     for annotation in store._annotations_cache.values():
#         entities = annotation.get("entities", [])
#         for entity in entities:
#             all_entities.append({
#                 "type": entity.get("type", ""),
#                 "valid": entity.get("validation", {}).get("valid", True)
#             })
    
#     if all_entities:
#         # Convert to DataFrame
#         entity_df = pd.DataFrame(all_entities)
        
#         # Entity type distribution
#         st.subheader("Entity Type Distribution")
#         type_counts = entity_df["type"].value_counts().reset_index()
#         type_counts.columns = ["entity_type", "count"]
        
#         fig = px.pie(
#             type_counts,
#             values="count",
#             names="entity_type",
#             title="Distribution of Entity Types"
#         )
#         st.plotly_chart(fig, use_container_width=True)
        
#         # Validation status by entity type
#         st.subheader("Validation Status by Entity Type")
#         validation_by_type = entity_df.groupby(["type", "valid"]).size().reset_index(name="count")
        
#         fig = px.bar(
#             validation_by_type,
#             x="type",
#             y="count",
#             color="valid",
#             title="Entity Validation Status by Type",
#             labels={"type": "Entity Type", "count": "Count", "valid": "Is Valid"},
#             color_discrete_map={True: "green", False: "red"}
#         )
#         st.plotly_chart(fig, use_container_width=True)

# def main():
#     """Main function for the Streamlit app."""
#     st.sidebar.title("Advanced Text Annotation")
    
#     # Navigation
#     page = st.sidebar.radio(
#         "Select a page",
#         ["Document Annotation", "Annotations Explorer", "Statistics Dashboard"]
#     )
    
#     # Display the selected page
#     if page == "Document Annotation":
#         document_annotation_page()
#     elif page == "Annotations Explorer":
#         display_annotations_explorer()
#     elif page == "Statistics Dashboard":
#         display_statistics()
    
#     # Add info about the app
#     st.sidebar.info(
#         "This dashboard allows you to annotate medical documents using AI, "
#         "review and correct annotations, and view statistics on annotation quality."
#     )

# if __name__ == "__main__":
#     main()
# dashboard/app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import sys
import re
from datetime import datetime, timedelta

# Add the parent directory to path to import from other modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your existing modules
from storage.file_store import FileStore
from core.human_review import (
    _modify_entity_during_review, 
    _get_entity_context,
    calculate_correction_impact
)
from utils.helpers import format_entity_for_display
# Import your process_document function
from main import process_document

# Page configuration
st.set_page_config(
    page_title="Advanced Text Annotation Framework",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize file storage
store = FileStore()

def document_annotation_page():
    """Interactive document annotation interface with review capabilities."""
    st.title("Document Annotation and Review")
    
    # Initialize session state variables if they don't exist
    if "phase" not in st.session_state:
        st.session_state.phase = "input"  # Phases: input, results, review
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "review_document_id" not in st.session_state:
        st.session_state.review_document_id = None
    
    # Handle review phase first
    if st.session_state.phase == "review" and st.session_state.review_document_id:
        # Show review interface
        display_human_review(st.session_state.review_document_id)
        return  # Exit the function to avoid showing the annotation interface
    
    # Input and results phases
    # Document input area
    document = st.text_area(
        "Enter medical document text to annotate:",
        height=200,
        placeholder="Example: Patient John Smith (DOB: 04/15/1975) was admitted on March 3, 2024, with complaints of chest pain..."
    )
    
    # Entity type selection
    entity_types = ["PATIENT", "DATE", "DOCTOR", "MED", "DOSAGE", "TEST", "RESULT", "FACILITY"]
    selected_types = st.multiselect("Select entity types to extract:", entity_types, default=entity_types)
    
    # Annotation trigger
    if st.button("Annotate Document") and document and selected_types:
        # Process the document using your existing pipeline
        with st.spinner("Processing document..."):
            result = process_document(document, selected_types)
            
            # Store result in session state for review access
            st.session_state.last_result = result
            st.session_state.phase = "results"
            
            # Display annotation results
            display_annotation_results(result)
            
            # Show review option if needed
            if result.get("needs_human_review", False):
                if st.button("Begin Human Review", key="begin_review_button"):
                    st.session_state.phase = "review"
                    st.session_state.review_document_id = result.get("_id")
                    st.rerun()
            else:
                st.success("Document annotated successfully! No human review required.")
    
    # Display previous results if in results phase
    elif st.session_state.phase == "results" and st.session_state.last_result:
        result = st.session_state.last_result
        display_annotation_results(result)
        
        # Show review button for previous result
        if result.get("needs_human_review", False):
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Begin Human Review", key="review_button"):
                    st.session_state.phase = "review"
                    st.session_state.review_document_id = result.get("_id")
                    st.rerun()


def display_annotation_results(result):
    """Display annotation results in Streamlit."""
    st.subheader("Annotation Results")
    
    # Create metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Model Used", result.get("model_name", "unknown"))
    with col2:
        st.metric("Confidence Score", f"{result.get('confidence_score', 0):.2f}")
    with col3:
        st.metric("Validation Score", f"{result.get('validation_score', 0):.2f}")
    with col4:
        needs_review = "Yes" if result.get("needs_human_review", True) else "No"
        st.metric("Needs Review", needs_review)
    
    # Show review reason if needed
    if result.get("needs_human_review", False):
        st.warning(f"Review reason: {result.get('review_reason', 'Unknown')}")
    
    # Display entities table
    st.subheader("Extracted Entities")
    
    # Create entity table
    entity_data = []
    for entity in result.get("entities", []):
        entity_data.append({
            "Type": entity.get("type", ""),
            "Text": entity.get("text", ""),
            "Position": f"{entity.get('start', 0)}:{entity.get('end', 0)}",
            "Valid": "✅" if entity.get("validation", {}).get("valid", True) else "❌",
            "Issues": ", ".join(entity.get("validation", {}).get("issues", [])) if not entity.get("validation", {}).get("valid", True) else ""
        })
    
    if entity_data:
        st.dataframe(pd.DataFrame(entity_data), use_container_width=True)
    
    # Show highlighted document
    st.subheader("Document with Highlighted Entities")
    highlighted_text = highlight_entities_in_text(result.get("document", ""), result.get("entities", []))
    st.markdown(highlighted_text, unsafe_allow_html=True)

def display_human_review(document_id):
    """Interactive human review interface within Streamlit."""
    st.subheader("Human Review Interface")

    # Add a button to return to annotation
    if st.button("← Return to Annotation"):
        st.session_state.phase = "input"
        st.rerun()
        return
    
    # Get annotation from storage
    annotation = store.find_by_id(document_id)
    
    if not annotation:
        st.error("Could not retrieve annotation data.")
        return
    
    document_text = annotation.get("document", "")
    entities = annotation.get("entities", [])
    
    # Document verification
    st.info(f"Document begins with: '{document_text[:50]}...'")
    is_correct = st.radio("Is this the correct document?", ["Yes", "No"], index=0)
    
    if is_correct == "No":
        st.warning("Document verification failed - returning to annotation")
        st.session_state.show_review = False
        return
    
    # Initialize review state
    if "corrected_entities" not in st.session_state:
        st.session_state.corrected_entities = entities.copy()
    
    # Flag problematic entities
    problematic_entities = []
    review_reason = annotation.get("review_reason", "")
    
    # Extract types with issues from review reason
    issue_types = []
    if "validation issues" in review_reason.lower():
        issue_matches = re.findall(r"([A-Z]+): ([^;]+)", review_reason)
        issue_types = [entity_type for entity_type, _ in issue_matches]
    
    # Mark entities that need review
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
    
    # Display all entities with flags
    st.write("### Current Entities")
    entity_table_data = []
    for i, item in enumerate(problematic_entities):
        entity = item["entity"]
        flag = "[NEEDS REVIEW]" if item["needs_review"] else ""
        entity_table_data.append({
            "Index": i+1,
            "Type": entity.get("type", ""),
            "Text": entity.get("text", ""),
            "Position": f"{entity.get('start', 0)}:{entity.get('end', 0)}",
            "Status": "❌ Needs Review" if item["needs_review"] else "✅ Valid"
        })
    
    st.dataframe(pd.DataFrame(entity_table_data), use_container_width=True)
    
    # Review options
    st.write("### Review Options")
    review_option = st.radio(
        "Select review option:",
        ["Review and correct flagged entities", "Add missing entities", "Accept all entities as-is", "Cancel review"],
        key="review_option"
    )
    
    if review_option == "Review and correct flagged entities":
        # Show entities needing review
        for i, item in enumerate(problematic_entities):
            if item["needs_review"]:
                entity = item["entity"]
                entity_idx = item["index"]
                
                st.markdown(f"**Reviewing: {entity.get('type')}: '{entity.get('text')}' ({entity.get('start')}:{entity.get('end')})**")
                
                # Show context
                context = _get_entity_context(document_text, entity)
                st.markdown(f"**Context:** {context}", unsafe_allow_html=True)
                
                # Actions
                action = st.radio(
                    "Action:",
                    ["Accept as-is", "Modify", "Delete", "Skip"],
                    key=f"action_{i}"
                )
                
                if action == "Modify":
                    # Show current values
                    st.write("Current values:")
                    st.write(f"- Type: {entity['type']}")
                    st.write(f"- Text: {entity['text']}")
                    st.write(f"- Start: {entity['start']}")
                    st.write(f"- End: {entity['end']}")
                    
                    # Fields for modification
                    new_type = st.text_input(f"New type (or keep '{entity['type']}')", 
                                            value=entity['type'], key=f"type_{i}")
                    new_text = st.text_input(f"New text (or keep '{entity['text']}')", 
                                          value=entity['text'], key=f"text_{i}")
                    
                    if st.button("Apply Modification", key=f"apply_{i}"):
                        # Update type
                        if new_type != entity['type']:
                            st.session_state.corrected_entities[entity_idx]["type"] = new_type
                        
                        # Update text and recalculate positions
                        if new_text != entity['text']:
                            st.session_state.corrected_entities[entity_idx] = _modify_entity_during_review(
                                document_text,
                                st.session_state.corrected_entities[entity_idx],
                                new_text
                            )
                        st.success("Entity updated!")
                
                elif action == "Delete":
                    if st.button(f"Confirm deletion", key=f"delete_{i}"):
                        # Remove entity from corrected list
                        del st.session_state.corrected_entities[entity_idx]
                        st.success(f"Entity '{entity['text']}' deleted!")
                        st.experimental_rerun()
                
                st.markdown("---")
    
    elif review_option == "Add missing entities":
        with st.form("add_entity_form"):
            st.write("### Add Missing Entity")
            
            entity_type = st.selectbox(
                "Entity type:",
                ["PATIENT", "DATE", "DOCTOR", "MED", "DOSAGE", "TEST", "RESULT", "FACILITY"]
            )
            entity_text = st.text_input("Entity text:")
            
            submitted = st.form_submit_button("Add Entity")
            if submitted and entity_text:
                # Find position in text
                start_pos = document_text.find(entity_text)
                if start_pos >= 0:
                    end_pos = start_pos + len(entity_text)
                    new_entity = {
                        "type": entity_type,
                        "text": entity_text,
                        "start": start_pos,
                        "end": end_pos,
                        "validation": {"valid": True, "issues": []}
                    }
                    st.session_state.corrected_entities.append(new_entity)
                    st.success(f"Added new entity: {entity_type} - '{entity_text}'")
                else:
                    st.error(f"Could not find '{entity_text}' in document.")
    
    elif review_option == "Accept all entities as-is":
        st.write("All entities will be accepted as currently shown.")
        
        # Mark all entities as valid
        for entity in st.session_state.corrected_entities:
            if "validation" in entity:
                entity["validation"]["valid"] = True
                entity["validation"]["issues"] = []
    
    elif review_option == "Cancel review":
        if st.button("Confirm cancellation"):
            st.warning("Review cancelled, no changes made")
            st.session_state.show_review = False
            del st.session_state.corrected_entities
            return
    
    # Display current corrected entities
    if "corrected_entities" in st.session_state:
        st.write("### Current Corrected Entities")
        corrected_table = []
        for i, entity in enumerate(st.session_state.corrected_entities):
            corrected_table.append({
                "Index": i+1,
                "Type": entity.get("type", ""),
                "Text": entity.get("text", ""),
                "Position": f"{entity.get('start', 0)}:{entity.get('end', 0)}",
                "Valid": "✅" if entity.get("validation", {}).get("valid", True) else "❌"
            })
        
        st.dataframe(pd.DataFrame(corrected_table), use_container_width=True)
    
    # Submit corrections button
    if st.button("Submit Review"):
        # Submit to storage
        result = store.update_after_review(document_id, st.session_state.corrected_entities)
        
        # Calculate impact
        impact = calculate_correction_impact(entities, st.session_state.corrected_entities)
        
        # Display success message
        st.success("Corrections submitted successfully!")
        
        # Show impact of corrections
        st.write("### Correction Impact")
        impact_cols = st.columns(5)
        with impact_cols[0]:
            st.metric("Original Count", impact['original_count'])
        with impact_cols[1]:
            st.metric("Corrected Count", impact['corrected_count'])
        with impact_cols[2]:
            st.metric("Modified", impact['modified'])
        with impact_cols[3]:
            st.metric("Added", impact['added'])
        with impact_cols[4]:
            st.metric("Removed", impact['removed'])
        
        # Reset review state
        st.session_state.show_review = False
        del st.session_state.corrected_entities
        
        if st.button("Annotate Another Document"):
            st.experimental_rerun()

def highlight_entities_in_text(text, entities):
    """Create HTML with highlighted entities in the text."""
    # Convert the text to HTML with proper escaping
    import html
    html_text = html.escape(text)
    
    # Create spans for each entity, starting from the end to avoid position changes
    sorted_entities = sorted(entities, key=lambda x: x.get("start", 0), reverse=True)
    
    for entity in sorted_entities:
        entity_type = entity.get("type", "")
        start = entity.get("start", 0)
        end = entity.get("end", 0)
        is_valid = entity.get("validation", {}).get("valid", True)
        
        # Select color based on entity type
        color_map = {
            "PATIENT": "#FF9999",
            "DATE": "#99FF99",
            "DOCTOR": "#9999FF",
            "MED": "#FFFF99",
            "DOSAGE": "#FF99FF",
            "TEST": "#99FFFF",
            "RESULT": "#FFCC99",
            "FACILITY": "#99CCFF"
        }
        
        background_color = color_map.get(entity_type, "#DDDDDD")
        
        # Add border if invalid
        border_style = "border: 1px solid red;" if not is_valid else ""
        
        # Create the span
        span = f'<span style="background-color: {background_color}; {border_style}" title="{entity_type}">{html_text[start:end]}</span>'
        
        # Replace the text with the span
        html_text = html_text[:start] + span + html_text[end:]
    
    # Wrap in a div with styling
    return f'<div style="font-family: monospace; white-space: pre-wrap; line-height: 1.5;">{html_text}</div>'

def display_annotations_explorer():
    """Display annotation history and allow browsing previous annotations."""
    st.title("Annotation Explorer")
    
    # Get all annotations
    annotations = []
    for annotation_id, annotation in store._annotations_cache.items():
        annotations.append({
            "id": annotation_id,
            "timestamp": annotation.get("timestamp", ""),
            "model_name": annotation.get("model_name", ""),
            "confidence_score": annotation.get("confidence_score", 0),
            "validation_score": annotation.get("validation_score", 0),
            "needs_human_review": annotation.get("needs_human_review", True),
            "entity_count": len(annotation.get("entities", [])),
            "document_preview": annotation.get("document", "")[:100] + "..."
        })
    
    if not annotations:
        st.warning("No annotations found. Process some documents first!")
        return
    
    # Convert to DataFrame and sort by timestamp
    df = pd.DataFrame(annotations)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp", ascending=False)
    
    # Display annotations table
    st.dataframe(df, use_container_width=True)
    
    # Select annotation to view details
    selected_id = st.selectbox("Select annotation to view details:", df["id"].tolist())
    
    if selected_id:
        # Get full annotation
        annotation = store.find_by_id(selected_id)
        
        if annotation:
            # Display document and results
            st.subheader("Document Text")
            st.text_area("Full Document", annotation.get("document", ""), height=150)
            
            # Display entity table
            st.subheader("Extracted Entities")
            entity_data = []
            for entity in annotation.get("entities", []):
                entity_data.append({
                    "Type": entity.get("type", ""),
                    "Text": entity.get("text", ""),
                    "Position": f"{entity.get('start', 0)}:{entity.get('end', 0)}",
                    "Valid": "✅" if entity.get("validation", {}).get("valid", True) else "❌",
                    "Issues": ", ".join(entity.get("validation", {}).get("issues", [])) if not entity.get("validation", {}).get("valid", True) else ""
                })
            
            if entity_data:
                st.dataframe(pd.DataFrame(entity_data), use_container_width=True)
            
            # Show highlighted document
            st.subheader("Document with Highlighted Entities")
            highlighted_text = highlight_entities_in_text(annotation.get("document", ""), annotation.get("entities", []))
            st.markdown(highlighted_text, unsafe_allow_html=True)

def display_statistics():
    """Display annotation statistics and metrics dashboard."""
    st.title("Annotation Statistics Dashboard")
    
    # Get statistics from store
    stats = store.get_statistics()
    
    # Display key metrics
    st.subheader("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Annotations", stats["total_annotations"])
    with col2:
        st.metric("Auto-Approved", f"{stats['auto_approved']} ({stats['auto_approval_rate']*100:.1f}%)")
    with col3:
        st.metric("Needs Review", stats["needs_review"])
    with col4:
        st.metric("Total Corrections", stats["total_corrections"])
    
    # Get entity statistics
    all_entities = []
    for annotation in store._annotations_cache.values():
        entities = annotation.get("entities", [])
        for entity in entities:
            all_entities.append({
                "type": entity.get("type", ""),
                "valid": entity.get("validation", {}).get("valid", True)
            })
    
    if all_entities:
        # Convert to DataFrame
        entity_df = pd.DataFrame(all_entities)
        
        # Entity type distribution
        st.subheader("Entity Type Distribution")
        type_counts = entity_df["type"].value_counts().reset_index()
        type_counts.columns = ["entity_type", "count"]
        
        fig = px.pie(
            type_counts,
            values="count",
            names="entity_type",
            title="Distribution of Entity Types"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Validation status by entity type
        st.subheader("Validation Status by Entity Type")
        validation_by_type = entity_df.groupby(["type", "valid"]).size().reset_index(name="count")
        
        fig = px.bar(
            validation_by_type,
            x="type",
            y="count",
            color="valid",
            title="Entity Validation Status by Type",
            labels={"type": "Entity Type", "count": "Count", "valid": "Is Valid"},
            color_discrete_map={True: "green", False: "red"}
        )
        st.plotly_chart(fig, use_container_width=True)

def main():
    """Main function for the Streamlit app."""
    st.sidebar.title("Advanced Text Annotation")
    
    # Navigation
    page = st.sidebar.radio(
        "Select a page",
        ["Document Annotation", "Annotations Explorer", "Statistics Dashboard"]
    )
    
    # Display the selected page
    if page == "Document Annotation":
        document_annotation_page()
    elif page == "Annotations Explorer":
        display_annotations_explorer()
    elif page == "Statistics Dashboard":
        display_statistics()
    
    # Add info about the app
    st.sidebar.info(
        "This dashboard allows you to annotate medical documents using AI, "
        "review and correct annotations, and view statistics on annotation quality."
    )

if __name__ == "__main__":
    main()
