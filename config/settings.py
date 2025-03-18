# config/settings.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenAI API configuration (used by LangChain)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model settings
DEFAULT_MODEL_NAME = "gpt-3.5-turbo"
HIGH_ACCURACY_MODEL_NAME = "gpt-4o"
DEFAULT_TEMPERATURE = 0.2
ANNOTATION_RUNS = 3  # Number of runs for consistency scoring

# Confidence thresholds
CONFIDENCE_THRESHOLD = 0.85
VALIDATION_THRESHOLD = 0.90

# Entity validation weights
CONFIDENCE_WEIGHTS = {
    "format": 0.2,
    "position": 0.4,
    "rules": 0.4
}

# Entity type descriptions for prompts
ENTITY_DESCRIPTIONS = {
    "PATIENT": "Patient name (first and last name)",
    "DATE": "Any dates mentioned (birth dates, appointment dates, etc.)",
    "DOCTOR": "Healthcare provider name with title (Dr., etc.)",
    "MED": "Medication name (only the name, not dosage)",
    "DOSAGE": "Medication dosage information (amount and frequency)",
    "TEST": "Medical tests ordered or performed",
    "RESULT": "Test results with values and units",
    "FACILITY": "Medical facility name"
}