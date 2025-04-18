# Dr. Arogya AI+ Your Personal Medical Assistant

An advanced AI-powered medical assistant that analyzes symptoms and provides personalized medical advice using the Model Context Protocol (MCP) architecture.

## Features

- **Symptom Analysis**: Enter your symptoms and receive detailed medical analysis
- **Potential Diagnosis**: Get a list of possible conditions based on your symptoms
- **Treatment Recommendations**: Receive suggestions for medications, home remedies, and lifestyle changes
- **Severity Assessment**: Understand the urgency of your condition
- **Follow-up Guidance**: Know when to see a doctor and what tests might be needed
- **Fast Response Time**: Get medical advice within 5-30 seconds
- **User-Friendly Interface**: Easy-to-use chat interface with progress indicators

## Architecture

This application follows the MCP (Model Context Protocol) architecture:

1. **Streamlit Frontend**: User interface with an agentic client that connects to the MCP server
2. **MCP SSE Server**: Remote server that exposes medical expertise via SSE transport
3. **LLM Integration**: Uses Router API as primary and falls back to other providers if needed

## Technology Stack

- **Backend**: Python with FastAPI
- **Frontend**: Streamlit
- **AI Models**: OpenRouter API with various LLM models
- **Architecture**: MCP (Model-Controller-Presenter) architecture

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Option 1: Running with Docker (Recommended)

1. Clone the repository:
   ```
   git clone https://github.com/vicky-a1/dr.-arogya-ai-symptom.git
   cd dr.-arogya-ai-symptom
   ```

2. Create a `.env` file with your API keys (see `.env.example`)
3. Build and run the containers:
   ```
   docker-compose up --build
   ```
4. Open your browser to http://localhost:8501

### Option 2: Running Locally
1. Clone the repository:
   ```
   git clone https://github.com/vicky-a1/dr.-arogya-ai-symptom.git
   cd dr.-arogya-ai-symptom
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your OpenRouter API key:
   ```
   ROUTER_API_KEY=your_openrouter_api_key
   ```

4. Start the MCP SSE server:
   ```
   python PydanticAI/doctor-app/sse_server.py --transport sse --port 8888
   ```

5. In a separate terminal, start the Streamlit frontend:
   ```
   streamlit run PydanticAI/doctor-app/app/main.py
   ```

6. Open your browser to http://localhost:8501

## Usage

1. Enter your symptoms in the chat interface
2. Wait for the AI to analyze your symptoms (5-30 seconds)
3. Review the medical advice provided
4. For common symptoms, you can also use the quick buttons in the sidebar

## How It Works

1. The user enters their symptoms in the chat interface
2. The Streamlit app's agent recognizes this as a medical query
3. The agent connects to the remote MCP server via SSE transport
4. The MCP server processes the symptoms using its medical expertise
5. The response is sent back to the agent and displayed to the user

## Medical Disclaimer

This application provides information for educational purposes only. The information provided is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
