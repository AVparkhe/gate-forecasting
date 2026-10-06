import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import requests
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# Pydantic models for structured JSON output
class Concept(BaseModel):
    name: str = Field(description="Name of the core concept")
    family: str = Field(description="Broader concept family")
    role: str = Field(description="'primary' or 'supporting'")

class DifficultyBreakdown(BaseModel):
    score: int = Field(ge=1, le=5, description="Overall difficulty score 1-5")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this classification 0.0-1.0")
    rationale: str = Field(description="Explanation for why this difficulty and subject were chosen")
    cognitive_level: str = Field(description="Bloom's taxonomy level (e.g. Recall, Application, Analysis)")

class EnrichmentResult(BaseModel):
    subject: str = Field(description="Subject from GATE syllabus")
    topic: str = Field(description="Topic from GATE syllabus")
    subtopic: str = Field(description="Subtopic from GATE syllabus")
    concepts: List[Concept] = Field(description="List of core concepts extracted")
    difficulty: DifficultyBreakdown = Field(description="Difficulty metrics")

class LLMProvider(ABC):
    @abstractmethod
    def enrich_question(self, question_text: str, options: Dict[str, str], marks: float, taxonomy: Dict[str, Any]) -> Dict[str, Any]:
        """Send question to LLM and return structured enrichment data."""
        pass

def get_system_prompt(taxonomy: Dict[str, Any], question_text: str, options: Dict[str, str], marks: float) -> str:
    return f"""You are an expert GATE Computer Science exam analyzer.
Your task is to classify the given question and extract core concepts according to the provided taxonomy.

TAXONOMY:
{json.dumps(taxonomy, indent=2)}

QUESTION:
{question_text}

OPTIONS:
{json.dumps(options, indent=2)}

MARKS: {marks}

INSTRUCTIONS:
1. Select the most appropriate Subject, Topic, and Subtopic ONLY from the provided Taxonomy. Do not invent new subjects.
2. Extract the core concepts required to solve the question.
3. Estimate the difficulty of the question on a scale of 1-5.
4. Provide a confidence score (0.0 to 1.0) and a rationale.
5. Determine the cognitive level (e.g., Recall, Application, Analysis, Evaluation).

Respond ONLY with a valid JSON object matching this schema:
{{
  "subject": "string",
  "topic": "string",
  "subtopic": "string",
  "concepts": [
    {{"name": "string", "family": "string", "role": "primary or supporting"}}
  ],
  "difficulty": {{
    "score": integer (1-5),
    "confidence": float (0.0-1.0),
    "rationale": "string",
    "cognitive_level": "string"
  }}
}}"""

# ---------------------------------------------------------
# 1. GOOGLE GEMINI PROVIDER
# ---------------------------------------------------------
class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-pro"):
        self.model_name = model_name
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing.")
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={"response_mime_type": "application/json"}
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise

    def enrich_question(self, question_text: str, options: Dict[str, str], marks: float, taxonomy: Dict[str, Any]) -> Dict[str, Any]:
        prompt = get_system_prompt(taxonomy, question_text, options, marks)
        response = self.model.generate_content(prompt)
        try:
            result_dict = json.loads(response.text)
            validated = EnrichmentResult(**result_dict)
            return validated.dict()
        except Exception as e:
            logger.error(f"Failed parsing Gemini output: {e}")
            raise

# ---------------------------------------------------------
# 2. ANTHROPIC CLAUDE PROVIDER (Highest CS Reasoning)
# ---------------------------------------------------------
class AnthropicProvider(LLMProvider):
    def __init__(self, model_name: str = "claude-3-5-sonnet-20241022"):
        self.model_name = model_name
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is missing.")

    def enrich_question(self, question_text: str, options: Dict[str, str], marks: float, taxonomy: Dict[str, Any]) -> Dict[str, Any]:
        prompt = get_system_prompt(taxonomy, question_text, options, marks)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "max_tokens": 1500,
            "system": "You are an expert GATE Computer Science exam analyzer. Respond ONLY with valid JSON.",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        res = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        content_text = data["content"][0]["text"].strip()
        # Clean possible markdown fence
        if content_text.startswith("```json"):
            content_text = content_text[7:]
        if content_text.endswith("```"):
            content_text = content_text[:-3]
        result_dict = json.loads(content_text.strip())
        validated = EnrichmentResult(**result_dict)
        return validated.dict()

# ---------------------------------------------------------
# 3. OPENAI GPT-4o PROVIDER
# ---------------------------------------------------------
class OpenAIProvider(LLMProvider):
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is missing.")

    def enrich_question(self, question_text: str, options: Dict[str, str], marks: float, taxonomy: Dict[str, Any]) -> Dict[str, Any]:
        prompt = get_system_prompt(taxonomy, question_text, options, marks)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are an expert GATE Computer Science exam analyzer. Output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        content_text = data["choices"][0]["message"]["content"].strip()
        result_dict = json.loads(content_text)
        validated = EnrichmentResult(**result_dict)
        return validated.dict()

def get_llm_provider(provider_name: str = "gemini", model_name: Optional[str] = None) -> LLMProvider:
    provider = provider_name.lower().strip()
    if provider == "gemini":
        model = model_name or os.getenv("LLM_MODEL", "gemini-1.5-pro")
        return GeminiProvider(model)
    elif provider in ("anthropic", "claude"):
        model = model_name or os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
        return AnthropicProvider(model)
    elif provider in ("openai", "gpt"):
        model = model_name or os.getenv("LLM_MODEL", "gpt-4o")
        return OpenAIProvider(model)
    else:
        raise NotImplementedError(f"Provider '{provider_name}' is not supported. Choose from 'gemini', 'anthropic', or 'openai'.")

class TaxonomyValidator:
    def __init__(self, taxonomy: Dict[str, Any]):
        self.taxonomy = taxonomy
        
    def validate(self, result: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate if the subject and topic exist in the taxonomy."""
        subject = result.get('subject')
        topic = result.get('topic')
        subtopic = result.get('subtopic')
        
        if not subject or subject not in self.taxonomy:
            return False, f"Invalid subject: {subject}"
            
        topics_dict = self.taxonomy[subject]
        if not topic or topic not in topics_dict:
            return False, f"Invalid topic '{topic}' for subject '{subject}'"
            
        allowed_subtopics = topics_dict[topic]
        if subtopic and subtopic not in allowed_subtopics:
            return False, f"Invalid subtopic '{subtopic}' for topic '{topic}'"
            
        return True, None
