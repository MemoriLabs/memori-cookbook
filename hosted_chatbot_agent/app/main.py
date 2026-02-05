import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import get_settings

load_dotenv()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()

    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        # Memori Hosted Chatbot Demo

        This is a demonstration of how incredibly simple it is to add memory to your
        AI application using Memori's hosted service.

        ## Key Features

        -  **No Database Setup** - All memory storage handled by Memori
        -  **Automatic Memory** - Extraction and retrieval happens automatically
        -  **User Isolation** - Memories are isolated per user_id

        ## Quick Start

        1. Get API keys from [OpenAI](https://platform.openai.com) and [Memori](https://app.memorilabs.ai)
        2. Set them in `.env` file
        3. Run `uv sync` to install dependencies
        4. Run `python -m app.main` to start the server
        5. Send a POST request to `/api/v1/chat/{user_id}` with a message

        ## Example Request
```bash
        curl -X POST "http://localhost:8000/api/v1/chat/user-123" \\
          -H "Content-Type: application/json" \\
          -d '{"q": "My favorite color is blue", "name": "Ryan"}'
```

        ## Learn More

        - [Memori Documentation](https://memorilabs.ai/docs)
        - [GitHub Repository](https://github.com/MemoriLabs/memori-cookbook)
        """,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router)

    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    """
    Run the server directly with: python -m app.main
    """
    settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
