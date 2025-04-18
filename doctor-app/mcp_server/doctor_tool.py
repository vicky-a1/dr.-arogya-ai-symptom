import os
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
    logger.error("ROUTER_API_KEY environment variable not set. Using fallback responses.")
    logger.error("Please add your OpenRouter API key to the .env file and restart the application.")
    API_KEY = "sk-placeholder"  # This will cause an error if used
    BASE_URL = "https://openrouter.ai/api/v1"
    CURRENT_MODEL = "qwen/qwen2.5-vl-32b-instruct:free"  # Default model, won't be used without API key
    USE_FALLBACK = True
else:
    logger.info("Using OpenRouter API")
    API_KEY = ROUTER_API_KEY
    BASE_URL = "https://openrouter.ai/api/v1"
    USE_FALLBACK = False  # Will be set to True if API calls fail

    # List of models to try (in order of preference, optimized for faster response)
    MODELS_TO_TRY = [
        # Models specified by the user, reordered for faster response
        "qwen/qwen2.5-vl-32b-instruct:free",  # Fast and good quality
        "mistralai/mistral-small-3.1-24b-instruct:free",  # Good general model
        "deepseek/deepseek-chat-v3-0324:free",  # Good for medical
        "deepseek/deepseek-r1-distill-qwen-32b:free",  # Good distilled model
        "cognitivecomputations/dolphin3.0-r1-mistral-24b:free",  # Good for detailed responses
        "qwen/qwq-32b-preview:free",  # Alternative Qwen model
        "qwen/qwen2.5-vl-72b-instruct:free"  # Larger model, better quality but slower
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

# We'll use requests library directly for OpenRouter API
import requests
import json

# Initialize configuration
# Set up headers for OpenRouter
headers = {}
if ROUTER_API_KEY:
    headers = {
        "Authorization": f"Bearer {ROUTER_API_KEY}",  # Add proper authorization header
        "HTTP-Referer": "https://github.com/pydantic/pydantic-ai",  # For attribution
        "X-Title": "AI Doctor MCP Application",  # For attribution
        "Content-Type": "application/json"
    }

    # Log the API key format (masked for security)
    masked_key = ROUTER_API_KEY[:4] + "*" * (len(ROUTER_API_KEY) - 8) + ROUTER_API_KEY[-4:]
    logger.info(f"API Key format: {masked_key}")

# Function to get fallback response based on symptoms
def get_fallback_response(symptoms: str) -> str:
    symptoms_lower = symptoms.lower()

    # Check for headache symptoms
    if any(term in symptoms_lower for term in ["headache", "migraine", "head pain", "head ache"]):
        logger.info("Using fallback response for headache")
        return """## Potential Diagnosis
- **Tension headache** (High likelihood): The most common type of headache, characterized by mild to moderate pain that feels like a band around the head.
- **Migraine** (Moderate likelihood): Characterized by throbbing pain, often on one side of the head, sometimes accompanied by nausea, vomiting, or sensitivity to light and sound.
- **Dehydration headache** (Moderate likelihood): Caused by insufficient fluid intake.
- **Sinus headache** (Low likelihood): Pain concentrated in the sinus areas, often with nasal congestion.
- **Cluster headache** (Low likelihood): Severe pain around one eye or one side of the head.

## Recommendations
- **Over-the-counter medications**:
  - Acetaminophen (Tylenol) for pain relief
  - Ibuprofen (Advil, Motrin) or Aspirin for pain and inflammation
  - Combination medications specifically for headaches (like Excedrin)

- **Home remedies**:
  - Apply a cold or warm compress to your head or neck
  - Rest in a quiet, dark room
  - Stay hydrated by drinking plenty of water
  - Practice relaxation techniques such as deep breathing or meditation
  - Gentle massage of the temples or neck

- **Lifestyle changes**:
  - Maintain regular sleep patterns
  - Stay hydrated throughout the day
  - Manage stress through regular exercise and relaxation techniques
  - Limit screen time and take regular breaks
  - Maintain good posture to reduce neck and shoulder tension

## Severity Assessment
**LOW to MEDIUM severity condition**

Most headaches are not dangerous and can be managed with self-care. However, the severity depends on:
- Frequency and duration of headaches
- Impact on daily activities
- Associated symptoms

The assessment is LOW if this is an occasional headache with typical symptoms, and MEDIUM if headaches are frequent or interfere with daily activities.

## Follow-up Recommendations
- **See a doctor if**:
  - Headache is sudden and severe ("worst headache of your life")
  - Headache is accompanied by fever, stiff neck, confusion, seizures, double vision, weakness, numbness, or difficulty speaking
  - Headache worsens despite over-the-counter pain medication
  - Headaches wake you from sleep
  - You have a history of headaches but the pattern has changed
  - Headaches started after a head injury

- **Tests that might be needed**:
  - Physical examination
  - Neurological examination
  - In persistent cases: CT scan or MRI (rarely needed for typical headaches)

- **Timeframes**:
  - For typical headaches: Self-care for 1-2 days
  - If no improvement after 3 days of self-treatment: Consult a healthcare provider
  - For severe or unusual symptoms as described above: Seek immediate medical attention

*Disclaimer: This information is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.*"""

    # Check for fever symptoms
    elif any(term in symptoms_lower for term in ["fever", "temperature", "hot", "chills", "sweating"]):
        logger.info("Using fallback response for fever")
        return """## Potential Diagnosis
- **Viral infection** (High likelihood): Common cold, flu, or other viral illnesses often cause fever.
- **Bacterial infection** (Moderate likelihood): Such as strep throat, urinary tract infection, or bacterial pneumonia.
- **COVID-19** (Moderate likelihood): Fever is a common symptom of COVID-19 infection.
- **Inflammatory conditions** (Low likelihood): Various inflammatory conditions can cause fever.
- **Medication reaction** (Low likelihood): Some medications can cause fever as a side effect.

## Recommendations
- **Over-the-counter medications**:
  - Acetaminophen (Tylenol) to reduce fever
  - Ibuprofen (Advil, Motrin) or Aspirin for fever and inflammation
  - Note: Follow dosage instructions carefully and consult a pharmacist if unsure

- **Home remedies**:
  - Stay hydrated by drinking plenty of fluids
  - Rest and get adequate sleep
  - Use a light blanket if you have chills
  - Take a lukewarm bath or apply cool compresses if the fever is high
  - Wear lightweight clothing and keep room temperature comfortable

- **Lifestyle changes**:
  - Temporarily reduce physical activity while recovering
  - Eat light, easily digestible foods
  - Avoid alcohol and caffeine
  - Practice good hand hygiene to prevent spreading infection

## Severity Assessment
**LOW to MEDIUM severity condition**

The severity of fever depends on:
- Temperature level (low-grade: 99-100.9°F/37.2-38.3°C, moderate: 101-103°F/38.4-39.4°C, high: >103°F/39.5°C)
- Duration of fever
- Associated symptoms
- Age and overall health

A typical fever in an otherwise healthy adult is usually LOW severity if below 102°F (38.9°C) and MEDIUM if higher or persistent.

## Follow-up Recommendations
- **See a doctor if**:
  - Fever is above 103°F (39.4°C)
  - Fever persists for more than 3 days
  - Fever is accompanied by severe headache, stiff neck, confusion, difficulty breathing, rash, or persistent vomiting
  - You have underlying health conditions or a weakened immune system
  - You've recently traveled to an area with endemic infectious diseases
  - You have severe pain anywhere in the body

- **Tests that might be needed**:
  - Physical examination
  - Blood tests to check for infection or inflammation
  - Specific tests for suspected infections (strep test, COVID-19 test, etc.)
  - Urine tests if urinary symptoms are present
  - Chest X-ray if respiratory symptoms are present

- **Timeframes**:
  - For mild fever (<101°F/38.3°C) with no concerning symptoms: Self-care for 2-3 days
  - If no improvement after 3 days: Consult a healthcare provider
  - For high fever or concerning symptoms as described above: Seek medical attention within 24 hours
  - For very high fever (>104°F/40°C) or severe symptoms: Seek immediate medical attention

*Disclaimer: This information is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.*"""

    # Check for cough symptoms
    elif any(term in symptoms_lower for term in ["cough", "coughing", "throat", "phlegm", "mucus"]):
        logger.info("Using fallback response for cough")
        return """## Potential Diagnosis
- **Common cold** (High likelihood): Viral infection causing upper respiratory symptoms including cough.
- **Bronchitis** (Moderate likelihood): Inflammation of the bronchial tubes, often following a cold or respiratory infection.
- **Allergies** (Moderate likelihood): Environmental allergens can trigger coughing, especially with other symptoms like sneezing or itchy eyes.
- **Asthma** (Low likelihood): Chronic condition with coughing, wheezing, and shortness of breath, often triggered by specific factors.
- **COVID-19** (Low to moderate likelihood): Viral infection with symptoms including cough, fever, and fatigue.

## Recommendations
- **Over-the-counter medications**:
  - Cough suppressants (dextromethorphan) for dry, hacking coughs
  - Expectorants (guaifenesin) to help clear mucus from a productive cough
  - Throat lozenges or sprays for sore throat associated with coughing
  - Antihistamines if allergies are suspected

- **Home remedies**:
  - Stay hydrated with warm liquids like tea with honey and lemon
  - Use a humidifier or take steamy showers to moisten airways
  - Gargle with salt water for sore throat relief
  - Elevate your head while sleeping to reduce nighttime coughing
  - Avoid irritants like smoke, dust, or strong fragrances

- **Lifestyle changes**:
  - Get adequate rest to support immune function
  - Avoid smoking and secondhand smoke
  - Maintain good indoor air quality
  - Practice good hand hygiene to prevent spreading infection

## Severity Assessment
**LOW to MEDIUM severity condition**

The severity depends on:
- Duration and intensity of cough
- Presence of other symptoms (fever, shortness of breath, chest pain)
- Color and amount of phlegm/mucus (if present)
- Impact on daily activities and sleep

Most coughs are LOW severity and resolve with self-care, but can be MEDIUM severity if persistent or accompanied by concerning symptoms.

## Follow-up Recommendations
- **See a doctor if**:
  - Cough persists for more than 3 weeks
  - Cough produces thick, greenish-yellow, or blood-tinged mucus
  - Cough is accompanied by shortness of breath, wheezing, or chest pain
  - You have a high fever (above 101°F/38.3°C) for more than 3 days
  - You have underlying conditions like asthma, COPD, or heart disease
  - Cough significantly disrupts sleep or daily activities

- **Tests that might be needed**:
  - Physical examination with lung assessment
  - Chest X-ray if pneumonia is suspected
  - Pulmonary function tests if asthma is suspected
  - COVID-19 or other respiratory pathogen testing
  - Sputum culture if bacterial infection is suspected

- **Timeframes**:
  - For typical viral cough: Self-care for 1-2 weeks
  - If no improvement after 3 weeks: Consult a healthcare provider
  - For severe symptoms (difficulty breathing, high fever, chest pain): Seek immediate medical attention

*Disclaimer: This information is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.*"""

    # Check for stomach/digestive symptoms
    elif any(term in symptoms_lower for term in ["stomach", "nausea", "vomit", "diarrhea", "constipation", "abdominal", "digestive", "gut"]):
        logger.info("Using fallback response for digestive issues")
        return """## Potential Diagnosis
- **Gastroenteritis** (High likelihood): Commonly known as stomach flu, caused by viral or bacterial infection.
- **Food poisoning** (Moderate likelihood): Caused by consuming contaminated food or beverages.
- **Irritable Bowel Syndrome (IBS)** (Moderate likelihood): A chronic condition affecting the large intestine.
- **Acid reflux/GERD** (Low likelihood): When stomach acid flows back into the esophagus.
- **Medication side effects** (Low likelihood): Many medications can cause digestive symptoms.

## Recommendations
- **Over-the-counter medications**:
  - Antacids (Tums, Rolaids) for heartburn or indigestion
  - Anti-diarrheal medications (Imodium) for diarrhea
  - Anti-nausea medications (Dramamine, Pepto-Bismol)
  - Stool softeners for constipation

- **Home remedies**:
  - Stay hydrated with clear fluids, especially water and electrolyte solutions
  - Follow the BRAT diet (bananas, rice, applesauce, toast) for diarrhea
  - Ginger tea or peppermint tea for nausea
  - Warm compress on the abdomen for cramps
  - Probiotics to restore gut flora

- **Lifestyle changes**:
  - Eat smaller, more frequent meals
  - Avoid trigger foods (spicy, fatty, acidic foods)
  - Limit alcohol and caffeine consumption
  - Manage stress through relaxation techniques
  - Stay upright for 1-2 hours after eating

## Severity Assessment
**LOW to MEDIUM severity condition**

The severity depends on:
- Duration and intensity of symptoms
- Presence of dehydration
- Presence of blood in stool or vomit
- Fever and other systemic symptoms
- Impact on daily activities

Most digestive issues are LOW severity and resolve with self-care, but can be MEDIUM severity if persistent or causing dehydration.

## Follow-up Recommendations
- **See a doctor if**:
  - Symptoms persist for more than 3 days
  - You have signs of dehydration (extreme thirst, dry mouth, little or no urination, severe weakness)
  - You have blood in vomit or stool
  - You have severe abdominal pain
  - You have a fever above 101°F (38.3°C)
  - You have recently traveled internationally
  - You have unexplained weight loss

- **Tests that might be needed**:
  - Physical examination
  - Blood tests to check for infection or inflammation
  - Stool sample analysis
  - Endoscopy or colonoscopy for persistent symptoms
  - Imaging studies (ultrasound, CT scan) for severe or persistent pain

- **Timeframes**:
  - For typical viral gastroenteritis: Self-care for 1-3 days
  - If no improvement after 3 days: Consult a healthcare provider
  - For severe symptoms (intense pain, persistent vomiting, signs of dehydration): Seek medical attention within 24 hours

*Disclaimer: This information is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.*"""

    # Default response for other symptoms
    else:
        logger.info("Using generic fallback response for unrecognized symptoms")
        return """## Medical Analysis

Based on the symptoms you've described, I can provide some general guidance. However, without a valid API connection, I can only offer limited information.

## Recommendations
- Monitor your symptoms and note any changes
- Stay hydrated and get adequate rest
- Consider over-the-counter medications appropriate for your symptoms
- Practice good hygiene to prevent spreading any potential infection

## Severity Assessment
Without more specific analysis, it's difficult to assess the severity of your condition. Please use your best judgment based on:
- How long you've had these symptoms
- Whether they're getting better or worse
- How much they impact your daily activities
- Whether you have any underlying health conditions

## Follow-up Recommendations
- If symptoms persist for more than a few days, consult a healthcare provider
- If symptoms are severe or rapidly worsening, seek medical attention promptly
- Consider a telehealth appointment if you prefer not to visit a medical facility

*Disclaimer: This information is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.*"""

# Function to validate API key
def validate_api_key():
    global USE_FALLBACK
    try:
        # Make a simple request to check if the API key is valid
        test_headers = {
            "Authorization": f"Bearer {ROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        test_response = requests.get(
            f"{BASE_URL}/models",
            headers=test_headers,
            timeout=5.0
        )

        if test_response.status_code == 200:
            logger.info("API key validation successful")
            USE_FALLBACK = False
            return True
        else:
            logger.error(f"API key validation failed: {test_response.status_code} - {test_response.text}")
            USE_FALLBACK = True
            return False
    except Exception as e:
        logger.error(f"API key validation error: {e}")
        USE_FALLBACK = True
        return False

try:
    # For backward compatibility, still create an OpenAI client
    client = OpenAI(
        base_url=BASE_URL,
        api_key=ROUTER_API_KEY,
        timeout=60.0
    )
    logger.info(f"OpenAI client initialized successfully with base URL: {BASE_URL}")
    logger.info(f"Using model: {CURRENT_MODEL}")

    # Validate the API key
    if not USE_FALLBACK:
        is_valid = validate_api_key()
        if not is_valid:
            logger.warning("API key is invalid or expired. Using fallback responses.")
            USE_FALLBACK = True
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")
    client = None
    USE_FALLBACK = True

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

    # Check if we should use fallback responses directly
    if USE_FALLBACK or client is None:
        logger.info("Using fallback responses due to API key issues")
        return get_fallback_response(symptoms)

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
            # Generic prompt for other models - optimized for faster response
            prompt = f"""
            As a virtual family doctor, provide concise medical advice for these symptoms: {symptoms}

            Format your response with these sections:

            ## Potential Diagnosis
            - List 3-4 possible conditions with likelihood (High/Moderate/Low)

            ## Recommendations
            - Key medications, home remedies, and lifestyle changes

            ## Severity Assessment
            - LOW, MEDIUM, or HIGH severity with brief reasoning

            ## Follow-up Recommendations
            - When to see a doctor and what tests might be needed

            Use markdown formatting. End with a brief medical disclaimer.
            """

            # Generic system prompt for other models - optimized for faster response
            system_prompt = """You are a medical assistant with expertise in general medicine. Provide concise, accurate medical advice for the symptoms. Be clear and direct, using simple language. Format with markdown. Include a brief disclaimer that your advice is not a substitute for professional medical care."""

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

                # Set timeout and parameters based on model type using if-else statements
                # Optimized for faster response times
                if current_model == "qwen/qwen2.5-vl-32b-instruct:free":
                    timeout = 15.0  # Reduced from 25.0
                    max_tokens = 800  # Reduced from 1200
                    temperature = 0.4  # Increased from 0.3 for faster generation
                    logger.info(f"Using qwen/qwen2.5-vl-32b-instruct:free with timeout={timeout}s")
                elif current_model == "deepseek/deepseek-chat-v3-0324:free":
                    timeout = 15.0  # Reduced from 25.0
                    max_tokens = 800  # Reduced from 1200
                    temperature = 0.35  # Increased from 0.25 for faster generation
                    logger.info(f"Using deepseek/deepseek-chat-v3-0324:free with timeout={timeout}s")
                elif current_model == "mistralai/mistral-small-3.1-24b-instruct:free":
                    timeout = 15.0  # Reduced from 25.0
                    max_tokens = 800  # Reduced from 1200
                    temperature = 0.3  # Increased from 0.2 for faster generation
                    logger.info(f"Using mistralai/mistral-small-3.1-24b-instruct:free with timeout={timeout}s")
                elif current_model == "cognitivecomputations/dolphin3.0-r1-mistral-24b:free":
                    timeout = 15.0  # Reduced from 25.0
                    max_tokens = 800  # Reduced from 1200
                    temperature = 0.35  # Increased from 0.25 for faster generation
                    logger.info(f"Using cognitivecomputations/dolphin3.0-r1-mistral-24b:free with timeout={timeout}s")
                elif current_model == "qwen/qwen2.5-vl-72b-instruct:free":
                    timeout = 20.0  # Reduced from 30.0
                    max_tokens = 1000  # Reduced from 1500
                    temperature = 0.4  # Increased from 0.3 for faster generation
                    logger.info(f"Using qwen/qwen2.5-vl-72b-instruct:free with timeout={timeout}s")
                elif current_model == "deepseek/deepseek-r1-distill-qwen-32b:free":
                    timeout = 15.0  # Reduced from 25.0
                    max_tokens = 800  # Reduced from 1200
                    temperature = 0.35  # Increased from 0.25 for faster generation
                    logger.info(f"Using deepseek/deepseek-r1-distill-qwen-32b:free with timeout={timeout}s")
                elif current_model == "qwen/qwq-32b-preview:free":
                    timeout = 15.0  # Reduced from 25.0
                    max_tokens = 800  # Reduced from 1200
                    temperature = 0.4  # Increased from 0.3 for faster generation
                    logger.info(f"Using qwen/qwq-32b-preview:free with timeout={timeout}s")
                else:
                    # Default parameters for any other model
                    timeout = 20.0  # Reduced from 30.0
                    max_tokens = 1000  # Reduced from 1500
                    temperature = 0.4  # Increased from 0.3 for faster generation
                    logger.info(f"Using default parameters for {current_model} with timeout={timeout}s")

                # Call the API with optimized parameters using requests directly
                logger.info(f"Calling OpenRouter API with model: {current_model}")

                # Prepare the request payload
                payload = {
                    "model": current_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                # Make the API call using requests
                try:
                    # Create fresh headers for each request
                    request_headers = {
                        "Authorization": f"Bearer {ROUTER_API_KEY}",
                        "HTTP-Referer": "https://github.com/pydantic/pydantic-ai",
                        "X-Title": "AI Doctor MCP Application",
                        "Content-Type": "application/json"
                    }

                    logger.info(f"Sending request to {BASE_URL}/chat/completions")
                    logger.info(f"Headers: {request_headers}")
                    response = requests.post(
                        f"{BASE_URL}/chat/completions",
                        headers=request_headers,
                        json=payload,
                        timeout=timeout
                    )

                    # Check if the request was successful
                    response.raise_for_status()

                    # Parse the response
                    response_data = response.json()
                    logger.info(f"Response status: {response.status_code}")

                    # Extract the medical advice from the response
                    medical_advice = response_data['choices'][0]['message']['content']
                except requests.exceptions.RequestException as req_error:
                    logger.error(f"Request error: {req_error}")
                    if hasattr(req_error, 'response') and req_error.response is not None:
                        logger.error(f"Response status code: {req_error.response.status_code}")
                        logger.error(f"Response content: {req_error.response.text}")
                    raise Exception(f"API request failed: {req_error}")

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

                    # Log detailed error information for debugging
                    logger.error(f"API Key: {'Set' if ROUTER_API_KEY else 'Not Set'}")
                    logger.error(f"Base URL: {BASE_URL}")
                    logger.error(f"Headers: Authorization header present: {'Yes' if ROUTER_API_KEY else 'No'}")

                    # Use the get_fallback_response function instead of hardcoded responses
                    logger.info("All models failed, using fallback response")
                    return get_fallback_response(symptoms)

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
