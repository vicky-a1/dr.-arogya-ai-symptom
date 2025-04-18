# app/main.py
import streamlit as st
import os
import logging
import asyncio
import json
import httpx
import time

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# MCP server URL
MCP_SERVER_URL = "http://localhost:8888"

# Direct MCP client implementation without using pydantic_ai
async def call_doctor_tool(symptoms: str) -> str:
    """Call the doctor tool directly using the MCP protocol."""
    try:
        # Step 1: Connect to the SSE endpoint to get the session ID
        async with httpx.AsyncClient() as client:
            # Get the SSE endpoint
            logger.info(f"Connecting to SSE endpoint: {MCP_SERVER_URL}/sse")
            response = await client.get(f"{MCP_SERVER_URL}/sse", timeout=30.0)

            if response.status_code != 200:
                logger.error(f"Failed to connect to SSE endpoint: {response.status_code}")
                return f"Error: Failed to connect to the medical service. Status code: {response.status_code}"

            # Extract the session ID from the first SSE message
            for line in response.text.split('\n'):
                if line.startswith('data: /messages/?session_id='):
                    session_id = line.split('session_id=')[1].strip()
                    logger.info(f"Got session ID: {session_id}")
                    break
            else:
                logger.error("Failed to get session ID from SSE response")
                return "Error: Failed to establish a connection with the medical service."

            # Step 2: Initialize the MCP session
            messages_url = f"{MCP_SERVER_URL}/messages/?session_id={session_id}"

            # Initialize request
            init_payload = {
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"sampling": {}, "roots": {"listChanged": True}},
                    "clientInfo": {"name": "streamlit-client", "version": "1.0.0"}
                },
                "jsonrpc": "2.0",
                "id": 0
            }

            init_response = await client.post(messages_url, json=init_payload, timeout=30.0)
            if init_response.status_code != 202:
                logger.error(f"Failed to initialize MCP session: {init_response.status_code}")
                return "Error: Failed to initialize the medical service."

            # Send initialized notification
            init_notify = {
                "method": "notifications/initialized",
                "jsonrpc": "2.0"
            }

            notify_response = await client.post(messages_url, json=init_notify, timeout=30.0)
            if notify_response.status_code != 202:
                logger.error(f"Failed to send initialized notification: {notify_response.status_code}")
                return "Error: Failed to initialize the medical service."

            # Step 3: List available tools
            list_tools = {
                "method": "tools/list",
                "jsonrpc": "2.0",
                "id": 1
            }

            tools_response = await client.post(messages_url, json=list_tools, timeout=30.0)
            if tools_response.status_code != 202:
                logger.error(f"Failed to list tools: {tools_response.status_code}")
                return "Error: Failed to get available medical tools."

            # Step 4: Call the doctor tool
            call_tool = {
                "method": "tools/call",
                "params": {
                    "name": "doctor",
                    "arguments": {"name": symptoms}
                },
                "jsonrpc": "2.0",
                "id": 2
            }

            logger.info(f"Calling doctor tool with symptoms: {symptoms}")
            tool_response = await client.post(messages_url, json=call_tool, timeout=60.0)

            if tool_response.status_code != 202:
                logger.error(f"Failed to call doctor tool: {tool_response.status_code}")
                return "Error: Failed to analyze your symptoms. Please try again."

            # Step 5: Wait for the response in the SSE stream
            # Since we can't easily parse the SSE stream in this simple implementation,
            # we'll make a direct call to the MCP server's doctor tool

            # Direct call to the doctor tool via the handle_tool_call function
            direct_response = await client.post(
                f"{MCP_SERVER_URL}/direct-call",
                json={"tool": "doctor", "symptoms": symptoms},
                timeout=60.0
            )

            if direct_response.status_code == 200:
                return direct_response.text
            else:
                # Fallback: Make a direct HTTP request to the doctor tool
                logger.info("Using direct HTTP request to the doctor tool")
                direct_call_url = f"{MCP_SERVER_URL}/direct-doctor"
                direct_call_response = await client.post(
                    direct_call_url,
                    json={"symptoms": symptoms},
                    timeout=60.0
                )

                if direct_call_response.status_code == 200:
                    return direct_call_response.text
                else:
                    # Final fallback: Call the analyze_symptoms function directly
                    # This is a simplified implementation that doesn't use the MCP protocol
                    # but directly calls the doctor tool function
                    logger.info("Using simplified direct call to analyze_symptoms")
                    return await analyze_symptoms_direct(symptoms)

    except Exception as e:
        logger.error(f"Error calling doctor tool: {e}", exc_info=True)
        return f"An error occurred while analyzing your symptoms. Please try again. Error: {str(e)}"

# Simplified direct implementation of analyze_symptoms
async def analyze_symptoms_direct(symptoms: str) -> str:
    """Direct implementation of the analyze_symptoms function."""
    try:
        # Import the analyze_symptoms function from the doctor_tool module
        import sys
        import os

        # Add the parent directory to the path so we can import the doctor_tool module
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if parent_dir not in sys.path:
            sys.path.append(parent_dir)

        # Import the analyze_symptoms function
        from mcp_server.doctor_tool import analyze_symptoms

        # Call the function directly
        result = await analyze_symptoms(symptoms)
        return result
    except Exception as e:
        logger.error(f"Error in direct analyze_symptoms call: {e}", exc_info=True)
        return f"An error occurred while analyzing your symptoms. Please try again. Error: {str(e)}"

# --- Streamlit UI ---
st.set_page_config(
    page_title="AI Doctor - Medical Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling based on the provided image
st.markdown("""
<style>
:root {
    --primary-color: #00BFA6;
    --text-color: #333333;
    --light-gray: #f8f9fa;
    --border-radius: 8px;
}

.main-header {
    font-size: 2.5rem;
    color: var(--primary-color);
    text-align: center;
    margin-bottom: 0.5rem;
    font-weight: 600;
}

.sub-header {
    font-size: 1rem;
    color: var(--text-color);
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

.symptom-button {
    background-color: #E0F7F4;
    color: var(--text-color);
    border: none;
    border-radius: var(--border-radius);
    padding: 0.5rem 1rem;
    margin: 0.25rem;
    font-size: 0.9rem;
    cursor: pointer;
    transition: background-color 0.3s;
}

.symptom-button:hover {
    background-color: #B2EBE0;
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

.check-button:hover {
    background-color: #00A896;
}

.input-area {
    border: 1px solid #E0E0E0;
    border-radius: var(--border-radius);
    padding: 1rem;
    margin-bottom: 1.5rem;
}

.input-placeholder {
    color: #9E9E9E;
    font-style: italic;
}

.symptom-tag-container {
    margin-top: 1rem;
}

.duration-selector {
    margin-top: 1rem;
    width: 100%;
}

/* Override Streamlit's default styling */
.stTextInput > div > div > input {
    border-color: #E0E0E0;
    border-radius: var(--border-radius);
}

.stSelectbox > div > div > div {
    border-color: #E0E0E0;
    border-radius: var(--border-radius);
}
</style>

<div class="main-header">Symptom Checker</div>
<div class="sub-header">Describe your symptoms in detail to get AI-powered health insights. Remember, this is not a medical diagnosis.</div>

<div class="disclaimer">
    <div class="disclaimer-icon">⚠️</div>
    <div class="disclaimer-text">
        <strong>Important Health Notice:</strong> This tool provides informational suggestions only, not medical diagnosis. For serious or persistent symptoms, please consult a healthcare professional.
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar with additional information and options
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/medical-doctor.png", width=100)
    st.title("About Dr. AI+")
    st.markdown("""
    This advanced medical assistant provides expert advice based on your symptoms and health information.

    **Features:**
    - Symptom analysis
    - Potential diagnosis suggestions
    - Treatment recommendations
    - Severity assessment
    - Follow-up guidance
    """)

    st.markdown("---")
    st.subheader("Common Symptoms")

    # Example symptoms that users can click on
    example_symptoms = [
        "Headache with fever",
        "Persistent cough",
        "Joint pain in knees",
        "Skin rash with itching",
        "Stomach pain and nausea",
        "Sore throat with difficulty swallowing"
    ]

    # Create buttons for example symptoms
    for symptom in example_symptoms:
        if st.button(symptom):
            # Set this symptom as the current input
            if "current_symptom" not in st.session_state:
                st.session_state.current_symptom = symptom
            else:
                st.session_state.current_symptom = symptom
            # Force a rerun to process this symptom
            st.experimental_rerun()

    st.markdown("---")
    st.caption("Powered by Advanced Medical AI")
    st.caption("© 2025 Dr. AI+ Medical Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm Dr. AI+, your expert medical assistant with extensive knowledge in multiple medical fields. Please describe your symptoms or medical concerns in detail, and I'll provide personalized advice."}
    ]

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Check if we have a symptom from the sidebar buttons
if "current_symptom" in st.session_state:
    prompt = st.session_state.current_symptom
    # Clear it so it doesn't trigger again
    del st.session_state.current_symptom

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process with AI
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Analyzing your symptoms...")

        try:
            with st.spinner("Dr. AI+ is analyzing your symptoms..."):
                # Call the doctor tool directly
                medical_advice = asyncio.run(analyze_symptoms_direct(prompt))

            # Display the response
            message_placeholder.markdown(medical_advice)
            # Add to chat history
            st.session_state.messages.append({"role": "assistant", "content": medical_advice})

        except Exception as e:
            logger.error(f"An error occurred: {e}")
            error_message = f"I'm sorry, I encountered an error while analyzing your symptoms. Please try again. Error: {str(e)}"
            message_placeholder.markdown(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})

# User input via chat
elif prompt := st.chat_input("Describe your symptoms here..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Process with AI
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Analyzing your symptoms...")

        try:
            with st.spinner("Dr. AI+ is analyzing your symptoms..."):
                # Show a progress bar to indicate model selection and processing
                progress_bar = st.progress(0)
                for i in range(100):
                    # Simulate progress
                    time.sleep(0.01)
                    progress_bar.progress(i + 1)

                # Call the doctor tool directly
                medical_advice = asyncio.run(analyze_symptoms_direct(prompt))

                # Remove the progress bar when done
                progress_bar.empty()

            # Display the response
            message_placeholder.markdown(medical_advice)
            # Add to chat history
            st.session_state.messages.append({"role": "assistant", "content": medical_advice})

        except Exception as e:
            logger.error(f"An error occurred: {e}")
            error_message = f"I'm sorry, I encountered an error while analyzing your symptoms. Please try again. Error: {str(e)}"
            message_placeholder.markdown(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})

# Add disclaimer at the bottom
st.markdown("---")
st.markdown("""
<div style="background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #dc3545;">
<h4 style="color: #dc3545; margin-top: 0;">Medical Disclaimer</h4>
<p>This AI assistant provides information for educational purposes only. The information provided by this application is not a substitute for professional medical advice, diagnosis, or treatment.</p>
<p>Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition. Never disregard professional medical advice or delay in seeking it because of something you have read on this application.</p>
<p>If you think you may have a medical emergency, call your doctor or emergency services immediately.</p>
</div>

<div style="text-align: center; margin-top: 1rem; color: #6c757d; font-size: 0.8rem;">
&copy; 2025 Dr. AI+ Medical Assistant | Powered by Advanced Medical AI
</div>
""", unsafe_allow_html=True)
