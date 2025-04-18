# app/advanced_main.py
import streamlit as st
import logging
import asyncio
import time
import httpx
from typing import List, Dict, Any, Optional, Union
import json
import threading
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- API Configuration ---
# Base URLs for the MCP servers
PRIMARY_MCP_SERVER_URL = "http://localhost:8889"  # Advanced MCP server
FALLBACK_MCP_SERVER_URL = "http://localhost:8888"  # Original MCP server

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

# --- MCP Client Implementation ---
class MCPClient:
    """Client for interacting with MCP servers."""

    def __init__(self, primary_url: str, fallback_url: str):
        self.primary_url = primary_url
        self.fallback_url = fallback_url
        self.model_performance = {}
        self.last_update = 0

    async def get_model_performance(self) -> Dict[str, Any]:
        """Get model performance metrics from the server."""
        # Only update once per minute
        current_time = time.time()
        if current_time - self.last_update < 60:
            return self.model_performance

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.primary_url}/api/model-performance")
                if response.status_code == 200:
                    self.model_performance = response.json()
                    self.last_update = current_time
                    return self.model_performance
        except Exception as e:
            logger.warning(f"Failed to get model performance: {e}")

        return self.model_performance

    async def select_best_model(self, symptoms: str) -> str:
        """Select the best model based on performance metrics."""
        performance = await self.get_model_performance()

        if not performance:
            # If no performance data, use the first model
            return MODELS[0]

        # Calculate a score for each model (lower is better)
        scores = {}
        for model in MODELS:
            if model in performance:
                perf = performance[model]
                # Balance response time and success rate
                scores[model] = perf["avg_time"] / (perf["success_rate"] ** 2)
            else:
                # Default score for models without performance data
                scores[model] = 20.0

        # Return the model with the lowest score
        return min(scores, key=scores.get)

    async def analyze_symptoms(self, symptoms: str, patient_data: Optional[Dict[str, Any]] = None) -> str:
        """Analyze symptoms using the MCP architecture."""
        # Format the symptoms with patient data if available
        formatted_symptoms = symptoms
        if patient_data:
            # Add patient data to the symptoms for more context
            patient_info = ", ".join([f"{k}: {v}" for k, v in patient_data.items()])
            formatted_symptoms = f"{formatted_symptoms}\n\nPatient information: {patient_info}"

        # Select the best model
        model = await self.select_best_model(formatted_symptoms)
        logger.info(f"Selected model: {model}")

        # Try the primary server first
        try:
            result = await self._call_primary_server(formatted_symptoms, model)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Primary server failed: {e}")

        # Fall back to the original server
        try:
            result = await self._call_fallback_server(formatted_symptoms, model)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Fallback server failed: {e}")

        # If all else fails, try direct API calls to both servers
        return await self._try_direct_api_calls(formatted_symptoms)

    async def _call_primary_server(self, symptoms: str, model: str) -> Optional[str]:
        """Call the primary MCP server."""
        try:
            url = f"{self.primary_url}/api/tools/analyze_symptoms"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json={
                        "symptoms": symptoms,
                        "model": model
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("result")
                else:
                    logger.warning(f"Primary server returned status code {response.status_code}")
                    return None
        except Exception as e:
            logger.warning(f"Error calling primary server: {e}")
            return None

    async def _call_fallback_server(self, symptoms: str, model: str) -> Optional[str]:
        """Call the fallback MCP server."""
        try:
            url = f"{self.fallback_url}/api/tools/analyze_symptoms"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json={
                        "symptoms": symptoms,
                        "model": model
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("result")
                else:
                    logger.warning(f"Fallback server returned status code {response.status_code}")
                    return None
        except Exception as e:
            logger.warning(f"Error calling fallback server: {e}")
            return None

    async def _try_direct_api_calls(self, symptoms: str) -> str:
        """Try direct API calls to both servers in parallel."""
        # Create tasks for both servers
        primary_task = self._call_primary_server(symptoms, MODELS[0])
        fallback_task = self._call_fallback_server(symptoms, MODELS[0])

        # Wait for the first successful result
        tasks = [primary_task, fallback_task]
        done, pending = await asyncio.wait(
            tasks,
            timeout=30.0,
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel any pending tasks
        for task in pending:
            task.cancel()

        # Check if we got any results
        for task in done:
            try:
                result = task.result()
                if result:
                    return result
            except Exception:
                pass

        # If all else fails, return a friendly error message
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

# Initialize the MCP client
mcp_client = MCPClient(PRIMARY_MCP_SERVER_URL, FALLBACK_MCP_SERVER_URL)

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

# Function to update symptom text
def add_symptom(symptom):
    current_text = st.session_state.symptom_text_input
    if current_text and not current_text.endswith(" "):
        current_text += " "
    st.session_state.symptom_text_input = current_text + symptom.lower()

# Initialize processing state
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# Initialize current result
if "current_result" not in st.session_state:
    st.session_state.current_result = None

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

/* Animated progress bar */
@keyframes pulse {
    0% { opacity: 0.6; }
    50% { opacity: 1; }
    100% { opacity: 0.6; }
}
.animated-progress {
    animation: pulse 1.5s infinite;
}

/* Table styling */
.medical-table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
}
.medical-table th {
    background-color: #f1f1f1;
    padding: 0.5rem;
    text-align: left;
    border: 1px solid #ddd;
}
.medical-table td {
    padding: 0.5rem;
    border: 1px solid #ddd;
}
.medical-table tr:nth-child(even) {
    background-color: #f9f9f9;
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

    # Create a grid of symptom buttons with box styling
    common_symptoms = [
        "Headache", "Fever", "Cough", "Fatigue",
        "Nausea", "Dizziness", "Shortness of breath", "Sore throat"
    ]

    # Common symptoms section
    st.markdown("<div style='margin-top: 1rem; margin-bottom: 0.5rem;'>Common symptoms you can mention:</div>", unsafe_allow_html=True)

    # Create a container with border styling
    st.markdown("""
    <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
    """, unsafe_allow_html=True)

    # Create two rows of buttons
    row1 = common_symptoms[:4]
    row2 = common_symptoms[4:]

    # First row - use Streamlit's native buttons
    cols1 = st.columns(4)
    for i, symptom in enumerate(row1):
        with cols1[i]:
            if st.button(symptom, key=f"symptom_{i}", use_container_width=True, on_click=add_symptom, args=(symptom,)):
                pass

    # Second row - use Streamlit's native buttons
    cols2 = st.columns(4)
    for i, symptom in enumerate(row2):
        with cols2[i]:
            if st.button(symptom, key=f"symptom_{i+4}", use_container_width=True, on_click=add_symptom, args=(symptom,)):
                pass

    # Close the container
    st.markdown("""
    </div>
    """, unsafe_allow_html=True)

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
    check_button = st.button("Check Symptoms", type="primary", use_container_width=True, disabled=st.session_state.is_processing)

    # Display processing indicator
    if st.session_state.is_processing:
        st.markdown("""
        <div style="margin-top: 1rem; text-align: center;" class="animated-progress">
            <div style="color: var(--primary-color); font-weight: 500; margin-bottom: 0.5rem;">
                Analyzing your symptoms...
            </div>
            <div style="color: #666; font-size: 0.9rem;">
                This usually takes 5-30 seconds
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Display results if available
    if "current_result" in st.session_state and st.session_state.current_result:
        st.markdown("""
        <div style="margin-top: 2rem; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #00BFA6; color: white; padding: 0.75rem 1rem; font-weight: 500;">
                Analysis Results
            </div>
            <div style="padding: 1rem;">
        """, unsafe_allow_html=True)

        st.markdown(st.session_state.current_result, unsafe_allow_html=True)

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
    """Process the symptom check using the MCP architecture."""
    try:
        # Set processing flag
        st.session_state.is_processing = True

        # Store the symptom input and duration in session state
        if duration != "Select duration":
            st.session_state.patient_data["Duration"] = duration

        # Call the MCP client to analyze the symptoms
        result = await mcp_client.analyze_symptoms(symptom_input, st.session_state.patient_data)

        # Store the result in session state
        st.session_state.current_result = result

        # Extract follow-up questions if present
        # This is a simple heuristic - in a real app, you'd parse the response more carefully
        if "follow-up question" in result.lower() or "additional information" in result.lower():
            st.session_state.awaiting_follow_up = True
            # Extract questions (simplified approach)
            lines = result.split("\n")
            questions = []
            for line in lines:
                if "?" in line and len(line) < 100:  # Simple heuristic for questions
                    questions.append(line.strip())
            if questions:
                st.session_state.follow_up_questions = questions

        return result
    except Exception as e:
        logger.error(f"Error in process_symptom_check: {e}", exc_info=True)
        return f"An error occurred while analyzing your symptoms: {str(e)}"
    finally:
        # Clear processing flag
        st.session_state.is_processing = False

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
