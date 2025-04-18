# AI Doctor - Medical Assistant

An AI-powered medical assistant that analyzes symptoms and provides medical advice using the Model Context Protocol (MCP) architecture. This application demonstrates how to build a SaaS solution using MCP's SSE transport for remote tool access.

## Architecture

This application follows the MCP (Model Context Protocol) architecture as shown in the diagram:

1. **Streamlit Frontend**: User interface with an agentic client that connects to the MCP server
2. **MCP SSE Server**: Remote server that exposes medical expertise via SSE transport
3. **LLM Integration**: Uses Router API as primary and falls back to other providers if needed

The key advantage of this architecture is that the medical expertise (prompts, tools, etc.) stays secure on the remote MCP server while clients can access it through a standardized interface.

## Setup

### Option 1: Running with Docker (Recommended)

1. Create a `.env` file with your API keys (see `.env.example`)
2. Build and run the containers:
   ```
   docker-compose up --build
   ```
3. Open your browser to http://localhost:8501

### Option 2: Running Locally

1. Create a `.env` file with your API keys (see `.env.example`)
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Start the MCP SSE server:
   ```
   python sse_server.py
   ```
4. In a separate terminal, start the Streamlit frontend:
   ```
   cd app
   streamlit run main.py
   ```
5. Open your browser to http://localhost:8501

## Features

- **Medical Expertise**: Analyzes symptoms and provides potential diagnoses
- **Comprehensive Advice**: Offers medical recommendations, severity assessment, and follow-up guidance
- **Secure Architecture**: Medical expertise stays on the remote server
- **Fallback Mechanisms**: Uses multiple LLM providers for reliability
- **User-Friendly Interface**: Chat-based interface for natural interaction

## How It Works

1. The user enters their symptoms in the chat interface
2. The Streamlit app's agent recognizes this as a medical query
3. The agent connects to the remote MCP server via SSE transport
4. The MCP server processes the symptoms using its medical expertise
5. The response is sent back to the agent and displayed to the user

## Medical Disclaimer

This AI assistant provides information for educational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.
