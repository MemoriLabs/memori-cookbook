import sys
from pathlib import Path


def check_env_file():
    """Check if .env file exists and has required variables."""
    env_file = Path(".env")

    if not env_file.exists():
        print("❌ Error: .env file not found!")
        print("")
        print("Please create a .env file with your API keys:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your OPENAI_API_KEY")
        print("  3. Add your MEMORI_API_KEY")
        print("")
        print("Get API keys from:")
        print("  OpenAI: https://platform.openai.com/api-keys")
        print("  Memori: https://app.memorilabs.ai/signup (free!)")
        return False

    # Check if keys are set
    env_content = env_file.read_text()

    if (
        "sk-your-openai-api-key-here" in env_content
        or "OPENAI_API_KEY=" not in env_content
    ):
        print("⚠️  Warning: OPENAI_API_KEY not set in .env file")
        print("Get your key from: https://platform.openai.com/api-keys")
        return False

    if (
        "mk-your-memori-api-key-here" in env_content
        or "MEMORI_API_KEY=" not in env_content
    ):
        print("⚠️  Warning: MEMORI_API_KEY not set in .env file")
        print("Get your key from: https://app.memorilabs.ai/signup (free!)")
        return False

    return True


def main():
    """Run the server with helpful messages."""
    print("🚀 Memori Hosted Chatbot Demo")
    print("=" * 50)
    print("")

    # Check environment
    if not check_env_file():
        print("")
        print("Please set up your .env file first!")
        sys.exit(1)

    print("✅ Environment configured")
    print("")
    print("Starting server...")
    print("  - API docs: http://localhost:8000/docs")
    print("  - Health check: http://localhost:8000/health")
    print("  - Chat endpoint: POST http://localhost:8000/api/v1/chat/{user_id}")
    print("")
    print("Try it with curl:")
    print('  curl -X POST "http://localhost:8000/api/v1/chat/user-123" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"q": "Hello!", "name": "Ryan"}\'')
    print("")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    print("")

    # Import and run
    try:
        import uvicorn
        from app.core.config import get_settings

        settings = get_settings()

        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("")
        print("Server stopped. Thanks for trying Memori! 👋")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
