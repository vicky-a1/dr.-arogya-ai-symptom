# app/simplified_main.py
import streamlit as st
import logging
import asyncio
import time
import httpx
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- API Configuration ---
# Base URL for the MCP SSE server
MCP_SERVER_URL = "http://localhost:8888"

# List of available models to try in order of preference
MODELS = [
    # Smaller, faster models first for quicker response
    "mistralai/mistral-7b-instruct:free",  # Very reliable, fast model
    "qwen/qwen1.5-7b-chat:free",  # Fast and reliable
    "anthropic/claude-3-haiku-20240307:free",  # Fast Claude model
    "google/gemma-7b-it:free",  # Fast Google model

    # Medium-sized models with good balance of speed and quality
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "deepseek/deepseek-chat-v3-0324:free",
    "qwen/qwen2.5-vl-32b-instruct:free",
    "cognitivecomputations/dolphin3.0-r1-mistral-24b:free"
]

# --- Direct API Call Function ---
async def analyze_symptoms_direct(symptoms: str, patient_data=None) -> str:
    """Call the doctor tool directly via API with optimized performance."""

    # Format the symptoms with patient data if available
    formatted_symptoms = symptoms
    if patient_data:
        # Add patient data to the symptoms for more context
        patient_info = ", ".join([f"{k}: {v}" for k, v in patient_data.items()])
        formatted_symptoms = f"{formatted_symptoms}\n\nPatient information: {patient_info}"

    # Set base timeout for API calls
    base_timeout = 20.0  # Base timeout value

    # Try smaller models first for faster response
    fast_models = MODELS[:4]  # First 4 models are smaller/faster
    medium_models = MODELS[4:]  # Remaining models are medium-sized

    # First try the fast models with shorter timeout
    for model in fast_models:
        try:
            # Adjust timeout based on model size
            if "7b" in model.lower() or "haiku" in model.lower():
                timeout = 15.0  # Shorter timeout for small models
            else:
                timeout = base_timeout

            logger.info(f"Trying fast model: {model} with {timeout}s timeout")

            # Prepare the API request
            url = f"{MCP_SERVER_URL}/api/tools/analyze_symptoms"

            # Create an async HTTP client with appropriate timeout
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Make the API call with the specific model
                response = await client.post(
                    url,
                    json={
                        "symptoms": formatted_symptoms,
                        "model": model  # Specify the model to use
                    }
                )

                # Check if the request was successful
                if response.status_code == 200:
                    # Parse the response
                    result = response.json()
                    logger.info(f"Successfully got response from model: {model}")
                    return result.get("result", "No result returned from the API.")
                else:
                    logger.warning(f"Model {model} failed with status code {response.status_code}")
                    continue  # Try the next model

        except httpx.TimeoutException:
            logger.warning(f"Timeout with model {model}, trying next model")
            continue  # Try the next model
        except Exception as e:
            logger.warning(f"Error with model {model}: {e}")
            continue  # Try the next model

    # If fast models failed, try medium models with longer timeout
    for model in medium_models:
        try:
            # Adjust timeout based on model size
            if "32b" in model.lower() or "24b" in model.lower():
                timeout = 25.0  # Medium timeout for medium models
            else:
                timeout = 30.0  # Longer timeout for larger models

            logger.info(f"Trying medium model: {model} with {timeout}s timeout")

            # Prepare the API request
            url = f"{MCP_SERVER_URL}/api/tools/analyze_symptoms"

            # Create an async HTTP client with appropriate timeout
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Make the API call with the specific model
                response = await client.post(
                    url,
                    json={
                        "symptoms": formatted_symptoms,
                        "model": model  # Specify the model to use
                    }
                )

                # Check if the request was successful
                if response.status_code == 200:
                    # Parse the response
                    result = response.json()
                    logger.info(f"Successfully got response from model: {model}")
                    return result.get("result", "No result returned from the API.")
                else:
                    logger.warning(f"Model {model} failed with status code {response.status_code}")
                    continue  # Try the next model

        except httpx.TimeoutException:
            logger.warning(f"Timeout with model {model}, trying next model")
            continue  # Try the next model
        except Exception as e:
            logger.warning(f"Error with model {model}: {e}")
            continue  # Try the next model

    # If all models failed, try a direct call to the doctor tool without specifying a model
    try:
        logger.info("Trying default model as fallback")
        url = f"{MCP_SERVER_URL}/api/tools/analyze_symptoms"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={"symptoms": formatted_symptoms}
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("result", "No result returned from the API.")
            else:
                error_message = f"API request failed with all models. Status code {response.status_code}: {response.text}"
                logger.error(error_message)
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
    except Exception as e:
        logger.error(f"Error in fallback analyze_symptoms call: {e}", exc_info=True)
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

# --- Streamlit UI ---
st.set_page_config(
    page_title="Dr. Arogya AI+ Your Personal Medical Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your medical assistant. Please describe your symptoms in detail, and I'll provide personalized health insights."}
    ]

# Initialize patient data if not already present
if "patient_data" not in st.session_state:
    st.session_state.patient_data = {}

# Initialize follow-up mode
if "awaiting_follow_up" not in st.session_state:
    st.session_state.awaiting_follow_up = False

# Initialize follow-up questions
if "follow_up_questions" not in st.session_state:
    st.session_state.follow_up_questions = []

# Initialize symptom text input
if "symptom_text_input" not in st.session_state:
    st.session_state.symptom_text_input = ""

# Custom CSS for styling based on the provided image
st.markdown("""
<style>
:root {
    --primary-color: #00BFA6;
    --text-color: #333333;
    --light-gray: #f8f9fa;
    --border-radius: 8px;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: var(--text-color);
}

.main-header {
    font-size: 2rem;
    color: var(--primary-color);
    text-align: center;
    margin-bottom: 0.5rem;
    font-weight: 600;
    line-height: 1.2;
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
}

.sub-header {
    font-size: 0.9rem;
    color: #666;
    text-align: center;
    margin-bottom: 1.5rem;
}

.disclaimer {
    background-color: var(--light-gray);
    padding: 1rem;
    border-radius: var(--border-radius);
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
}

.disclaimer-icon {
    color: #FF5722;
    font-size: 1.5rem;
    margin-right: 0.5rem;
}

.disclaimer-text {
    font-size: 0.9rem;
    color: var(--text-color);
}

.input-button {
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: var(--border-radius);
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
    cursor: pointer;
    margin-right: 0.5rem;
    display: inline-flex;
    align-items: center;
}

.input-button-inactive {
    background-color: #f1f1f1;
    color: var(--text-color);
    border: none;
    border-radius: var(--border-radius);
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
}

.input-icon {
    margin-right: 0.5rem;
}

.symptom-button {
    background-color: #E0F7F4;
    color: var(--text-color);
    border: none;
    border-radius: var(--border-radius);
    padding: 0.5rem 1rem;
    margin: 0.25rem;
    font-size: 0.9rem;
    cursor: pointer;
}

.check-button {
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: var(--border-radius);
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    cursor: pointer;
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    margin-top: 1rem;
}

.info-card {
    border: 1px solid #e0e0e0;
    border-radius: var(--border-radius);
    padding: 1rem;
    margin-bottom: 1rem;
}

.info-card-header {
    color: var(--primary-color);
    font-size: 1.1rem;
    font-weight: 500;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
}

.info-card-icon {
    margin-right: 0.5rem;
}

.info-card-content {
    font-size: 0.9rem;
}

/* Hide Streamlit elements */
.stDeployButton, footer, header {
    display: none !important;
}

/* Override Streamlit's default styling */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-color: #e0e0e0;
    border-radius: var(--border-radius);
}

.stSelectbox > div > div > div {
    border-color: #e0e0e0;
    border-radius: var(--border-radius);
}

/* Remove extra padding */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 0 !important;
    max-width: 1000px;
}

/* Custom border for the top of the page */
.top-border {
    border-top: 3px solid var(--primary-color);
    padding-top: 1rem;
    margin-top: -1rem;
}
</style>

<div class="main-header">Dr. Arogya AI+ Your Personal Medical Assistant</div>
<div class="sub-header">Expert medical consultation at your fingertips</div>

<div class="disclaimer">
    <div class="disclaimer-icon">⚠️</div>
    <div class="disclaimer-text">
        <strong>Important Health Notice:</strong> This tool provides informational suggestions only, not medical diagnosis. For serious or persistent symptoms, please consult a healthcare professional.
    </div>
</div>
""", unsafe_allow_html=True)

# Create a two-column layout for the main content
col1, col2 = st.columns([2, 1])

with col1:
    # Symptom input area
    st.markdown("<div style='margin-bottom: 0.5rem;'>Describe your symptoms</div>", unsafe_allow_html=True)
    symptom_input = st.text_area(
        "",
        value=st.session_state.symptom_text_input,
        placeholder="",
        height=150,
        key="symptom_text_input",
        label_visibility="collapsed"
    )

    # Common symptoms section
    st.markdown("<div style='margin-top: 1rem; margin-bottom: 0.5rem;'>Common symptoms you can mention:</div>", unsafe_allow_html=True)

    # Create a grid of symptom buttons
    common_symptoms = [
        "Headache", "Fever", "Cough", "Fatigue",
        "Nausea", "Dizziness", "Shortness of breath", "Sore throat"
    ]

    # Display symptom buttons in a grid
    cols = st.columns(4)
    for i, symptom in enumerate(common_symptoms):
        with cols[i % 4]:
            if st.button(symptom, key=f"symptom_{i}", use_container_width=True):
                # Add the symptom to the text area
                current_text = st.session_state.symptom_text_input
                if current_text and not current_text.endswith(" "):
                    current_text += " "
                st.session_state.symptom_text_input = current_text + symptom.lower()
                st.rerun()

    # Duration selector
    st.markdown("<div style='margin-top: 1rem; margin-bottom: 0.5rem;'>How long have you been experiencing these symptoms?</div>", unsafe_allow_html=True)
    duration = st.selectbox(
        "",
        ["Select duration", "Less than 24 hours", "1-3 days", "4-7 days", "1-2 weeks", "More than 2 weeks"],
        index=0,
        label_visibility="collapsed"
    )

    # Input buttons
    st.markdown("""
    <div style="margin-top: 1.5rem; margin-bottom: 1rem;">
        <button class="input-button">
            <span class="input-icon">✏️</span> Text Input
        </button>
        <button class="input-button-inactive">
            <span class="input-icon">🎤</span> Voice Input
        </button>
    </div>
    """, unsafe_allow_html=True)

    # Check Symptoms button
    check_button = st.button("Check Symptoms", type="primary", use_container_width=True)

    # Display results if available
    if "current_result" in st.session_state and st.session_state.current_result:
        st.markdown("""
        <div style="margin-top: 2rem; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #00BFA6; color: white; padding: 0.75rem 1rem; font-weight: 500;">
                Analysis Results
            </div>
            <div style="padding: 1rem;">
        """, unsafe_allow_html=True)

        st.markdown(st.session_state.current_result, unsafe_allow_html=False)

        st.markdown("</div></div>", unsafe_allow_html=True)

        # Display follow-up questions if awaiting answers
        if st.session_state.awaiting_follow_up and st.session_state.follow_up_questions:
            st.markdown("<div style='margin-top: 1.5rem;'><strong>To provide better health insights, please answer these questions:</strong></div>", unsafe_allow_html=True)
            for i, question in enumerate(st.session_state.follow_up_questions):
                st.markdown(f"<div style='margin-top: 0.5rem;'><strong>{i+1}.</strong> {question}</div>", unsafe_allow_html=True)

with col2:
    # Display patient information if available
    if st.session_state.patient_data:
        st.markdown("""
        <div class="info-card">
            <div class="info-card-header">
                <span class="info-card-icon">📋</span> Your Information
            </div>
        """, unsafe_allow_html=True)

        for key, value in st.session_state.patient_data.items():
            st.markdown(f"<div><strong>{key}:</strong> {value}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Health tips section
    st.markdown("""
    <div class="info-card">
        <div class="info-card-header">
            <span class="info-card-icon">💡</span> Health Tips
        </div>
        <div class="info-card-content">
            <p>🌡️ <strong>Track your symptoms</strong> - Note when they started and any changes</p>
            <p>💧 <strong>Stay hydrated</strong> - Drink plenty of water, especially when ill</p>
            <p>🛌 <strong>Rest properly</strong> - Give your body time to recover</p>
            <p>🩺 <strong>Seek help</strong> - Don't delay contacting a doctor for serious symptoms</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Define an async function to handle the symptom checking process
async def process_symptom_check(symptom_input, duration):
    # Store the symptom input and duration in session state
    if duration != "Select duration":
        st.session_state.patient_data["Duration"] = duration

    # Show a spinner while processing
    with st.spinner("Analyzing your symptoms..."):
        # Show a progress bar with optimized steps
        progress_bar = st.progress(0)

        # Start processing the medical query with patient data
        processing_task = analyze_symptoms_direct(symptom_input, st.session_state.patient_data)

        # Show progress while waiting for the response - optimized for faster models
        progress_steps = [
            (0, 40, 0.005),  # Very quick initial progress (0.5ms per step)
            (40, 70, 0.01),  # Medium speed middle progress (10ms per step)
            (70, 90, 0.005)  # Quick progress towards end (5ms per step)
        ]

        # Update progress bar while processing in background
        task_complete = False
        result = None
        current_progress = 0  # Track current progress

        # Create a task to run the API call
        task = asyncio.create_task(processing_task)

        # Update progress while waiting
        for start, end, delay in progress_steps:
            for i in range(start, end):
                # Check if we already have a result
                if task.done():
                    task_complete = True
                    break

                # Update progress bar
                progress_bar.progress(i)
                current_progress = i  # Update current progress
                await asyncio.sleep(delay)  # Non-blocking sleep

            if task_complete:
                break

        # If task is still not done, wait at 90%
        if not task_complete:
            progress_bar.progress(90)
            # Wait for the result
            result = await task
        else:
            # Get the result that completed during animation
            result = task.result()

        # Complete the progress bar with a quick animation
        for i in range(max(current_progress, 90), 101):
            progress_bar.progress(i)
            await asyncio.sleep(0.01)  # Very brief pause between steps

        # Store the result in session state
        st.session_state.current_result = result

        # Remove the progress bar when done
        progress_bar.empty()

        return result

# Process the check button click
if check_button:
    if symptom_input.strip():
        # Run the async function using asyncio.run
        asyncio.run(process_symptom_check(symptom_input, duration))
        # Rerun to display the results
        st.rerun()
    else:
        st.error("Please describe your symptoms before checking.")

# Add a simple footer
st.markdown("""
<div style="text-align: center; margin-top: 3rem; color: #888; font-size: 0.8rem;">
    © 2025 Dr. Arogya AI+ Your Personal Medical Assistant | For informational purposes only
</div>
""", unsafe_allow_html=True)
