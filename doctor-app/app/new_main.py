# app/main.py
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

# --- Direct API Call Function ---
async def analyze_symptoms_direct(symptoms: str) -> str:
    """Call the doctor tool directly via API."""
    try:
        # Prepare the API request
        url = f"{MCP_SERVER_URL}/api/tools/analyze_symptoms"

        # Create an async HTTP client
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Make the API call
            response = await client.post(
                url,
                json={"symptoms": symptoms}
            )

            # Check if the request was successful
            if response.status_code == 200:
                # Parse the response
                result = response.json()
                return result.get("result", "No result returned from the API.")
            else:
                error_message = f"API request failed with status code {response.status_code}: {response.text}"
                logger.error(error_message)
                return f"Error: {error_message}"
    except Exception as e:
        logger.error(f"Error in direct analyze_symptoms call: {e}", exc_info=True)
        return f"An error occurred while analyzing your symptoms. Please try again. Error: {str(e)}"

# --- Streamlit UI ---
st.set_page_config(
    page_title="Symptom Checker",
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

# Check if we need to clear all data (from the "Start New Check" button)
if "clear_all_data" in st.session_state and st.session_state.clear_all_data:
    # Clear all session state data
    st.session_state.patient_data = {}
    st.session_state.awaiting_follow_up = False
    st.session_state.follow_up_questions = []
    # We can't directly modify symptom_text_input here, but we'll handle it in the UI
    if "current_result" in st.session_state:
        del st.session_state.current_result
    # Reset the flag
    st.session_state.clear_all_data = False

# Custom CSS for enhanced styling with more compelling and user-friendly design
st.markdown("""
<style>
:root {
    --primary-color: #00BFA6;
    --primary-dark: #008E76;
    --primary-light: #E0F7F4;
    --accent-color: #FF5722;
    --text-color: #333333;
    --text-light: #666666;
    --light-gray: #f8f9fa;
    --white: #ffffff;
    --shadow: rgba(0, 0, 0, 0.05);
    --border-radius: 12px;
    --border-radius-sm: 8px;
    --transition: all 0.3s ease;
    --box-shadow: 0 4px 12px var(--shadow);
}

/* Global styles */
.streamlit-container {
    max-width: 1200px;
    margin: 0 auto;
}

/* Typography */
.main-header {
    font-size: 2.8rem;
    background: linear-gradient(90deg, var(--primary-color), var(--primary-dark));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 0.5rem;
    font-weight: 700;
    letter-spacing: -0.5px;
}

.sub-header {
    font-size: 1.1rem;
    color: var(--text-light);
    text-align: center;
    margin-bottom: 2rem;
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.5;
}

/* Disclaimer */
.disclaimer {
    background-color: var(--light-gray);
    padding: 1.2rem;
    border-radius: var(--border-radius);
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    box-shadow: var(--box-shadow);
    border-left: 4px solid var(--accent-color);
    transition: var(--transition);
}

.disclaimer:hover {
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

.disclaimer-icon {
    color: var(--accent-color);
    font-size: 1.8rem;
    margin-right: 1rem;
}

.disclaimer-text {
    font-size: 0.95rem;
    color: var(--text-color);
    line-height: 1.5;
}

/* Buttons */
.tab-button {
    background-color: var(--light-gray);
    color: var(--text-color);
    border: none;
    border-radius: var(--border-radius-sm);
    padding: 0.7rem 1.2rem;
    font-size: 1rem;
    cursor: pointer;
    transition: var(--transition);
    font-weight: 500;
}

.tab-button.active {
    background-color: var(--primary-color);
    color: var(--white);
}

.tab-button:hover:not(.active) {
    background-color: #e9ecef;
}

.symptom-button {
    background-color: var(--primary-light);
    color: var(--text-color);
    border: none;
    border-radius: var(--border-radius-sm);
    padding: 0.7rem 1rem;
    margin: 0.3rem;
    font-size: 0.95rem;
    cursor: pointer;
    transition: var(--transition);
    box-shadow: 0 2px 4px var(--shadow);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 500;
}

.symptom-button:hover {
    background-color: var(--primary-color);
    color: var(--white);
    transform: translateY(-2px);
    box-shadow: 0 4px 8px var(--shadow);
}

.check-button {
    background: linear-gradient(90deg, var(--primary-color), var(--primary-dark));
    color: white;
    border: none;
    border-radius: var(--border-radius);
    padding: 0.9rem 1.5rem;
    font-size: 1.1rem;
    cursor: pointer;
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    margin-top: 1.5rem;
    transition: var(--transition);
    box-shadow: 0 4px 12px rgba(0, 191, 166, 0.3);
    font-weight: 600;
    letter-spacing: 0.5px;
}

.check-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0, 191, 166, 0.4);
}

.check-button:active {
    transform: translateY(0);
}

.reset-button {
    background-color: #f1f1f1;
    color: var(--text-color);
    border: none;
    border-radius: var(--border-radius-sm);
    padding: 0.6rem 1rem;
    font-size: 0.9rem;
    cursor: pointer;
    transition: var(--transition);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 1rem;
    font-weight: 500;
}

.reset-button:hover {
    background-color: #e0e0e0;
}

/* Input area */
.input-area {
    border: 1px solid #E0E0E0;
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin-bottom: 2rem;
    background-color: var(--white);
    box-shadow: var(--box-shadow);
    transition: var(--transition);
}

.input-area:hover, .input-area:focus-within {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
    border-color: var(--primary-color);
}

.input-placeholder {
    color: #9E9E9E;
    font-style: italic;
}

/* Card styling */
.card {
    background-color: var(--white);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--box-shadow);
    transition: var(--transition);
    border-top: 4px solid var(--primary-color);
}

.card:hover {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.card-title {
    font-size: 1.2rem;
    color: var(--primary-color);
    margin-bottom: 1rem;
    font-weight: 600;
    display: flex;
    align-items: center;
}

.card-title-icon {
    margin-right: 0.5rem;
    font-size: 1.4rem;
}

.card-content {
    color: var(--text-color);
    line-height: 1.6;
}

/* Results section */
.results-container {
    margin-top: 2rem;
    border-radius: var(--border-radius);
    padding: 0;
    overflow: hidden;
    box-shadow: var(--box-shadow);
    transition: var(--transition);
    border: 1px solid #E0E0E0;
}

.results-container:hover {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.results-header {
    font-size: 1.3rem;
    color: var(--white);
    margin-bottom: 0;
    background: linear-gradient(90deg, var(--primary-color), var(--primary-dark));
    padding: 1rem 1.5rem;
    font-weight: 600;
    display: flex;
    align-items: center;
}

.results-header-icon {
    margin-right: 0.7rem;
    font-size: 1.5rem;
}

.results-content {
    padding: 1.5rem;
}

/* Table styling */
table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 1.5rem 0;
    border-radius: var(--border-radius-sm);
    overflow: hidden;
    box-shadow: 0 2px 8px var(--shadow);
}

th {
    background: linear-gradient(90deg, var(--primary-color), var(--primary-dark));
    color: white;
    text-align: left;
    padding: 1rem;
    font-weight: 600;
    font-size: 1rem;
}

td {
    padding: 1rem;
    border-bottom: 1px solid #E0E0E0;
    font-size: 0.95rem;
}

tr:last-child td {
    border-bottom: none;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

tr:hover {
    background-color: #f0f0f0;
}

/* Follow-up questions */
.follow-up-question {
    background-color: var(--primary-light);
    padding: 1rem;
    border-radius: var(--border-radius-sm);
    margin-bottom: 1rem;
    border-left: 3px solid var(--primary-color);
    transition: var(--transition);
}

.follow-up-question:hover {
    background-color: #d0f0eb;
    transform: translateX(5px);
}

/* Health tips */
.health-tip {
    display: flex;
    align-items: flex-start;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #f0f0f0;
}

.health-tip:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
}

.health-tip-icon {
    color: var(--primary-color);
    font-size: 1.3rem;
    margin-right: 0.7rem;
    flex-shrink: 0;
}

.health-tip-content {
    flex-grow: 1;
}

.health-tip-title {
    font-weight: 600;
    margin-bottom: 0.2rem;
}

.health-tip-description {
    color: var(--text-light);
    font-size: 0.9rem;
    line-height: 1.4;
}

/* Duration selector */
.duration-selector {
    margin-top: 1.5rem;
    width: 100%;
}

.duration-label {
    font-weight: 500;
    margin-bottom: 0.5rem;
    color: var(--text-color);
    display: flex;
    align-items: center;
}

.duration-icon {
    margin-right: 0.5rem;
    color: var(--primary-color);
}

/* Override Streamlit's default styling */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-color: #E0E0E0;
    border-radius: var(--border-radius-sm);
    padding: 0.8rem;
    font-size: 1rem;
    transition: var(--transition);
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 1px var(--primary-light);
}

.stSelectbox > div > div > div {
    border-color: #E0E0E0;
    border-radius: var(--border-radius-sm);
    transition: var(--transition);
}

.stSelectbox > div > div > div:hover {
    border-color: var(--primary-color);
}

/* Hide the sidebar collapse button */
.css-fblp2m {
    display: none;
}

/* Footer */
.footer {
    text-align: center;
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid #f0f0f0;
    color: var(--text-light);
    font-size: 0.9rem;
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
    animation: fadeIn 0.5s ease forwards;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .main-header {
        font-size: 2.2rem;
    }

    .sub-header {
        font-size: 1rem;
    }

    .input-area, .card, .results-container {
        padding: 1rem;
    }

    .symptom-button {
        padding: 0.5rem 0.8rem;
        font-size: 0.9rem;
    }

    .check-button {
        padding: 0.8rem 1.2rem;
        font-size: 1rem;
    }
}
</style>

<div class="main-header">Symptom Checker</div>
<div class="sub-header">Describe your symptoms in detail to get AI-powered health insights. Remember, this is not a medical diagnosis.</div>

<div class="disclaimer animate-fade-in">
    <div class="disclaimer-icon">⚠️</div>
    <div class="disclaimer-text">
        <strong>Important Health Notice:</strong> This tool provides informational suggestions only, not medical diagnosis. For serious or persistent symptoms, please consult a healthcare professional.
    </div>
</div>
""", unsafe_allow_html=True)

# Function to extract follow-up questions from AI response
def extract_follow_up_questions(response):
    questions = []
    # Look for follow-up questions section
    if "## Follow-up Questions" in response or "### Follow-up Questions" in response:
        try:
            # Extract the section with follow-up questions
            if "## Follow-up Questions" in response:
                questions_section = response.split("## Follow-up Questions")[1]
            else:
                questions_section = response.split("### Follow-up Questions")[1]

            # Split by next heading or end of text
            if "##" in questions_section:
                questions_section = questions_section.split("##")[0]

            # Extract bullet points as questions
            for line in questions_section.split("\n"):
                if line.strip().startswith("-") or line.strip().startswith("*"):
                    question = line.strip()[1:].strip()
                    if question and len(question) > 10:  # Ensure it's a substantial question
                        questions.append(question)
        except Exception as e:
            logger.warning(f"Error extracting follow-up questions: {e}")

    return questions

# Function to process user input and get medical advice
async def process_medical_query(prompt, is_follow_up=False):
    try:
        # Prepare the prompt with patient data if this is a follow-up
        if is_follow_up and st.session_state.patient_data:
            # Format patient data for the API call
            patient_data_section = "[PATIENT_DATA]\n"
            for key, value in st.session_state.patient_data.items():
                patient_data_section += f"{key}: {value}\n"
            patient_data_section += "[/PATIENT_DATA]"

            # Combine with the prompt
            full_prompt = f"{prompt}\n\n{patient_data_section}"
        else:
            full_prompt = prompt

        # Call the doctor tool with the prepared prompt
        medical_advice = await analyze_symptoms_direct(full_prompt)

        # Check for follow-up questions in the response
        follow_up_questions = extract_follow_up_questions(medical_advice)
        if follow_up_questions:
            st.session_state.follow_up_questions = follow_up_questions
            st.session_state.awaiting_follow_up = True
        else:
            st.session_state.awaiting_follow_up = False
            st.session_state.follow_up_questions = []

        return medical_advice
    except Exception as e:
        logger.error(f"Error in process_medical_query: {e}", exc_info=True)
        return f"I'm sorry, I encountered an error while analyzing your symptoms. Please try again. Error: {str(e)}"

# Create a two-column layout for the main content
col1, col2 = st.columns([2, 1])

with col1:
    # Input area with border and animation
    st.markdown('<div class="input-area animate-fade-in">', unsafe_allow_html=True)

    # Text input option with improved tabs
    st.markdown('<div style="display: flex; gap: 10px; margin-bottom: 15px;">', unsafe_allow_html=True)
    st.markdown('<button class="tab-button active"><span style="margin-right: 5px;">✏️</span> Text Input</button>', unsafe_allow_html=True)
    st.markdown('<button class="tab-button"><span style="margin-right: 5px;">🎤</span> Voice Input</button>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Define common symptoms here so they're available for both the buttons and processing
    common_symptoms = [
        {"name": "Headache", "icon": "🤕"},
        {"name": "Fever", "icon": "🌡️"},
        {"name": "Cough", "icon": "😷"},
        {"name": "Fatigue", "icon": "😴"},
        {"name": "Nausea", "icon": "🤢"},
        {"name": "Dizziness", "icon": "💫"},
        {"name": "Shortness of breath", "icon": "🫁"},
        {"name": "Sore throat", "icon": "👄"}
    ]

    # Process any symptom buttons that were clicked
    current_text = ""
    if "symptom_text_input" in st.session_state:
        current_text = st.session_state.symptom_text_input

    # Check if we need to clear the text (from the "Start New Check" button)
    if "clear_all_data" in st.session_state and st.session_state.clear_all_data:
        current_text = ""

    # Check if any symptom buttons were clicked
    for symptom in common_symptoms:
        symptom_key = f"add_symptom_{symptom['name']}"
        if symptom_key in st.session_state and st.session_state[symptom_key]:
            # Add the symptom to the text
            if current_text and not current_text.endswith(" "):
                current_text += " "
            current_text += symptom['name'].lower()
            # Clear the flag
            st.session_state[symptom_key] = False

    # Symptom input area with enhanced styling
    st.markdown('<label style="font-weight: 500; margin-bottom: 8px; display: block;">Describe your symptoms</label>', unsafe_allow_html=True)
    symptom_input = st.text_area(
        "",
        value=current_text,
        placeholder="For example: I've had a headache for 2 days, with face fever and fatigue. The pain is concentrated on the right side of my head and gets worse when I look at bright lights.",
        height=150,
        key="symptom_text_input"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # Common symptoms section with enhanced styling
    st.markdown('<div class="animate-fade-in" style="animation-delay: 0.1s;">', unsafe_allow_html=True)
    st.markdown('<div class="card-title"><span class="card-title-icon">🔍</span> Common symptoms you can mention:</div>', unsafe_allow_html=True)

    # Use the common symptoms defined above

    # Display symptom buttons in a grid with enhanced styling
    cols = st.columns(4)
    for i, symptom in enumerate(common_symptoms):
        with cols[i % 4]:
            # Create a unique key for each button
            button_key = f"symptom_{i}"
            # Store the symptom in session state if button is clicked
            if st.button(f"{symptom['icon']} {symptom['name']}", key=button_key, use_container_width=True):
                # Store the symptom in a temporary session state variable
                st.session_state[f"add_symptom_{symptom['name']}"] = True
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Duration selector with enhanced styling
    st.markdown('<div class="animate-fade-in" style="animation-delay: 0.2s;">', unsafe_allow_html=True)
    st.markdown('<div class="duration-label"><span class="duration-icon">⏱️</span> How long have you been experiencing these symptoms?</div>', unsafe_allow_html=True)
    duration = st.selectbox(
        "",
        ["Select duration", "Less than 24 hours", "1-3 days", "4-7 days", "1-2 weeks", "More than 2 weeks"],
        index=0
    )

    # Check Symptoms button with enhanced styling
    check_button = st.button("🔍 Check Symptoms", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Display results if available
    if "current_result" in st.session_state and st.session_state.current_result:
        st.markdown('<div class="results-container animate-fade-in">', unsafe_allow_html=True)
        st.markdown('<div class="results-header"><span class="results-header-icon">📝</span> Analysis Results</div>', unsafe_allow_html=True)
        st.markdown('<div class="results-content">', unsafe_allow_html=True)
        st.markdown(st.session_state.current_result, unsafe_allow_html=False)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Display follow-up questions if awaiting answers
        if st.session_state.awaiting_follow_up and st.session_state.follow_up_questions:
            st.markdown('<div class="animate-fade-in" style="margin-top: 2rem;">', unsafe_allow_html=True)
            st.markdown('<div class="card-title"><span class="card-title-icon">💬</span> To provide better health insights, please answer these questions:</div>', unsafe_allow_html=True)
            for i, question in enumerate(st.session_state.follow_up_questions):
                st.markdown(f'<div class="follow-up-question"><strong>{i+1}.</strong> {question}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # Display patient information if available
    if st.session_state.patient_data:
        st.markdown('<div class="card animate-fade-in">', unsafe_allow_html=True)
        st.markdown('<div class="card-title"><span class="card-title-icon">📃</span> Your Information</div>', unsafe_allow_html=True)

        # Create a formatted display of patient data
        for key, value in st.session_state.patient_data.items():
            st.markdown(f'<div style="margin-bottom: 10px;"><strong>{key}:</strong> {value}</div>', unsafe_allow_html=True)

        # No button here anymore
        st.markdown('</div>', unsafe_allow_html=True)

    # Health tips section with enhanced styling
    st.markdown('<div class="card animate-fade-in" style="animation-delay: 0.1s;">', unsafe_allow_html=True)
    st.markdown('<div class="card-title"><span class="card-title-icon">🛠️</span> Health Tips</div>', unsafe_allow_html=True)

    # Health tips with improved layout
    health_tips = [
        {
            "icon": "🌡️",
            "title": "Track your symptoms",
            "description": "Note when they started and any changes over time"
        },
        {
            "icon": "💧",
            "title": "Stay hydrated",
            "description": "Drink plenty of water, especially when ill"
        },
        {
            "icon": "🛌",
            "title": "Rest properly",
            "description": "Give your body time to recover and heal"
        },
        {
            "icon": "🩺",
            "title": "Seek help",
            "description": "Don't delay contacting a doctor for serious symptoms"
        }
    ]

    for tip in health_tips:
        st.markdown(f'''
        <div class="health-tip">
            <div class="health-tip-icon">{tip["icon"]}</div>
            <div class="health-tip-content">
                <div class="health-tip-title">{tip["title"]}</div>
                <div class="health-tip-description">{tip["description"]}</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Footer with enhanced styling
    st.markdown('<div class="footer animate-fade-in" style="animation-delay: 0.2s;">', unsafe_allow_html=True)
    st.markdown('© 2025 Symptom Checker | For informational purposes only', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Process the check button click
if check_button:
    if symptom_input.strip():
        # Store the symptom input and duration in session state
        if duration != "Select duration":
            st.session_state.patient_data["Duration"] = duration

        # Show a spinner with custom message
        with st.spinner("Our AI doctor is analyzing your symptoms..."):
            # Show a progress bar with custom styling
            progress_container = st.container()
            progress_bar = progress_container.progress(0)

            # Add a message above the progress bar
            progress_message = st.empty()
            progress_message.markdown('<div style="text-align: center; color: var(--primary-color); font-weight: 500; margin-bottom: 10px;">Processing your health information...</div>', unsafe_allow_html=True)

            # Simulate progress with more realistic steps
            progress_steps = [
                (0, 20, 0.02, "Analyzing symptoms..."),
                (20, 40, 0.03, "Checking medical database..."),
                (40, 70, 0.01, "Generating potential diagnoses..."),
                (70, 90, 0.02, "Preparing recommendations..."),
                (90, 100, 0.03, "Finalizing results...")
            ]

            for start, end, delay, message in progress_steps:
                progress_message.markdown(f'<div style="text-align: center; color: var(--primary-color); font-weight: 500; margin-bottom: 10px;">{message}</div>', unsafe_allow_html=True)
                for i in range(start, end):
                    time.sleep(delay)
                    progress_bar.progress(i)

            # Process the medical query
            result = asyncio.run(process_medical_query(symptom_input, is_follow_up=bool(st.session_state.patient_data)))

            # Store the result in session state
            st.session_state.current_result = result

            # Complete the progress bar
            progress_bar.progress(100)
            progress_message.markdown('<div style="text-align: center; color: var(--primary-color); font-weight: 500; margin-bottom: 10px;">Analysis complete!</div>', unsafe_allow_html=True)

            # Remove the progress elements after a short delay
            time.sleep(0.5)
            progress_container.empty()
            progress_message.empty()

            # Rerun to display the results
            st.rerun()
    else:
        st.error("Please describe your symptoms before checking.")

# Add disclaimer at the bottom with enhanced styling
st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
st.markdown("""
<div class="animate-fade-in" style="animation-delay: 0.3s; background-color: #f8f9fa; padding: 1.5rem; border-radius: var(--border-radius); box-shadow: var(--box-shadow); border-left: 4px solid #dc3545;">
    <h4 style="color: #dc3545; margin-top: 0; display: flex; align-items: center; font-size: 1.2rem; margin-bottom: 1rem;">
        <span style="margin-right: 0.5rem; font-size: 1.4rem;">⚕️</span> Medical Disclaimer
    </h4>
    <p style="margin-bottom: 0.8rem; line-height: 1.6;">This symptom checker provides information for educational purposes only. The information provided is not a substitute for professional medical advice, diagnosis, or treatment.</p>
    <p style="margin-bottom: 0.8rem; line-height: 1.6;">Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition. Never disregard professional medical advice or delay in seeking it because of something you have read on this application.</p>
    <p style="margin-bottom: 0; line-height: 1.6;">If you think you may have a medical emergency, call your doctor or emergency services immediately.</p>
</div>
""", unsafe_allow_html=True)
