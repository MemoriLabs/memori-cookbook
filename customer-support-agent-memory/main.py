"""
Customer Support AI Agent with DigitalOcean Gradient AI

A FastAPI-based AI agent that uses DigitalOcean Gradient AI Platform and Memori to provide customer support.
The agent can scrape website content via web crawler data sources and answer user questions based on the website data.
It maintains conversation memory for personalized assistance.

Run: `pip install -r requirements.txt` to install dependencies
Then: `uvicorn main_gradient:app --reload` to start the server
"""

import asyncio
import hashlib
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import asyncpg
import httpx
import validators
from digitalocean_client import DigitalOceanGradientClient
from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    FastAPI,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from memori_integration import get_memori_instance
from pydantic import BaseModel

# Load environment variables
load_dotenv()


# ============================================================================
# Pydantic Models (API Request/Response schemas)
# ============================================================================


class ScrapeWebsiteRequest(BaseModel):
    website_url: str
    depth: int | None = 2
    max_pages: int | None = 20


class QueryRequest(BaseModel):
    question: str
    session_id: str
    user_id: str = "anonymous"
    website_context: str | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    session_id: str


class SessionRequest(BaseModel):
    user_id: str = "anonymous"
    website_url: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    created_at: str
    website_url: str | None = None


class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    website_url: str | None = None
    agent_uuid: str | None = None
    agent_url: str | None = None
    knowledge_base_uuids: list[str] = []


class WebsiteScrapingResponse(BaseModel):
    success: bool
    pages_scraped: int
    message: str
    website_url: str


class FileUploadRequest(BaseModel):
    chunk_size: int | None = 1000
    use_semantic: bool | None = False
    custom_name: str | None = None


class TextUploadRequest(BaseModel):
    text_content: str
    document_name: str
    chunk_size: int | None = 1000
    use_semantic: bool | None = False


class URLUploadRequest(BaseModel):
    url_to_scrape: str
    max_depth: int | None = 2
    max_links: int | None = 20
    chunk_size: int | None = 1000


class KnowledgeUploadResponse(BaseModel):
    success: bool
    message: str
    details: dict | None = None


class DomainRegistrationRequest(BaseModel):
    domain_name: str


class ConversationMessage(BaseModel):
    id: str
    session_id: str
    user_id: str
    role: str  # 'user' or 'assistant'
    content: str
    created_at: str


class ConversationHistoryResponse(BaseModel):
    session_id: str
    user_id: str
    messages: list[ConversationMessage]
    total_messages: int


# ============================================================================
# Global Storage
# ============================================================================

# Store agent info by website_key (one agent per website)
agents: dict[
    str, dict[str, Any]
] = {}  # website_key -> {agent_uuid, agent_url, kb_uuids, created_at}

# Store session info
sessions: dict[str, SessionInfo] = {}

# Store knowledge base UUID by website
knowledge_bases: dict[str, str] = {}  # website_key -> kb_uuid


# ============================================================================
# Database Configuration
# ============================================================================

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://do_user:do_user_password@postgres:5432/customer_support",
)


async def get_db_connection():
    """Get database connection for session management"""
    try:
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = int(os.getenv("POSTGRES_PORT", "5432"))
        db_user = os.getenv("POSTGRES_USER", "do_user")
        db_password = os.getenv("POSTGRES_PASSWORD", "do_user_password")
        db_name = os.getenv("POSTGRES_DB", "customer_support")

        return await asyncio.wait_for(
            asyncpg.connect(
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port,
                database=db_name,
            ),
            timeout=30.0,
        )
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        return None


async def test_db_connection():
    """Test database connection and return status"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return False
        try:
            result = await conn.fetchval("SELECT 1")
            return result == 1
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Database connection test failed: {e}")
        return False


async def save_session_to_db(session_info: SessionInfo) -> bool:
    """Save session to database"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return False
        try:
            await conn.execute(
                """
                INSERT INTO user_sessions (session_id, user_id, website_url, created_at, last_activity, status)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (session_id)
                DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    website_url = EXCLUDED.website_url,
                    last_activity = EXCLUDED.last_activity,
                    status = EXCLUDED.status
            """,
                session_info.session_id,
                session_info.user_id,
                session_info.website_url,
                session_info.created_at,
                session_info.last_activity,
                "active",
            )
            return True
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to save session to database: {e}")
        return False


async def load_session_from_db(session_id: str) -> SessionInfo | None:
    """Load session from database"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return None
        try:
            row = await conn.fetchrow(
                """
                SELECT session_id, user_id, website_url, created_at, last_activity, status
                FROM user_sessions
                WHERE session_id = $1 AND status = 'active'
            """,
                session_id,
            )
            if row:
                return SessionInfo(
                    session_id=str(row["session_id"]),
                    user_id=row["user_id"],
                    website_url=row["website_url"],
                    created_at=row["created_at"],
                    last_activity=row["last_activity"],
                )
            return None
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to load session from database: {e}")
        return None


async def save_conversation_to_db(
    session_id: str,
    user_id: str,
    role: str,
    content: str,
    message_id: str | None = None,
) -> bool:
    """Save conversation message to database"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return False
        try:
            if message_id is None:
                message_id = str(uuid.uuid4())

            await conn.execute(
                """
                INSERT INTO conversation_history (id, session_id, user_id, role, content, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """,
                message_id,
                session_id,
                user_id,
                role,
                content,
                datetime.now(),
            )
            return True
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to save conversation to database: {e}")
        return False


async def save_agent_to_db(website_key: str, agent_info: dict[str, Any]) -> bool:
    """Save agent information to database"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return False
        try:
            await conn.execute(
                """
                INSERT INTO agents (website_key, agent_uuid, agent_url, agent_access_key,
                                   website_url, knowledge_base_uuids, deployment_status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (website_key)
                DO UPDATE SET
                    agent_uuid = EXCLUDED.agent_uuid,
                    agent_url = EXCLUDED.agent_url,
                    agent_access_key = EXCLUDED.agent_access_key,
                    website_url = EXCLUDED.website_url,
                    knowledge_base_uuids = EXCLUDED.knowledge_base_uuids,
                    deployment_status = EXCLUDED.deployment_status,
                    updated_at = EXCLUDED.updated_at
            """,
                website_key,
                agent_info.get("agent_uuid"),
                agent_info.get("agent_url"),
                agent_info.get("agent_access_key"),
                agent_info.get("website_url"),
                agent_info.get("knowledge_base_uuids", []),
                agent_info.get("deployment_status", "UNKNOWN"),
                agent_info.get("created_at", datetime.now()),
                datetime.now(),
            )
            return True
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to save agent to database: {e}")
        return False


async def load_agent_from_db(website_key: str) -> dict[str, Any] | None:
    """Load agent information from database"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return None
        try:
            row = await conn.fetchrow(
                """
                SELECT website_key, agent_uuid, agent_url, agent_access_key,
                       website_url, knowledge_base_uuids, deployment_status, created_at, updated_at
                FROM agents
                WHERE website_key = $1
            """,
                website_key,
            )
            if row:
                return {
                    "agent_uuid": str(row["agent_uuid"]),
                    "agent_url": row["agent_url"],
                    "agent_access_key": row["agent_access_key"],
                    "website_url": row["website_url"],
                    "knowledge_base_uuids": list(row["knowledge_base_uuids"])
                    if row["knowledge_base_uuids"]
                    else [],
                    "deployment_status": row.get("deployment_status", "UNKNOWN"),
                    "created_at": row["created_at"],
                }
            return None
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to load agent from database: {e}")
        return None


async def load_all_agents_from_db() -> dict[str, dict[str, Any]]:
    """Load all agents from database into memory"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return {}
        try:
            rows = await conn.fetch(
                """
                SELECT website_key, agent_uuid, agent_url, agent_access_key,
                       website_url, knowledge_base_uuids, deployment_status, created_at
                FROM agents
            """
            )
            result = {}
            for row in rows:
                website_key = row["website_key"]
                result[website_key] = {
                    "agent_uuid": str(row["agent_uuid"]),
                    "agent_url": row["agent_url"],
                    "agent_access_key": row["agent_access_key"],
                    "website_url": row["website_url"],
                    "knowledge_base_uuids": list(row["knowledge_base_uuids"])
                    if row["knowledge_base_uuids"]
                    else [],
                    "deployment_status": row.get("deployment_status", "UNKNOWN"),
                    "created_at": row["created_at"],
                }
            print(f"DEBUG: Loaded {len(result)} agents from database")
            return result
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to load agents from database: {e}")
        return {}


async def get_reusable_database_id() -> str | None:
    """Get the reusable database ID from config table"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return None
        try:
            row = await conn.fetchrow(
                """
                SELECT config_value
                FROM digitalocean_config
                WHERE config_key = 'database_id' AND config_value != ''
            """
            )
            if row:
                return row["config_value"]
            return None
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to get reusable database ID: {e}")
        return None


async def save_reusable_database_id(database_id: str) -> bool:
    """Save the reusable database ID to config table"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return False
        try:
            await conn.execute(
                """
                INSERT INTO digitalocean_config (config_key, config_value, updated_at)
                VALUES ('database_id', $1, $2)
                ON CONFLICT (config_key)
                DO UPDATE SET
                    config_value = EXCLUDED.config_value,
                    updated_at = EXCLUDED.updated_at
            """,
                database_id,
                datetime.now(),
            )
            return True
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to save reusable database ID: {e}")
        return False


async def save_knowledge_base_to_db(
    website_key: str,
    kb_uuid: str,
    website_url: str,
    kb_name: str | None = None,
    database_id: str | None = None,
) -> bool:
    """Save knowledge base information to database"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return False
        try:
            await conn.execute(
                """
                INSERT INTO knowledge_bases (website_key, kb_uuid, website_url, kb_name, database_id, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (website_key)
                DO UPDATE SET
                    kb_uuid = EXCLUDED.kb_uuid,
                    website_url = EXCLUDED.website_url,
                    kb_name = EXCLUDED.kb_name,
                    database_id = EXCLUDED.database_id,
                    updated_at = EXCLUDED.updated_at
            """,
                website_key,
                kb_uuid,
                website_url,
                kb_name,
                database_id,
                datetime.now(),
                datetime.now(),
            )
            return True
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to save knowledge base to database: {e}")
        return False


async def load_knowledge_base_from_db(website_key: str) -> str | None:
    """Load knowledge base UUID from database"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return None
        try:
            row = await conn.fetchrow(
                """
                SELECT kb_uuid
                FROM knowledge_bases
                WHERE website_key = $1
            """,
                website_key,
            )
            if row:
                return str(row["kb_uuid"])
            return None
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to load knowledge base from database: {e}")
        return None


async def load_all_knowledge_bases_from_db() -> dict[str, str]:
    """Load all knowledge bases from database into memory"""
    try:
        conn = await get_db_connection()
        if conn is None:
            return {}
        try:
            rows = await conn.fetch(
                """
                SELECT website_key, kb_uuid
                FROM knowledge_bases
            """
            )
            result = {row["website_key"]: str(row["kb_uuid"]) for row in rows}
            print(f"DEBUG: Loaded {len(result)} knowledge bases from database")
            return result
        finally:
            await conn.close()
    except Exception as e:
        print(f"ERROR: Failed to load knowledge bases from database: {e}")
        return {}


# ============================================================================
# Helper Functions
# ============================================================================


def get_website_key(url: str) -> str:
    """Generate a unique key for a website URL"""
    return hashlib.md5(url.encode()).hexdigest()[:16]


async def setup_knowledge_base(website_url: str) -> str:
    """
    Set up knowledge base for a specific website

    Args:
        website_url: The website URL to scrape

    Returns:
        Knowledge base UUID
    """
    website_key = get_website_key(website_url)

    # Return existing knowledge base if already in memory
    if website_key in knowledge_bases:
        print(f"DEBUG: Using existing knowledge base from memory for {website_url}")
        return knowledge_bases[website_key]

    # Try to load from database
    kb_uuid = await load_knowledge_base_from_db(website_key)
    if kb_uuid:
        print(f"DEBUG: Loaded knowledge base from database for {website_url}")
        knowledge_bases[website_key] = kb_uuid
        return kb_uuid

    print(f"DEBUG: Creating new knowledge base for {website_url}")

    # Create DigitalOcean client
    client = DigitalOceanGradientClient()

    # Get or create reusable database ID
    database_id = await get_reusable_database_id()
    print(
        f"DEBUG: Using {'existing' if database_id else 'new'} database ID for knowledge base"
    )

    # Create knowledge base with initial web crawler datasource
    kb = await client.create_knowledge_base(
        name=f"KB for {website_url}",
        base_url=website_url,
        database_id=database_id,
        tags=["customer-support", website_key, "auto-created"],
    )
    kb_uuid = kb["uuid"]
    kb_database_id = kb.get("database_id")
    print(f"DEBUG: Created knowledge base with UUID: {kb_uuid}")
    print(f"DEBUG: Knowledge base database ID: {kb_database_id}")

    # Save the database ID for reuse if this is the first KB
    if kb_database_id and not database_id:
        print(f"DEBUG: Saving database ID {kb_database_id} for future reuse")
        await save_reusable_database_id(kb_database_id)

    # Note: Datasource is now created with the KB, no need for separate add_web_crawler_data_source call
    # The indexing should start automatically with the datasource

    # Start indexing job
    # print(f"DEBUG: Starting indexing job for knowledge base {kb_uuid}")
    # job = await client.start_indexing_job(kb_uuid)
    # print(f"DEBUG: Indexing job started with UUID: {job.get('uuid')}")

    # Cache the knowledge base UUID in memory
    knowledge_bases[website_key] = kb_uuid

    # Save to database with database_id
    await save_knowledge_base_to_db(
        website_key, kb_uuid, website_url, f"KB for {website_url}", kb_database_id
    )

    return kb_uuid


async def create_agent(
    website_url: str,
    wait_for_deployment: bool = False,
) -> dict[str, Any]:
    """
    Create a customer support agent for a website using DigitalOcean Gradient AI

    One agent is created per website and shared across all sessions.
    Memori handles user and session-specific context.

    Args:
        website_url: Website URL for knowledge base
        wait_for_deployment: If True, wait for agent deployment to complete

    Returns:
        Dictionary with agent info (agent_uuid, agent_url, kb_uuids)
    """
    print(
        f"DEBUG: create_agent called - website_url: {website_url}, wait_for_deployment: {wait_for_deployment}"
    )

    # Create DigitalOcean client
    client = DigitalOceanGradientClient()

    # Setup knowledge base for website
    kb_uuids = []
    if website_url:
        try:
            kb_uuid = await setup_knowledge_base(website_url)
            kb_uuids = [kb_uuid]
            print(f"DEBUG: Using knowledge base UUID: {kb_uuid}")
        except Exception as e:
            print(f"WARNING: Failed to setup knowledge base: {e}")

    # Create agent instruction (no session/user specific info)
    instruction = f"""You are a helpful Customer Support AI Assistant for {website_url}.

Guidelines:
1. Use your knowledge base from scraped website content to answer questions accurately.
2. Provide helpful, accurate, and friendly responses.
3. If you don't know the answer, say so honestly.
4. When citing information from the knowledge base, mention that it's from the website.
5. Be conversational and maintain context throughout the conversation.
6. The conversation context (user preferences, history, etc.) is managed by Memori and will be provided with each request.

Website: {website_url}

Note: This agent serves multiple users and sessions. User-specific context is managed externally via Memori.
"""

    # Create the agent without knowledge bases (attach after deployment)
    print("DEBUG: Creating DigitalOcean Gradient AI agent for website...")
    website_key = get_website_key(website_url)
    agent = await client.create_agent(
        name=f"Support Agent - {website_url}",
        instruction=instruction,
        knowledge_base_uuids=None,  # Don't attach during creation
        description=f"Customer support agent for {website_url}",
        tags=["customer-support", website_key, "shared-agent"],
        temperature=0.7,
        max_tokens=4096,
        provide_citations=True,
    )

    # Create access key for the agent
    # Note: api_keys from agent response are often invalid/old, so always create a new one
    print(f"DEBUG: Creating new access key for agent {agent['uuid']}")
    agent_access_key = None
    try:
        access_key_response = await client.create_agent_access_key(
            agent_uuid=agent["uuid"], key_name=f"key-{website_key}"
        )
        # Response structure: {"api_key_info": {"secret_key": "...", "name": "...", ...}}
        agent_access_key = access_key_response.get("secret_key")

        if agent_access_key:
            print(
                f"DEBUG: Created new access key successfully (length: {len(agent_access_key)})"
            )
        else:
            print(
                f"WARNING: Could not extract secret_key from response: {access_key_response}"
            )
    except Exception as e:
        print(f"WARNING: Failed to create access key: {e}")
        import traceback

        print(f"WARNING: Traceback: {traceback.format_exc()}")
        agent_access_key = None

    # Extract deployment URL from agent response
    deployment = agent.get("deployment", {})
    agent_url = deployment.get("url") if deployment else None
    deployment_status = deployment.get("status", "UNKNOWN") if deployment else "UNKNOWN"

    # Wait for deployment if requested
    if wait_for_deployment and not agent_url:
        print("DEBUG: Waiting for agent deployment to complete...")
        try:
            deployed_agent = await client.wait_for_agent_deployment(
                agent["uuid"], max_wait_seconds=30, poll_interval=5
            )
            deployment = deployed_agent.get("deployment", {})
            agent_url = deployment.get("url") if deployment else None
            deployment_status = (
                deployment.get("status", "UNKNOWN") if deployment else "UNKNOWN"
            )
            print(f"DEBUG: Agent deployment completed with URL: {agent_url}")
        except TimeoutError as e:
            print(f"WARNING: Agent deployment timeout: {e}")
            # Continue without URL - it will be updated later
        except Exception as e:
            print(f"WARNING: Error waiting for deployment: {e}")
            # Continue without URL - it will be updated later

    # Attach knowledge bases after deployment is ready
    if agent_url and kb_uuids:
        print(f"DEBUG: Agent deployed, attaching {len(kb_uuids)} knowledge base(s)...")
        for kb_uuid in kb_uuids:
            try:
                await client.attach_knowledge_base(
                    agent_uuid=agent["uuid"], knowledge_base_uuid=kb_uuid
                )
                print(f"DEBUG: Successfully attached knowledge base {kb_uuid}")
            except Exception as e:
                print(f"WARNING: Failed to attach knowledge base {kb_uuid}: {e}")
    elif kb_uuids and not agent_url:
        print(
            f"WARNING: Agent not yet deployed (status: {deployment_status}), knowledge bases will need to be attached later"
        )

    agent_info = {
        "agent_uuid": agent["uuid"],
        "agent_url": agent_url,
        "agent_access_key": agent_access_key,
        "knowledge_base_uuids": kb_uuids,
        "website_url": website_url,
        "created_at": datetime.now(),
        "deployment_status": deployment_status,
    }

    print(
        f"DEBUG: Agent created - UUID: {agent['uuid']}, URL: {agent_url}, Status: {deployment_status}"
    )

    return agent_info


async def check_and_update_agent_url(agent_info: dict[str, Any]) -> dict[str, Any]:
    """
    Check if agent has a deployment URL, if not try to fetch it

    Args:
        agent_info: Agent information dictionary

    Returns:
        Updated agent info with URL if available
    """
    # If URL already exists, return as-is
    if agent_info.get("agent_url"):
        return agent_info

    # Try to get updated agent info from DigitalOcean
    agent_uuid = agent_info.get("agent_uuid")
    if not agent_uuid:
        return agent_info

    try:
        client = DigitalOceanGradientClient()
        agent = await client.get_agent(agent_uuid)
        deployment = agent.get("deployment", {})
        agent_url = deployment.get("url") if deployment else None
        deployment_status = (
            deployment.get("status", "UNKNOWN") if deployment else "UNKNOWN"
        )

        if agent_url and agent_url != agent_info.get("agent_url"):
            # Update agent info with new URL
            agent_info["agent_url"] = agent_url
            agent_info["deployment_status"] = deployment_status

            # Create a new access key if not already present
            # Note: api_keys from agent response are often invalid, so create a new one
            if not agent_info.get("agent_access_key"):
                try:
                    website_key_temp = get_website_key(
                        agent_info.get("website_url", "")
                    )
                    access_key_response = await client.create_agent_access_key(
                        agent_uuid=agent_uuid, key_name=f"key-{website_key_temp}"
                    )
                    agent_info["agent_access_key"] = access_key_response.get(
                        "secret_key"
                    )

                    if agent_info["agent_access_key"]:
                        print(
                            f"DEBUG: Created agent access key (length: {len(agent_info['agent_access_key'])})"
                        )
                    else:
                        print(
                            f"WARNING: Could not extract secret_key from: {access_key_response}"
                        )
                except Exception as e:
                    print(
                        f"WARNING: Failed to create access key in check_and_update: {e}"
                    )

            print(f"DEBUG: Updated agent URL: {agent_url}, Status: {deployment_status}")

            # Attach knowledge bases if agent is now deployed and has knowledge bases
            kb_uuids = agent_info.get("knowledge_base_uuids", [])
            if kb_uuids:
                print(
                    f"DEBUG: Agent deployed, attaching {len(kb_uuids)} knowledge base(s)..."
                )
                for kb_uuid in kb_uuids:
                    try:
                        await client.attach_knowledge_base(
                            agent_uuid=agent_uuid, knowledge_base_uuid=kb_uuid
                        )
                        print(f"DEBUG: Successfully attached knowledge base {kb_uuid}")
                    except Exception as e:
                        print(
                            f"WARNING: Failed to attach knowledge base {kb_uuid}: {e}"
                        )

            # Update in database
            website_key = get_website_key(agent_info.get("website_url", ""))
            if website_key:
                await save_agent_to_db(website_key, agent_info)
        else:
            agent_info["deployment_status"] = deployment_status
            print(
                f"DEBUG: Agent deployment status: {deployment_status}, URL not yet available"
            )

    except Exception as e:
        print(f"WARNING: Failed to check agent deployment status: {e}")

    return agent_info


async def poll_agent_deployment_background(
    agent_uuid: str, website_key: str, max_wait_seconds: int = 180
):
    """
    Background task to poll for agent deployment completion

    Args:
        agent_uuid: UUID of the agent
        website_key: Website key for caching
        max_wait_seconds: Maximum time to wait in seconds (default: 180)
    """
    print(f"DEBUG: Starting background polling for agent {agent_uuid}")

    try:
        client = DigitalOceanGradientClient()

        # Wait for deployment to complete
        agent = await client.wait_for_agent_deployment(
            agent_uuid, max_wait_seconds=max_wait_seconds, poll_interval=5
        )

        # Extract deployment info
        deployment = agent.get("deployment", {})
        agent_url = deployment.get("url") if deployment else None
        deployment_status = (
            deployment.get("status", "UNKNOWN") if deployment else "UNKNOWN"
        )

        print(
            f"DEBUG: Background polling completed - URL: {agent_url}, Status: {deployment_status}"
        )

        # Update agent info in memory cache
        if website_key in agents:
            agents[website_key]["agent_url"] = agent_url
            agents[website_key]["deployment_status"] = deployment_status

            # Create a new access key if not already present
            # Note: api_keys from agent response are often invalid, so create a new one
            if not agents[website_key].get("agent_access_key"):
                try:
                    access_key_response = await client.create_agent_access_key(
                        agent_uuid=agent_uuid, key_name=f"key-{website_key}"
                    )
                    agents[website_key]["agent_access_key"] = access_key_response.get(
                        "secret_key"
                    )

                    if agents[website_key]["agent_access_key"]:
                        print(
                            f"DEBUG: Created agent access key in background task (length: {len(agents[website_key]['agent_access_key'])})"
                        )
                    else:
                        print(
                            f"WARNING: Could not extract secret_key in background task: {access_key_response}"
                        )
                except Exception as e:
                    print(
                        f"WARNING: Failed to create access key in background task: {e}"
                    )

            # Attach knowledge bases if agent is deployed and has knowledge bases
            kb_uuids = agents[website_key].get("knowledge_base_uuids", [])
            if agent_url and kb_uuids:
                print(
                    f"DEBUG: Agent deployed, attaching {len(kb_uuids)} knowledge base(s)..."
                )
                for kb_uuid in kb_uuids:
                    try:
                        await client.attach_knowledge_base(
                            agent_uuid=agent_uuid, knowledge_base_uuid=kb_uuid
                        )
                        print(f"DEBUG: Successfully attached knowledge base {kb_uuid}")
                    except Exception as e:
                        print(
                            f"WARNING: Failed to attach knowledge base {kb_uuid}: {e}"
                        )

            # Update in database
            await save_agent_to_db(website_key, agents[website_key])
            print(f"DEBUG: Updated agent in database - URL: {agent_url}")

    except TimeoutError as e:
        print(f"WARNING: Background polling timeout for agent {agent_uuid}: {e}")
    except Exception as e:
        print(f"ERROR: Background polling failed for agent {agent_uuid}: {e}")


async def get_or_create_agent(
    website_url: str | None = None,
    domain_api_key: str | None = None,
) -> dict[str, Any]:
    """
    Get existing agent or create new one for a website

    One agent per website is created and shared across all sessions.
    Memori provides user and session-specific context.

    Returns:
        Agent info dictionary
    """
    # Use a default key if no website URL provided
    website_key = get_website_key(website_url) if website_url else "default"

    # Check if agent already exists in memory
    if website_key in agents:
        print(f"DEBUG: Using existing agent from memory for website {website_url}")
        return agents[website_key]

    # Try to load from database
    agent_info = await load_agent_from_db(website_key)
    if agent_info:
        print(f"DEBUG: Loaded agent from database for website {website_url}")
        agents[website_key] = agent_info
        return agent_info

    # Create new agent for this website
    print(f"DEBUG: Creating new agent for website {website_url}")
    agent_info = await create_agent(website_url or "general", domain_api_key)

    # Store agent info in memory
    agents[website_key] = agent_info

    # Save to database
    await save_agent_to_db(website_key, agent_info)

    return agent_info


# ============================================================================
# Application Lifecycle
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    print("=" * 80)
    print("Starting Customer Support AI Agent with DigitalOcean Gradient AI")
    print("=" * 80)

    # Initialize Memori
    try:
        get_memori_instance()
        print("✓ Memori initialized successfully")
    except Exception as e:
        print(f"✗ Memori initialization failed: {e}")

    # Test database connection
    db_ok = await test_db_connection()
    if db_ok:
        print("✓ Database connection successful")

        # Load agents from database
        global agents
        loaded_agents = await load_all_agents_from_db()
        agents.update(loaded_agents)

        # Load knowledge bases from database
        global knowledge_bases
        loaded_kbs = await load_all_knowledge_bases_from_db()
        knowledge_bases.update(loaded_kbs)
    else:
        print("✗ Database connection failed - sessions will use memory only")

    # Test DigitalOcean connection
    try:
        client = DigitalOceanGradientClient()
        print("✓ DigitalOcean Gradient AI client initialized")
        print(f"  - Region: {client.region}")
        print(f"  - Model: {client.model_id}")
    except Exception as e:
        print(f"✗ DigitalOcean client initialization failed: {e}")

    yield

    # Shutdown
    print("\nShutting down application...")


# ============================================================================
# FastAPI Application
# ============================================================================

# Define security scheme for Swagger UI
security_scheme = HTTPBearer(auto_error=False)

app = FastAPI(
    title="Customer Support AI Agent (DigitalOcean Gradient AI)",
    description="AI-powered customer support agent using DigitalOcean Gradient AI Platform and Memori",
    version="2.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
    },
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve demo HTML page"""
    html_file = "static/demo.html"
    if os.path.exists(html_file):
        with open(html_file) as f:
            return f.read()
    return "<h1>Customer Support AI Agent (DigitalOcean Gradient AI)</h1><p>API is running. Use /docs for API documentation.</p>"


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = await test_db_connection()

    try:
        DigitalOceanGradientClient()
        do_status = "ok"
    except Exception as e:
        do_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": "connected" if db_status else "disconnected",
        "digitalocean": do_status,
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(sessions),
        "active_agents": len(agents),
        "knowledge_bases": len(knowledge_bases),
    }


@app.post("/session", response_model=SessionResponse)
async def create_session(request: SessionRequest):
    """Create a new chat session"""
    session_id = str(uuid.uuid4())

    session_info = SessionInfo(
        session_id=session_id,
        user_id=request.user_id,
        created_at=datetime.now(),
        last_activity=datetime.now(),
        website_url=request.website_url,
    )

    # Store in memory
    sessions[session_id] = session_info

    # Try to save to database
    await save_session_to_db(session_info)

    print(f"DEBUG: Created session {session_id} for user {request.user_id}")

    return SessionResponse(
        session_id=session_id,
        user_id=request.user_id,
        created_at=session_info.created_at.isoformat(),
        website_url=request.website_url,
    )


@app.post("/ask", response_model=QueryResponse)
async def ask(
    request: QueryRequest,
    x_domain_id: str | None = Header(None, alias="X-Domain-ID"),
):
    """
    Ask the AI agent a question using DigitalOcean's chat completions API

    This endpoint uses the agent's native chat completions endpoint directly,
    allowing access to additional features like retrieval info, functions, and guardrails.

    The agent endpoint format is: {agent_url}/api/v1/chat/completions
    """
    print(
        f"DEBUG: Ask received - session: {request.session_id}, question: {request.question[:50]}..."
    )

    # Get domain info from database using X-Domain-ID header
    if not x_domain_id:
        raise HTTPException(status_code=400, detail="Missing X-Domain-ID header")

    conn = await get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        domain_row = await conn.fetchrow(
            "SELECT id, domain_name FROM registered_domains WHERE id = $1",
            x_domain_id,
        )
        if not domain_row:
            raise HTTPException(status_code=401, detail="Unknown domain_id")

        domain_info = {
            "id": domain_row["id"],
            "domain_name": domain_row["domain_name"],
        }
    finally:
        await conn.close()

    # Validate session
    session_info = sessions.get(request.session_id)
    if not session_info:
        # Try to load from database
        session_info = await load_session_from_db(request.session_id)
        if session_info:
            sessions[request.session_id] = session_info
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    # Use domain_name from domain_info to ensure consistent agent lookup
    # This matches the website_key used during domain registration
    domain_name = domain_info.get("domain_name")
    website_url = f"https://{domain_name}" if domain_name else session_info.website_url
    website_key = get_website_key(website_url) if website_url else "default"

    print(f"DEBUG: Using website_url: {website_url}, website_key: {website_key}")

    # Get or create agent for this domain
    agent_info = await get_or_create_agent(website_url)

    # Check and update agent deployment status if URL is missing
    if not agent_info.get("agent_url"):
        print("DEBUG: Agent URL not available, checking deployment status...")
        agent_info = await check_and_update_agent_url(agent_info)

        # Update in memory cache
        agents[website_key] = agent_info

    # Get agent endpoint URL and access key
    agent_url = agent_info.get("agent_url")
    agent_access_key = agent_info.get("agent_access_key")
    deployment_status = agent_info.get("deployment_status", "UNKNOWN")

    print(
        f"DEBUG: Agent info - URL: {agent_url}, Has access key: {agent_access_key is not None}, Status: {deployment_status}"
    )

    if not agent_url:
        # Check deployment status to provide helpful message
        if deployment_status in ["STATUS_WAITING_FOR_DEPLOYMENT", "STATUS_DEPLOYING"]:
            raise HTTPException(
                status_code=503,
                detail="Your AI agent is currently being deployed. This usually takes 1-2 minutes. Please try again shortly.",
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Agent deployment URL not available. Status: {deployment_status}",
            )

    if not agent_access_key:
        print(
            f"ERROR: Agent access key not available for agent {agent_info.get('agent_uuid')}"
        )
        raise HTTPException(status_code=500, detail="Agent access key not available")

    # Use Memori for conversation with automatic memory integration
    # Get domain_id for process attribution
    domain_id = domain_info.get("domain_id", "unknown")

    try:
        # Get Memori instance
        memori = get_memori_instance()

        # Use Memori to handle the conversation with automatic context recall
        # Pass agent credentials to use DigitalOcean Gradient AI
        # Run synchronous chat method in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        memori_result = await loop.run_in_executor(
            None,
            lambda: memori.chat(
                question=request.question,
                user_id=request.user_id,
                domain_id=domain_id,
                agent_url=agent_url,
                agent_access_key=agent_access_key,
                system_prompt="You are a helpful customer support agent. Use the knowledge base context to answer questions accurately. If you don't know the answer, say so politely.",
            ),
        )

        if memori_result.get("success"):
            answer = memori_result.get("answer", "")
            print(f"DEBUG: Memori answered successfully {answer}")
            print(f"DEBUG: Memori response: {len(answer)} chars")

            # Save conversation to database
            await save_conversation_to_db(
                request.session_id, request.user_id, "user", request.question
            )
            await save_conversation_to_db(
                request.session_id, request.user_id, "assistant", answer
            )

            # Update session activity
            session_info.last_activity = datetime.now()

            return QueryResponse(
                answer=answer,
                sources=[],
                session_id=request.session_id,
            )
        else:
            # Memori returned error
            error_msg = memori_result.get("error", "Unknown error")
            print(f"ERROR: Memori call failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get response from AI agent: {error_msg}",
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        import traceback

        print(f"ERROR: Memori error: {e}")
        print(f"ERROR: Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question with AI agent: {str(e)}",
        ) from e


@app.post("/knowledge/upload/file", response_model=KnowledgeUploadResponse)
async def upload_file_to_knowledge(
    file: UploadFile,
    chunk_size: int = 1000,
    use_semantic: bool = False,
    custom_name: str | None = None,
    x_domain_id: str | None = Header(None, alias="X-Domain-ID"),
):
    """
    Upload a document (PDF, TXT, MD, JSON, CSV) to the knowledge base via DigitalOcean.

    The website URL is automatically determined from your API key.

    Supports the following file types:
    - PDF (.pdf)
    - Text (.txt)
    - Markdown (.md)
    - JSON (.json)
    - CSV (.csv)

    Note: This uses DigitalOcean's file upload API with presigned URLs.
    """
    try:
        # Get domain info from X-Domain-ID header
        if not x_domain_id:
            raise HTTPException(status_code=400, detail="Missing X-Domain-ID header")

        conn = await get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            domain_row = await conn.fetchrow(
                "SELECT domain_name FROM registered_domains WHERE id = $1",
                x_domain_id,
            )
            if not domain_row:
                raise HTTPException(status_code=401, detail="Unknown domain_id")

            website_url = f"https://{domain_row['domain_name']}"
        finally:
            await conn.close()

        website_key = get_website_key(website_url)

        print(f"DEBUG: upload_file - website_url: {website_url}")
        print(f"DEBUG: upload_file - filename: {file.filename}")

        # Get or create knowledge base for this website
        if website_key not in knowledge_bases:
            kb_uuid = await setup_knowledge_base(website_url)
        else:
            kb_uuid = knowledge_bases[website_key]

        # Create DigitalOcean client
        client = DigitalOceanGradientClient()

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Get presigned URL for file upload
        print("DEBUG: Requesting presigned URL for file upload")
        presigned_response = await client.create_presigned_url_for_file(
            knowledge_base_uuid=kb_uuid,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
        )

        presigned_url = presigned_response.get("url")
        stored_object_key = presigned_response.get("key")

        if not presigned_url or not stored_object_key:
            raise HTTPException(
                status_code=500, detail="Failed to get presigned URL from DigitalOcean"
            )

        # Upload file to presigned URL
        print("DEBUG: Uploading file to presigned URL")
        async with httpx.AsyncClient(timeout=60.0) as upload_client:
            upload_response = await upload_client.put(
                presigned_url,
                content=file_content,
                headers={
                    "Content-Type": file.content_type or "application/octet-stream"
                },
            )
            upload_response.raise_for_status()

        # Add file data source to knowledge base
        print("DEBUG: Adding file data source to knowledge base")
        data_source = await client.add_file_data_source(
            knowledge_base_uuid=kb_uuid,
            stored_object_key=stored_object_key,
            filename=custom_name or file.filename,
        )

        # Start indexing job
        print("DEBUG: Starting indexing job for uploaded file")
        job = await client.start_indexing_job(kb_uuid)

        return KnowledgeUploadResponse(
            success=True,
            message=f"Successfully uploaded {file.filename} to knowledge base",
            details={
                "filename": file.filename,
                "file_size": file_size,
                "knowledge_base_uuid": kb_uuid,
                "data_source_uuid": data_source.get("uuid"),
                "indexing_job_uuid": job.get("uuid"),
            },
        )

    except httpx.HTTPStatusError as e:
        print(
            f"ERROR: DigitalOcean API error: {e.response.status_code} - {e.response.text}"
        )
        return JSONResponse(
            status_code=500,
            content=KnowledgeUploadResponse(
                success=False,
                message=f"DigitalOcean API error: {e.response.status_code}",
            ).dict(),
        )
    except Exception as e:
        print(f"ERROR: Failed to upload file: {e}")
        return JSONResponse(
            status_code=500,
            content=KnowledgeUploadResponse(
                success=False, message=f"Error uploading file: {str(e)}"
            ).dict(),
        )


@app.post("/knowledge/upload/text", response_model=KnowledgeUploadResponse)
async def upload_text_to_knowledge(
    request: TextUploadRequest,
    x_domain_id: str | None = Header(None, alias="X-Domain-ID"),
):
    """
    Upload plain text content to the knowledge base via DigitalOcean.

    The website URL is automatically determined from your API key.

    Use this endpoint to directly add text content without a file.
    """
    try:
        # Get domain info from X-Domain-ID header
        if not x_domain_id:
            raise HTTPException(status_code=400, detail="Missing X-Domain-ID header")

        conn = await get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            domain_row = await conn.fetchrow(
                "SELECT domain_name FROM registered_domains WHERE id = $1",
                x_domain_id,
            )
            if not domain_row:
                raise HTTPException(status_code=401, detail="Unknown domain_id")

            website_url = f"https://{domain_row['domain_name']}"
        finally:
            await conn.close()

        website_key = get_website_key(website_url)

        print(f"DEBUG: upload_text - website_url: {website_url}")
        print(f"DEBUG: upload_text - document_name: {request.document_name}")

        # Get or create knowledge base for this website
        if website_key not in knowledge_bases:
            kb_uuid = await setup_knowledge_base(website_url)
        else:
            kb_uuid = knowledge_bases[website_key]

        # Create DigitalOcean client
        client = DigitalOceanGradientClient()

        # Convert text to bytes
        text_bytes = request.text_content.encode("utf-8")
        text_size = len(text_bytes)

        # Create a temporary filename
        temp_filename = f"{request.document_name}.txt"

        # Get presigned URL for text upload
        print("DEBUG: Requesting presigned URL for text upload")
        presigned_response = await client.create_presigned_url_for_file(
            knowledge_base_uuid=kb_uuid,
            filename=temp_filename,
            content_type="text/plain",
        )

        presigned_url = presigned_response.get("url")
        stored_object_key = presigned_response.get("key")

        if not presigned_url or not stored_object_key:
            raise HTTPException(
                status_code=500, detail="Failed to get presigned URL from DigitalOcean"
            )

        # Upload text to presigned URL
        print("DEBUG: Uploading text to presigned URL")
        async with httpx.AsyncClient(timeout=60.0) as upload_client:
            upload_response = await upload_client.put(
                presigned_url,
                content=text_bytes,
                headers={"Content-Type": "text/plain"},
            )
            upload_response.raise_for_status()

        # Add file data source to knowledge base
        print("DEBUG: Adding text data source to knowledge base")
        data_source = await client.add_file_data_source(
            knowledge_base_uuid=kb_uuid,
            stored_object_key=stored_object_key,
            filename=request.document_name,
        )

        # Start indexing job
        print("DEBUG: Starting indexing job for uploaded text")
        job = await client.start_indexing_job(kb_uuid)

        return KnowledgeUploadResponse(
            success=True,
            message=f"Successfully uploaded text content '{request.document_name}' to knowledge base",
            details={
                "document_name": request.document_name,
                "text_size": text_size,
                "knowledge_base_uuid": kb_uuid,
                "data_source_uuid": data_source.get("uuid"),
                "indexing_job_uuid": job.get("uuid"),
            },
        )

    except httpx.HTTPStatusError as e:
        print(
            f"ERROR: DigitalOcean API error: {e.response.status_code} - {e.response.text}"
        )
        return JSONResponse(
            status_code=500,
            content=KnowledgeUploadResponse(
                success=False,
                message=f"DigitalOcean API error: {e.response.status_code}",
            ).dict(),
        )
    except Exception as e:
        print(f"ERROR: Failed to upload text: {e}")
        return JSONResponse(
            status_code=500,
            content=KnowledgeUploadResponse(
                success=False, message=f"Error uploading text: {str(e)}"
            ).dict(),
        )


@app.post("/knowledge/upload/url", response_model=KnowledgeUploadResponse)
async def upload_url_to_knowledge(
    request: URLUploadRequest,
    x_domain_id: str | None = Header(None, alias="X-Domain-ID"),
):
    """
    Scrape and upload content from a URL to the knowledge base via DigitalOcean web crawler.
    """
    try:
        # Get domain info from X-Domain-ID header
        if not x_domain_id:
            raise HTTPException(status_code=400, detail="Missing X-Domain-ID header")

        conn = await get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            domain_row = await conn.fetchrow(
                "SELECT domain_name FROM registered_domains WHERE id = $1",
                x_domain_id,
            )
            if not domain_row:
                raise HTTPException(status_code=401, detail="Unknown domain_id")

            website_url = f"https://{domain_row['domain_name']}"
        finally:
            await conn.close()

        website_key = get_website_key(website_url)

        print(f"DEBUG: upload_url - website_url: {website_url}")
        print(f"DEBUG: upload_url - url_to_scrape: {request.url_to_scrape}")

        # Validate URL
        if not validators.url(request.url_to_scrape):
            raise HTTPException(status_code=400, detail="Invalid URL")

        # Get or create knowledge base for this website
        if website_key not in knowledge_bases:
            kb_uuid = await setup_knowledge_base(website_url)
        else:
            kb_uuid = knowledge_bases[website_key]

        # Create DigitalOcean client
        client = DigitalOceanGradientClient()

        # Add web crawler data source for the specified URL
        print(f"DEBUG: Adding web crawler data source for {request.url_to_scrape}")
        data_source = await client.add_web_crawler_data_source(
            knowledge_base_uuid=kb_uuid,
            url=request.url_to_scrape,
            max_pages=request.max_links,
            max_depth=request.max_depth,
        )

        # Start indexing job
        print("DEBUG: Starting indexing job for URL")
        job = await client.start_indexing_job(kb_uuid)
        job_uuid = job["uuid"]

        # Poll for completion (with timeout)
        max_wait = 300  # 5 minutes
        start_time = datetime.now()
        pages_indexed = 0

        while (datetime.now() - start_time).seconds < max_wait:
            job_status = await client.get_indexing_job_status(job_uuid)
            status = job_status.get("status", "UNKNOWN")

            if status == "COMPLETED":
                pages_indexed = int(job_status.get("total_items_indexed", 0))
                print(f"DEBUG: Indexing completed - {pages_indexed} items indexed")
                break
            elif status == "FAILED":
                return JSONResponse(
                    status_code=500,
                    content=KnowledgeUploadResponse(
                        success=False, message="Indexing job failed"
                    ).dict(),
                )

            await asyncio.sleep(5)

        return KnowledgeUploadResponse(
            success=True,
            message=f"Successfully scraped and indexed content from {request.url_to_scrape}",
            details={
                "url_to_scrape": request.url_to_scrape,
                "pages_indexed": pages_indexed,
                "max_depth": request.max_depth,
                "max_links": request.max_links,
                "knowledge_base_uuid": kb_uuid,
                "data_source_uuid": data_source.get("uuid"),
                "indexing_job_uuid": job_uuid,
            },
        )

    except httpx.HTTPStatusError as e:
        print(
            f"ERROR: DigitalOcean API error: {e.response.status_code} - {e.response.text}"
        )
        return JSONResponse(
            status_code=500,
            content=KnowledgeUploadResponse(
                success=False,
                message=f"DigitalOcean API error: {e.response.status_code}",
            ).dict(),
        )
    except Exception as e:
        print(f"ERROR: Failed to upload URL: {e}")
        return JSONResponse(
            status_code=500,
            content=KnowledgeUploadResponse(
                success=False, message=f"Error uploading URL: {str(e)}"
            ).dict(),
        )


@app.get("/knowledge/supported-types")
async def get_supported_file_types():
    """
    Get list of supported file types for knowledge upload.
    """
    return {
        "supported_types": [".pdf", ".txt", ".md", ".json", ".csv"],
        "descriptions": {
            ".pdf": "PDF documents",
            ".txt": "Plain text files",
            ".md": "Markdown documents",
            ".json": "JSON data files",
            ".csv": "CSV data files",
        },
        "additional_sources": ["url", "text"],
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information"""
    session_info = sessions.get(session_id)
    if not session_info:
        session_info = await load_session_from_db(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_info.session_id,
        "user_id": session_info.user_id,
        "created_at": session_info.created_at.isoformat(),
        "last_activity": session_info.last_activity.isoformat(),
        "website_url": session_info.website_url,
    }


@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    return {
        "sessions": [
            {
                "session_id": info.session_id,
                "user_id": info.user_id,
                "created_at": info.created_at.isoformat(),
                "last_activity": info.last_activity.isoformat(),
                "website_url": info.website_url,
            }
            for info in sessions.values()
        ],
        "total": len(sessions),
    }


@app.get("/conversations/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str):
    """Get conversation history for a session"""
    try:
        conn = await get_db_connection()
        if conn is None:
            raise HTTPException(status_code=503, detail="Database not available")

        try:
            rows = await conn.fetch(
                """
                SELECT id, session_id, user_id, role, content, created_at
                FROM conversation_history
                WHERE session_id = $1
                ORDER BY created_at ASC
                """,
                session_id,
            )

            messages = [
                ConversationMessage(
                    id=str(row["id"]),
                    session_id=str(row["session_id"]),
                    user_id=row["user_id"],
                    role=row["role"],
                    content=row["content"],
                    created_at=row["created_at"].isoformat(),
                )
                for row in rows
            ]

            user_id = rows[0]["user_id"] if rows else "unknown"

            return ConversationHistoryResponse(
                session_id=session_id,
                user_id=user_id,
                messages=messages,
                total_messages=len(messages),
            )

        finally:
            await conn.close()

    except Exception as e:
        print(f"ERROR: Failed to get conversation history: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve conversation history"
        ) from e


@app.post("/register-domain")
async def register_domain(
    request: DomainRegistrationRequest,
    background_tasks: BackgroundTasks,
):
    """Register a new domain.

    This endpoint creates a new domain registration and sets up an AI agent for it.
    The agent is created immediately but deployment happens in the background (takes 1-2 minutes).
    """
    try:
        domain_name = request.domain_name.strip().lower()
        if not domain_name:
            raise HTTPException(status_code=400, detail="domain_name cannot be empty")

        # Use the validators package for robust domain validation
        try:
            if not validators.domain(domain_name):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid domain_name format. Expected formats like 'www.example.com' or 'sub.example.co.uk'",
                )
        except Exception as e:
            # If validators raises for some unexpected reason, return a 400 to the caller
            raise HTTPException(
                status_code=400,
                detail=f"Invalid domain_name: {str(e)}",
            ) from e

        conn = await get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection failed")

        try:
            # Check if domain is already registered
            existing_domain_row = await conn.fetchrow(
                "SELECT id FROM registered_domains WHERE domain_name = $1", domain_name
            )

            if existing_domain_row:
                return JSONResponse(
                    status_code=409,
                    content={
                        "message": "Domain already registered",
                        "domain_id": str(existing_domain_row["id"]),
                    },
                )

            try:
                row = await conn.fetchrow(
                    "INSERT INTO registered_domains (domain_name, created_at) VALUES ($1, $2) RETURNING id",
                    domain_name,
                    datetime.now(),
                )

                domain_id = row["id"] if row else None

                # Create agent for the newly registered domain (without waiting for deployment)
                website_url = f"https://{domain_name}"
                print(f"DEBUG: Creating agent for registered domain: {website_url}")
                agent_info = None
                deployment_message = ""

                try:
                    # Create agent without waiting for deployment
                    website_key = get_website_key(website_url)
                    agent_info = await create_agent(
                        website_url=website_url,
                        wait_for_deployment=False,  # Don't wait, return immediately
                    )

                    # Store in memory and database
                    agents[website_key] = agent_info
                    await save_agent_to_db(website_key, agent_info)

                    # Start background task to poll for deployment completion
                    agent_uuid = agent_info.get("agent_uuid")
                    if agent_uuid:
                        background_tasks.add_task(
                            poll_agent_deployment_background,
                            agent_uuid,
                            website_key,
                            max_wait_seconds=180,
                        )
                        deployment_message = "Agent created successfully. Deployment will complete in 1-2 minutes and you can start using it."
                        print(
                            f"DEBUG: Agent created - UUID: {agent_uuid}. Background polling started."
                        )
                    else:
                        deployment_message = "Agent created but UUID not available"

                except Exception as agent_error:
                    deployment_message = f"Agent creation failed: {str(agent_error)}"
                    print(f"WARNING: Failed to create agent for domain: {agent_error}")
                    # Don't fail the registration if agent creation fails

                return {
                    "message": "Domain registered successfully",
                    "domain_id": domain_id,
                    "agent_created": agent_info is not None,
                    "agent_uuid": agent_info.get("agent_uuid") if agent_info else None,
                    "agent_deployment_status": agent_info.get("deployment_status")
                    if agent_info
                    else None,
                    "deployment_message": deployment_message,
                }
            except asyncpg.UniqueViolationError as e:
                # Check if it's a domain_name or api_key constraint violation
                if "domain_name" in str(e):
                    return JSONResponse(
                        status_code=409,
                        content={
                            "message": "Domain already registered",
                            "detail": str(e),
                        },
                    )
                elif "api_key" in str(e):
                    return JSONResponse(
                        status_code=409,
                        content={
                            "message": "API key already used for another domain",
                            "detail": str(e),
                        },
                    )
                else:
                    return JSONResponse(
                        status_code=409,
                        content={
                            "message": "Registration conflict",
                            "detail": str(e),
                        },
                    )
        finally:
            await conn.close()

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: Failed to register domain: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error registering domain: {str(e)}"
        ) from e


@app.get("/knowledge-bases")
async def list_knowledge_bases():
    """List all knowledge bases"""
    return {
        "knowledge_bases": [
            {"website_key": key, "kb_uuid": uuid_val}
            for key, uuid_val in knowledge_bases.items()
        ],
        "total": len(knowledge_bases),
    }


@app.get("/agents")
async def list_agents():
    """List all active agents (one per website)"""
    return {
        "agents": [
            {
                "website_key": website_key,
                "agent_uuid": info.get("agent_uuid"),
                "website_url": info.get("website_url"),
                "agent_url": info.get("agent_url"),
                "has_access_key": bool(info.get("agent_access_key")),
                "created_at": info.get("created_at").isoformat()
                if info.get("created_at")
                else None,
                "knowledge_base_uuids": info.get("knowledge_base_uuids", []),
            }
            for website_key, info in agents.items()
        ],
        "total": len(agents),
        "note": "One agent per website, shared across all sessions. Memori provides user/session context.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
