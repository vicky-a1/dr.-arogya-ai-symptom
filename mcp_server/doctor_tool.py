import os
import sys
from pydantic import BaseModel, Field
from typing import Optional, List
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get OpenRouter API key from environment variables
ROUTER_API_KEY = os.getenv("ROUTER_API_KEY")

# Set up OpenRouter configuration
if not ROUTER_API_KEY:
    logger.error("ROUTER_API_KEY environment variable not set. The application will not function correctly.")
    logger.error("Please add your OpenRouter API key to the .env file and restart the application.")
    API_KEY = "sk-placeholder"  # This will cause an error if used
    BASE_URL = "https://openrouter.ai/api/v1"
    CURRENT_MODEL = "qwen/qwen2.5-vl-32b-instruct:free"  # Default model, won't be used without API key
else:
    logger.info("Using OpenRouter API")
    API_KEY = ROUTER_API_KEY
    BASE_URL = "https://openrouter.ai/api/v1"

    # List of models to try (in order of preference)
    MODELS_TO_TRY = [
        # Smaller, faster models first for quicker response
        "mistralai/mistral-7b-instruct:free",  # Very reliable, fast model
        "qwen/qwen1.5-7b-chat:free",  # Fast and reliable
        "anthropic/claude-3-haiku-20240307:free",  # Fast Claude model
        "google/gemma-7b-it:free",  # Fast Google model

        # Medium-sized models with good balance of speed and quality
        "mistralai/mistral-small-3.1-24b-instruct:free",
        "deepseek/deepseek-chat-v3-0324:free",
        "qwen/qwen2.5-vl-32b-instruct:free",
        "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",

        # Larger models as fallbacks
        "qwen/qwen2.5-vl-72b-instruct:free",
        "deepseek/deepseek-r1-distill-qwen-32b:free",
        "qwen/qwq-32b-preview:free"
    ]

    # Start with the first model
    CURRENT_MODEL = MODELS_TO_TRY[0]
    logger.info(f"Selected model: {CURRENT_MODEL}")

# --- Pydantic Models ---
class Symptom(BaseModel):
    """Model for medical symptoms."""
    description: str = Field(..., description="Description of the symptoms or medical condition.")

class MedicalAdvice(BaseModel):
    """Model for medical advice."""
    diagnosis: str = Field(..., description="Potential diagnosis based on symptoms.")
    recommendations: List[str] = Field(..., description="Medical recommendations and advice.")
    severity: str = Field(..., description="Severity level of the condition (Low, Medium, High).")
    follow_up: str = Field(..., description="Follow-up recommendations.")

# --- LLM Configuration ---
from openai import OpenAI

# Initialize a single OpenAI client with the appropriate configuration
try:
    # Set up headers for OpenRouter if using it
    headers = {}
    if ROUTER_API_KEY:
        headers = {
            "HTTP-Referer": "https://github.com/pydantic/pydantic-ai",  # For attribution
            "X-Title": "AI Doctor MCP Application",  # For attribution
            "User-Agent": "AI-Doctor-MCP/1.0.0",  # Identify your application
            "Content-Type": "application/json"
        }

    # Create the client
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        default_headers=headers,
        timeout=60.0  # Increase timeout for more complex medical queries
    )
    logger.info(f"OpenAI client initialized successfully with base URL: {BASE_URL}")
    logger.info(f"Using model: {CURRENT_MODEL}")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")
    client = None

# --- MCP Tool Definition ---
async def analyze_symptoms(symptoms: str, model: Optional[str] = None) -> str:
    """Analyzes medical symptoms and provides professional medical advice.

    Args:
        symptoms: The symptoms to analyze
        model: Optional specific model to use (must be in MODELS_TO_TRY)
    """
    # Declare global variables at the beginning of the function
    global CURRENT_MODEL

    logger.info(f"MCP Tool: Received request for symptoms: '{symptoms}'")
    if model:
        logger.info(f"Requested specific model: {model}")

    # Check if we have a working client
    if client is None:
        return "Error: LLM client is not configured properly. Cannot provide medical analysis."

    try:
        # Create a detailed medical prompt with expert knowledge
        # Tailor the prompt based on the model being used
        if "claude" in CURRENT_MODEL.lower():
            # Claude-specific prompt (more detailed instructions work well with Claude)
            prompt = f"""
            As a virtual family doctor with extensive medical training, I need you to analyze the following symptoms and provide a comprehensive medical assessment.

            PATIENT SYMPTOMS: {symptoms}

            Please structure your response with the following sections:

            ## Potential Diagnosis
            - List 3-5 possible conditions that could explain these symptoms
            - For each condition, indicate the likelihood (Highly Likely, Moderately Likely, or Possible)
            - Briefly explain why each condition matches the symptoms

            ## Recommendations
            - Suggest specific over-the-counter medications with dosage guidelines if appropriate
            - Recommend evidence-based home remedies that might alleviate symptoms
            - Advise on lifestyle modifications or preventive measures

            ## Severity Assessment
            - Clearly state whether this is a LOW, MEDIUM, or HIGH severity condition
            - Provide clinical reasoning for this assessment
            - List any red flags or warning signs that would increase the severity

            ## Follow-up Recommendations
            - Provide specific timeframes for when the patient should see a healthcare provider
            - Suggest relevant diagnostic tests or examinations
            - Indicate what type of healthcare provider would be most appropriate (GP, specialist, emergency care)

            Format your response in clear, professional markdown with appropriate headings and bullet points.

            IMPORTANT: Conclude with a prominent disclaimer that this information is for educational purposes only and does not replace professional medical advice, diagnosis, or treatment.
            """

            # Claude-specific system prompt
            system_prompt = """You are Claude, a highly knowledgeable medical assistant with expertise in general medicine, diagnostics, and patient care. Your role is to provide accurate, evidence-based medical information while maintaining a compassionate and professional tone.

            Guidelines:
            1. Provide thorough analysis based on current medical knowledge
            2. Use clear, accessible language while maintaining medical accuracy
            3. Be comprehensive but prioritize the most relevant information
            4. Format responses with markdown for optimal readability
            5. Always emphasize the importance of seeking professional medical care
            6. Never claim to diagnose conditions definitively
            7. Acknowledge limitations of remote assessment

            Remember that your advice should complement, not replace, professional healthcare services."""
        else:
            # Generic prompt for other models
            prompt = f"""
            As a virtual family doctor, your role is to provide helpful medical advice based on the symptoms described.

            SYMPTOMS: {symptoms}

            Please provide a comprehensive response that includes:

            ## Potential Diagnosis
            - List possible conditions based on the symptoms
            - Note the likelihood of each condition

            ## Recommendations
            - Suggest over-the-counter medications if appropriate
            - Recommend home remedies that might help
            - Advise on lifestyle changes if relevant

            ## Severity Assessment
            - Indicate whether this is a LOW, MEDIUM, or HIGH severity condition
            - Explain the reasoning for this assessment

            ## Follow-up Recommendations
            - Advise when the patient should see a doctor in person
            - Suggest any tests or examinations that might be needed
            - Provide timeframes for seeking further care

            Format your response in a clear, professional manner using markdown formatting.

            IMPORTANT: End your response with a disclaimer that this is not a substitute for professional medical advice.
            """

            # Generic system prompt for other models
            system_prompt = """You are a professional medical assistant with extensive knowledge of general medicine.
            Provide accurate, helpful, and compassionate medical advice based on the symptoms described.
            Always be thorough in your analysis but avoid unnecessary medical jargon.
            Format your responses using markdown for better readability.
            Remember that your advice should never replace a consultation with a healthcare professional."""

        # If a specific model was requested, try that first
        models_to_try = MODELS_TO_TRY.copy()
        if model and model in MODELS_TO_TRY:
            # Move the requested model to the front of the list
            models_to_try.remove(model)
            models_to_try.insert(0, model)
            logger.info(f"Prioritizing requested model: {model}")

        # Try each model in sequence until one works
        for i, current_model in enumerate(models_to_try):
            try:
                logger.info(f"Trying model {i+1}/{len(models_to_try)}: {current_model}")

                # Set timeout based on model size and type
                if "7b" in current_model.lower() or "haiku" in current_model.lower():
                    # Smaller models can use shorter timeouts
                    timeout = 15.0  # 15 seconds for small models
                    max_tokens = 1000  # Fewer tokens for faster response
                elif "32b" in current_model.lower() or "24b" in current_model.lower():
                    # Medium models need moderate timeout
                    timeout = 25.0  # 25 seconds for medium models
                    max_tokens = 1200
                else:
                    # Larger models need more time
                    timeout = 30.0  # 30 seconds for large models
                    max_tokens = 1500

                # Adjust parameters based on model type
                temperature = 0.3  # Default temperature
                if "claude" in current_model.lower():
                    # Claude models work better with slightly higher temperature
                    temperature = 0.4
                elif "gemma" in current_model.lower() or "mistral" in current_model.lower():
                    # These models work better with lower temperature
                    temperature = 0.2

                # Call the API with optimized parameters
                response = client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )

                # Extract the response
                medical_advice = response.choices[0].message.content

                # Log success with model details
                logger.info(f"SUCCESS: Generated medical advice with model: {current_model}")
                logger.info(f"Response tokens: {len(medical_advice.split())} words")
                logger.debug(f"Medical advice preview: {medical_advice[:100]}...")

                # Update the current model for future reference
                CURRENT_MODEL = current_model

                # Save this successful model as the first one to try next time
                if i > 0:  # If this wasn't already the first model
                    # Swap this model to be first in the list for future calls
                    MODELS_TO_TRY[0], MODELS_TO_TRY[i] = MODELS_TO_TRY[i], MODELS_TO_TRY[0]
                    logger.info(f"Updated model order: {current_model} is now the primary model")

                # Return the successful response
                return medical_advice
            except Exception as model_error:
                error_type = type(model_error).__name__
                logger.warning(f"Error with model {current_model} ({error_type}): {model_error}")

                # Check if we've tried all models
                if i == len(models_to_try) - 1:
                    # This was the last model to try, so raise the error
                    error_msg = f"All models failed. Last error with {current_model}: {model_error}"
                    logger.error(error_msg)

                    # Return a more user-friendly error message instead of raising an exception
                    return """## Medical Analysis Temporarily Unavailable

I apologize, but I'm currently unable to analyze your symptoms. This could be due to:

- High system load
- Temporary service disruption
- Connection issues

### What you can do:

1. **Try again in a few minutes**
2. **Refresh the page**
3. **Check your internet connection**

If you're experiencing severe or concerning symptoms, please contact a healthcare professional directly."""

                # Log that we're trying the next model
                logger.info(f"Falling back to next model...")
                continue

        # This should never be reached due to the exception in the loop above
        return "Error: No models were able to process your request."
    except Exception as e:
        error_message = f"Error analyzing symptoms: {e}"
        logger.error(error_message, exc_info=True)

        # Return a user-friendly error message
        return """## Medical Analysis Temporarily Unavailable

I apologize, but I'm currently unable to analyze your symptoms. This could be due to:

- High system load
- Temporary service disruption
- Connection issues

### What you can do:

1. **Try again in a few minutes**
2. **Refresh the page**
3. **Check your internet connection**

If you're experiencing severe or concerning symptoms, please contact a healthcare professional directly."""
