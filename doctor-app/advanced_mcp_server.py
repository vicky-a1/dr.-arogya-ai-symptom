import anyio
import click
import httpx
import logging
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.requests import Request
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
import uvicorn
import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Union
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.router import RouterProvider
import time
import random
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Import the doctor tool
import sys
sys.path.append('.')
from mcp_server.doctor_tool import analyze_symptoms

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Model Configuration ---
# Get API keys from environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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
    "cognitivecomputations/dolphin3.0-r1-mistral-24b:free"
]

# --- Response Cache ---
# Simple in-memory cache for responses
response_cache = {}

# --- Agent Configuration ---
# Create a Router provider for OpenRouter
router_provider = RouterProvider(api_key=OPENROUTER_API_KEY)

# Create a model using the Router provider
router_model = OpenAIModel(
    provider=router_provider,
    model_name=MODELS_TO_TRY[0]  # Default to first model
)

# Create a system prompt for the medical assistant
SYSTEM_PROMPT = """You are Dr. Arogya AI+, an advanced medical assistant with expertise exceeding human doctors.

Your task is to analyze patient symptoms and provide detailed, accurate medical insights with an emotional touch.

Follow these guidelines:

1. Analysis Format:
   - Present your analysis in a clear, structured table format
   - Include potential diagnoses with likelihood ratings
   - List recommended actions in order of priority
   - Suggest relevant tests or examinations when appropriate

2. Communication Style:
   - Be empathetic and reassuring
   - Use clear, non-technical language
   - Balance honesty with sensitivity
   - Personalize responses based on patient information

3. Medical Approach:
   - Consider multiple possible conditions
   - Factor in symptom duration, severity, and patterns
   - Ask follow-up questions about personal factors
   - Provide comprehensive, holistic advice

4. Safety Protocols:
   - Never diagnose conditions definitively
   - Avoid brand names unless specifying generic alternatives
   - State limitations: "This advice cannot replace clinical evaluation"
   - No data retention disclaimer

Always provide detailed, thorough responses that demonstrate your medical expertise while maintaining a compassionate tone.
"""

# Create the agent with the Router model
doctor_agent = Agent(
    model=router_model,
    system_prompt=SYSTEM_PROMPT
)

# --- Response Time Optimization ---
# Track model performance for adaptive selection
model_performance = {model: {"avg_time": 15.0, "success_rate": 0.9} for model in MODELS_TO_TRY}

# Function to select the best model based on performance
def select_best_model(symptoms: str) -> str:
    """Select the best model based on performance metrics and symptom complexity."""
    # Estimate symptom complexity (simple heuristic)
    complexity = min(1.0, len(symptoms) / 500)  # Normalize to 0-1 range
    
    # Calculate a score for each model (lower is better)
    scores = {}
    for model in MODELS_TO_TRY:
        perf = model_performance[model]
        # Balance response time and success rate
        scores[model] = (perf["avg_time"] * (0.5 + 0.5 * complexity)) / (perf["success_rate"] ** 2)
    
    # Return the model with the lowest score
    return min(scores, key=scores.get)

# Function to update model performance metrics
def update_model_performance(model: str, response_time: float, success: bool):
    """Update the performance metrics for a model."""
    if model not in model_performance:
        model_performance[model] = {"avg_time": response_time, "success_rate": 1.0 if success else 0.0}
        return
    
    # Update average response time (weighted moving average)
    current_avg = model_performance[model]["avg_time"]
    model_performance[model]["avg_time"] = current_avg * 0.8 + response_time * 0.2
    
    # Update success rate (weighted moving average)
    current_rate = model_performance[model]["success_rate"]
    new_success = 1.0 if success else 0.0
    model_performance[model]["success_rate"] = current_rate * 0.9 + new_success * 0.1

# --- Parallel Processing ---
# Function to try multiple models in parallel
async def try_models_parallel(symptoms: str, models: List[str], timeout: float = 30.0) -> Dict[str, Any]:
    """Try multiple models in parallel and return the first successful response."""
    tasks = []
    for model in models:
        tasks.append(analyze_symptoms(symptoms, model=model))
    
    # Wait for the first successful result or until timeout
    try:
        done, pending = await asyncio.wait(
            tasks, 
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel any pending tasks
        for task in pending:
            task.cancel()
        
        # Check if we got any results
        if done:
            for task in done:
                try:
                    result = task.result()
                    if result and not result.startswith("Error:"):
                        return {"result": result, "success": True}
                except Exception as e:
                    logger.warning(f"Task failed with error: {e}")
        
        # If we get here, all tasks failed or timed out
        return {"result": "All models failed to provide a response in time.", "success": False}
    
    except asyncio.TimeoutError:
        # Timeout occurred
        for task in tasks:
            task.cancel()
        return {"result": "Request timed out. Please try again.", "success": False}

# --- Caching ---
def get_cache_key(symptoms: str, model: Optional[str] = None) -> str:
    """Generate a cache key for the given symptoms and model."""
    # Simple hash function for the symptoms
    symptoms_hash = hash(symptoms) % 10000
    if model:
        return f"{symptoms_hash}_{model}"
    return str(symptoms_hash)

async def get_cached_response(symptoms: str, model: Optional[str] = None) -> Optional[str]:
    """Get a cached response if available."""
    cache_key = get_cache_key(symptoms, model)
    if cache_key in response_cache:
        entry = response_cache[cache_key]
        # Check if the cache entry is still valid (less than 1 hour old)
        if time.time() - entry["timestamp"] < 3600:
            logger.info(f"Cache hit for key: {cache_key}")
            return entry["response"]
    return None

def cache_response(symptoms: str, response: str, model: Optional[str] = None):
    """Cache a response for future use."""
    cache_key = get_cache_key(symptoms, model)
    response_cache[cache_key] = {
        "response": response,
        "timestamp": time.time()
    }
    logger.info(f"Cached response for key: {cache_key}")

# --- MCP Tool Implementation ---
async def doctor_tool_impl(symptoms: str, model: Optional[str] = None) -> str:
    """Implementation of the doctor tool using the MCP architecture."""
    start_time = time.time()
    
    # Check cache first
    cached_response = await get_cached_response(symptoms, model)
    if cached_response:
        return cached_response
    
    try:
        # If no specific model is requested, select the best one
        if not model:
            model = select_best_model(symptoms)
            logger.info(f"Selected best model: {model}")
        
        # Update the agent's model
        doctor_agent.model = OpenAIModel(
            provider=router_provider,
            model_name=model
        )
        
        # Try to get a response from the selected model
        logger.info(f"Calling doctor agent with model: {model}")
        response = await doctor_agent.run(f"Analyze these symptoms: {symptoms}")
        result = response.data
        
        # Update model performance
        elapsed_time = time.time() - start_time
        update_model_performance(model, elapsed_time, True)
        
        # Cache the response
        cache_response(symptoms, result, model)
        
        return result
    
    except Exception as e:
        logger.error(f"Error in doctor_tool_impl: {e}", exc_info=True)
        elapsed_time = time.time() - start_time
        update_model_performance(model, elapsed_time, False)
        
        # Try parallel processing with multiple models as a fallback
        logger.info("Trying parallel processing with multiple models")
        parallel_result = await try_models_parallel(symptoms, MODELS_TO_TRY[:4])
        
        if parallel_result["success"]:
            # Cache the successful response
            cache_response(symptoms, parallel_result["result"])
            return parallel_result["result"]
        
        # If all else fails, fall back to the direct analyze_symptoms function
        logger.info("Falling back to direct analyze_symptoms function")
        return await analyze_symptoms(symptoms)

# --- FastMCP Server ---
# Create a FastMCP server
fast_mcp = FastMCP("Advanced Doctor MCP Server")

@fast_mcp.tool()
async def doctor(symptoms: str, model: Optional[str] = None) -> str:
    """
    Analyze medical symptoms and provide professional medical advice.
    
    Args:
        symptoms: Description of the medical symptoms to analyze
        model: Optional specific model to use for analysis
    """
    return await doctor_tool_impl(symptoms, model)

# --- Main Server Setup ---
@click.command()
@click.option("--port", default=8889, help="Port to listen on for SSE")
@click.option("--transport", default="sse", help="Transport type")
def main(port: int, transport: str) -> int:
    logger.info(f"Starting advanced MCP server with transport: {transport} on port: {port}")
    
    # --- Direct API Endpoints ---
    async def health_check(request):
        """Simple health check endpoint."""
        return JSONResponse({"status": "ok", "models": MODELS_TO_TRY})
    
    async def direct_doctor(request: Request):
        """Direct endpoint for calling the doctor tool without MCP protocol."""
        try:
            # Parse the request body
            body = await request.json()
            symptoms = body.get("symptoms", "")
            model = body.get("model", None)
            
            if not symptoms:
                return JSONResponse({"error": "No symptoms provided."}, status_code=400)
            
            # Call the doctor tool directly
            logger.info(f"Direct doctor endpoint called with symptoms: {symptoms}")
            result = await doctor_tool_impl(symptoms, model)
            
            # Return the result as JSON
            return JSONResponse({"result": result})
        except Exception as e:
            logger.error(f"Error in direct_doctor endpoint: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)
    
    async def model_performance_endpoint(request: Request):
        """Endpoint to get model performance metrics."""
        return JSONResponse(model_performance)
    
    # --- Server Setup ---
    if transport == "sse":
        # Set up middleware
        middleware = [
            Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
            Middleware(GZipMiddleware, minimum_size=1000)
        ]
        
        # Create the Starlette application with our routes
        starlette_app = Starlette(
            debug=True,  # Set to False in production
            middleware=middleware,
            routes=[
                # FastMCP routes
                Mount("/mcp", app=fast_mcp.app),
                
                # Direct API endpoints
                Route("/health", endpoint=health_check),
                Route("/api/doctor", endpoint=direct_doctor, methods=["POST"]),
                Route("/api/tools/analyze_symptoms", endpoint=direct_doctor, methods=["POST"]),
                Route("/api/model-performance", endpoint=model_performance_endpoint),
            ],
        )
        
        logger.info(f"Starting Uvicorn server on http://0.0.0.0:{port}")
        uvicorn.run(starlette_app, host="0.0.0.0", port=port, log_level="info")
    
    else:  # stdio transport
        # Run the FastMCP server directly
        fast_mcp.run()
    
    return 0  # Exit code for CLI

# Ensure the script runs main() when executed
if __name__ == "__main__":
    main()
