# models/model_provider.py
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from config.settings import (
    OPENAI_API_KEY, 
    DEFAULT_MODEL_NAME, 
    HIGH_ACCURACY_MODEL_NAME, 
    DEFAULT_TEMPERATURE
)

class ModelProvider:
    """
    Provider class for LangChain models with dynamic selection capabilities.
    Uses LangChain abstractions instead of direct OpenAI API calls.
    """
    
    def __init__(self):
        # Pre-configured model instances
        self.models = {
            "default": ChatOpenAI(
                model_name=DEFAULT_MODEL_NAME,
                temperature=DEFAULT_TEMPERATURE,
                api_key=OPENAI_API_KEY
            ),
            "high_accuracy": ChatOpenAI(
                model_name=HIGH_ACCURACY_MODEL_NAME,
                temperature=DEFAULT_TEMPERATURE * 0.5,  # Lower temperature for higher precision
                api_key=OPENAI_API_KEY
            )
        }
    
    def get_model(self, model_type: str = "default") -> BaseChatModel:
        """
        Get a LangChain model instance based on the requested type.
        
        Args:
            model_type: Type of model to use ("default", "high_accuracy")
            
        Returns:
            LangChain model instance
        """
        return self.models.get(model_type, self.models["default"])
    
    def select_model_for_document(self, document: str) -> BaseChatModel:
        """
        Select appropriate model based on document complexity.
        
        Args:
            document: The document text to analyze
            
        Returns:
            Most appropriate LangChain model for the document
        """
        complexity = self._calculate_complexity(document)
        
        # Use more powerful model for complex documents
        if complexity > 0.7:
            return self.get_model("high_accuracy")
            
        return self.get_model("default")
    
    def _calculate_complexity(self, document: str) -> float:
        """
        Calculate document complexity score (0-1).
        
        Args:
            document: Document text
            
        Returns:
            Complexity score between 0 and 1
        """
        # Simple complexity based on length and sentence complexity
        words = document.split()
        length_factor = min(len(words) / 500, 1.0)
        
        sentences = document.split('.')
        avg_words_per_sentence = sum(len(s.split()) for s in sentences if s) / max(len(sentences), 1)
        sentence_complexity = min(avg_words_per_sentence / 25, 1.0)
        
        # Look for medical terminology as a complexity indicator
        medical_terms = ["diagnosis", "prescribed", "medication", "treatment", 
                        "symptoms", "patient", "clinical", "dosage"]
        term_density = sum(1 for term in medical_terms if term.lower() in document.lower()) / len(medical_terms)
        
        return (0.4 * length_factor + 0.3 * sentence_complexity + 0.3 * term_density)
