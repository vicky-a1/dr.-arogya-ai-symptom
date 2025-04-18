import anyio
import click
import httpx
import logging
import mcp.types as types
from mcp.server.lowlevel import Server
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.requests import Request
import uvicorn
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the doctor tool
import sys
sys.path.append('.')
from mcp_server.doctor_tool import analyze_symptoms

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Main Server Setup ---
@click.command()
@click.option("--port", default=8888, help="Port to listen on for SSE")
@click.option("--transport", default="sse", help="Transport type")
def main(port: int, transport: str) -> int:
    logger.debug(f"Starting server with transport: {transport} on port: {port}")
    # Give the server a descriptive name
    app = Server("doctor-sse-server")

    # --- Tool Dispatcher ---
    @app.call_tool()
    async def handle_tool_call(
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handles incoming requests to call a specific tool."""
        logger.debug(f"Tool requested: '{name}' with arguments: {arguments}")

        if name == "doctor":
            if "name" not in arguments:
                logger.error(f"Missing required argument 'name' for tool '{name}'")
                # Return error message in the expected format
                return [types.TextContent(type="text", text="Error: Missing required argument 'name' for doctor tool.")]
            # Call the medical analysis implementation
            result = await analyze_symptoms(arguments["name"])
            return [types.TextContent(type="text", text=result)]
        else:
            logger.error(f"Unknown tool requested: {name}")
            # Return error message in the expected format
            return [types.TextContent(type="text", text=f"Error: Unknown tool '{name}'. Available tools: doctor.")]

    # --- Tool Lister ---
    @app.list_tools()
    async def list_available_tools() -> list[types.Tool]:
        """Lists all tools provided by this server."""
        logger.debug("Listing available tools.")
        return [
            # Doctor Tool Definition
            types.Tool(
                name="doctor",
                description="Family doctor for consultation on medical conditions.",
                inputSchema={
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Description of the medical condition or symptoms.",
                        }
                    },
                },
                # outputSchema could specify the format of the TextContent if needed
            ),
        ]

    logger.debug(f"Setting up SSE transport...")
    from mcp.server.sse import SseServerTransport

    # Using /messages/ for POST as per original code
    sse_transport = SseServerTransport("/messages/") # Path for POSTing messages *to* the server

    if transport == "sse":
        # Define the health check endpoint
        async def health_check(request):
            """Simple health check endpoint."""
            return JSONResponse({"status": "ok"})

        # Define a direct endpoint for calling the doctor tool
        async def direct_doctor(request: Request):
            """Direct endpoint for calling the doctor tool without MCP protocol."""
            try:
                # Parse the request body
                body = await request.json()
                symptoms = body.get("symptoms", "")
                model = body.get("model", None)  # Get the optional model parameter

                if not symptoms:
                    return PlainTextResponse("Error: No symptoms provided.", status_code=400)

                # Call the doctor tool directly
                if model:
                    logger.info(f"Direct doctor endpoint called with symptoms: {symptoms} and model: {model}")
                    result = await analyze_symptoms(symptoms, model=model)
                else:
                    logger.info(f"Direct doctor endpoint called with symptoms: {symptoms}")
                    result = await analyze_symptoms(symptoms)

                # Return the result as JSON
                # Check if the result is already a JSON string
                if isinstance(result, str) and result.startswith('{') and result.endswith('}'):
                    try:
                        # Try to parse as JSON
                        json_result = json.loads(result)
                        return JSONResponse(json_result)
                    except json.JSONDecodeError:
                        pass

                # If not JSON or parsing failed, wrap it in a result field
                return JSONResponse({"result": result})
            except Exception as e:
                logger.error(f"Error in direct_doctor endpoint: {e}", exc_info=True)
                return JSONResponse({"error": str(e)}, status_code=500)

        # Define the SSE connection handler
        async def handle_sse_connection(request):
            """Handles the initial SSE connection request from a client."""
            logger.debug(f"Handling new SSE connection request from: {request.client}")
            # The sse_transport manages the actual SSE stream communication
            async with sse_transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                # streams[0] is for reading from client, streams[1] is for writing to client
                logger.debug(f"SSE connection established for {request.client}. Running MCP app logic.")
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )
            logger.debug(f"SSE connection closed for {request.client}.")
            # Note: The response is handled internally by connect_sse

        # Create the Starlette application with our routes
        starlette_app = Starlette(
            debug=True, # Set to False in production
            routes=[
                # Endpoint where clients connect to establish the SSE stream
                Route("/sse", endpoint=handle_sse_connection),
                # Endpoint where clients POST messages *to* the server (part of SSE protocol)
                Mount("/messages/", app=sse_transport.handle_post_message),
                # Standard health check endpoint
                Route("/health", endpoint=health_check),
                # Direct endpoint for calling the doctor tool without MCP protocol
                Route("/direct-doctor", endpoint=direct_doctor, methods=["POST"]),
                # API endpoint for analyze_symptoms tool
                Route("/api/tools/analyze_symptoms", endpoint=direct_doctor, methods=["POST"]),
            ],
        )

        logger.info(f"Starting Uvicorn server with SSE transport on http://0.0.0.0:{port}")
        uvicorn.run(starlette_app, host="0.0.0.0", port=port, log_level="info")

    else: # stdio transport
        from mcp.server.stdio import stdio_server

        async def arun_stdio():
            logger.info("Starting MCP server with stdio transport.")
            async with stdio_server() as streams:
                # streams[0] is stdin, streams[1] is stdout
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )
            logger.info("Stdio server stopped.")

        # Run the stdio server using anyio
        try:
            anyio.run(arun_stdio)
        except KeyboardInterrupt:
            logger.info("Stdio server interrupted by user.")

    return 0 # Exit code for CLI

# Ensure the script runs main() when executed
if __name__ == "__main__":
    main()
