"""
DigitalOcean Gradient AI Platform API Client
Provides functions to interact with DigitalOcean Gradient AI API endpoints
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DigitalOceanGradientClient:
    """Client for DigitalOcean Gradient AI Platform API"""

    def __init__(self):
        self.token = os.getenv("DIGITALOCEAN_TOKEN")
        self.project_id = os.getenv("DIGITALOCEAN_PROJECT_ID")
        self.model_id = os.getenv("DIGITALOCEAN_AI_MODEL_ID")
        self.embedding_model_id = os.getenv("DIGITALOCEAN_EMBEDDING_MODEL_ID")
        # Use tor1 region - confirmed working based on existing agents
        self.region = os.getenv("DIGITALOCEAN_REGION", "tor1")
        self.base_url = "https://api.digitalocean.com/v2/gen-ai"

        if not all(
            [self.token, self.project_id, self.model_id, self.embedding_model_id]
        ):
            raise ValueError("Missing required DigitalOcean environment variables")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def create_knowledge_base(
        self,
        name: str,
        base_url: str,
        database_id: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a knowledge base on DigitalOcean with initial web crawler datasource

        Args:
            name: Name of the knowledge base
            base_url: Base URL for web crawler datasource
            database_id: Optional database ID to reuse (recommended to avoid creating many databases)
            description: Optional description
            tags: Optional list of tags for organization

        Returns:
            Knowledge base object with uuid and database_id
        """
        # Sanitize name to meet DigitalOcean requirements:
        # - Only lowercase letters, numbers, hyphens, underscores
        # - No spaces, dots, or special characters
        # - Start with lowercase letter or number
        import re

        # Replace special characters with hyphens
        sanitized_name = re.sub(r"[^a-z0-9_-]", "-", name.lower())
        # Remove consecutive hyphens
        sanitized_name = re.sub(r"-+", "-", sanitized_name)
        # Remove leading/trailing hyphens
        sanitized_name = sanitized_name.strip("-")
        # Ensure it starts with alphanumeric
        if sanitized_name and not sanitized_name[0].isalnum():
            sanitized_name = "kb-" + sanitized_name
        # Limit length to 63 characters (common DNS/k8s limit)
        sanitized_name = sanitized_name[:63]
        # Fallback if empty
        if not sanitized_name:
            sanitized_name = "knowledge-base"

        # Create KB with initial web crawler datasource
        # DigitalOcean requires datasources to be provided at creation time
        payload = {
            "name": sanitized_name,
            "embedding_model_uuid": self.embedding_model_id,
            "project_id": self.project_id,
            "region": self.region,
            "datasources": [
                {
                    "web_crawler_data_source": {
                        "base_url": base_url,
                        "crawling_option": "DOMAIN",
                        "embed_media": False,
                    }
                }
            ],
        }

        # Add database_id if provided (reuse existing database)
        if database_id:
            payload["database_id"] = database_id

        if tags:
            payload["tags"] = tags

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/knowledge_bases", headers=self.headers, json=payload
            )
            if response.status_code != 200:
                logger.error(
                    f"Knowledge base creation failed: {response.status_code} - {response.text}"
                )
            response.raise_for_status()
            result = response.json()
            logger.info(
                f"Created knowledge base: {result.get('knowledge_base', {}).get('uuid')}"
            )
            return result.get("knowledge_base", {})

    async def add_web_crawler_data_source(
        self,
        knowledge_base_uuid: str,
        url: str,
        max_pages: int = 100,
        max_depth: int = 3,
    ) -> dict[str, Any]:
        """
        Add a web crawler data source to a knowledge base

        Args:
            knowledge_base_uuid: UUID of the knowledge base
            url: Base URL to crawl
            max_pages: Maximum number of pages to crawl (default: 100)
            max_depth: Maximum crawl depth (default: 3)

        Returns:
            Data source object with uuid
        """
        payload = {
            "knowledge_base_uuid": knowledge_base_uuid,
            "web_crawler_data_source": {
                "base_url": url,
                "crawling_option": "PATH",
                "embed_media": True,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/knowledge_bases/{knowledge_base_uuid}/data_sources",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(
                f"Added web crawler data source: {result.get('knowledge_base_data_source', {}).get('uuid')}"
            )
            return result.get("knowledge_base_data_source", {})

    async def start_indexing_job(
        self, knowledge_base_uuid: str, data_source_uuids: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Start an indexing job for a knowledge base

        Args:
            knowledge_base_uuid: UUID of the knowledge base
            data_source_uuids: Optional list of data source UUIDs to index
                             (if None, all data sources will be indexed)

        Returns:
            Indexing job object with status
        """
        payload = {"knowledge_base_uuid": knowledge_base_uuid}

        if data_source_uuids:
            payload["data_source_uuids"] = data_source_uuids

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/indexing_jobs", headers=self.headers, json=payload
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Started indexing job: {result.get('job', {}).get('uuid')}")
            return result.get("job", {})

    async def get_indexing_job_status(self, job_uuid: str) -> dict[str, Any]:
        """
        Get the status of an indexing job

        Args:
            job_uuid: UUID of the indexing job

        Returns:
            Indexing job status information
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/indexing_jobs/{job_uuid}", headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            return result.get("job", {})

    async def create_agent(
        self,
        name: str,
        instruction: str,
        knowledge_base_uuids: list[str] | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        provide_citations: bool = True,
    ) -> dict[str, Any]:
        """
        Create an agent on DigitalOcean Gradient AI Platform

        Args:
            name: Agent name
            instruction: Agent instructions (system prompt)
            knowledge_base_uuids: List of knowledge base UUIDs to attach
            description: Optional agent description
            tags: Optional list of tags
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            provide_citations: Whether to provide citations from knowledge base

        Returns:
            Agent object with uuid and deployment URL
        """
        # Sanitize name to meet DigitalOcean requirements:
        # - Only lowercase letters, numbers, hyphens, underscores
        # - No spaces, dots, or special characters
        # - Start with lowercase letter or number
        import re

        # Replace special characters with hyphens
        sanitized_name = re.sub(r"[^a-z0-9_-]", "-", name.lower())
        # Remove consecutive hyphens
        sanitized_name = re.sub(r"-+", "-", sanitized_name)
        # Remove leading/trailing hyphens
        sanitized_name = sanitized_name.strip("-")
        # Ensure it starts with alphanumeric
        if sanitized_name and not sanitized_name[0].isalnum():
            sanitized_name = "agent-" + sanitized_name
        # Limit length to 63 characters
        sanitized_name = sanitized_name[:63]
        # Fallback if empty
        if not sanitized_name:
            sanitized_name = "support-agent"

        payload = {
            "name": sanitized_name,
            "instruction": instruction,
            "model_uuid": self.model_id,
            "project_id": self.project_id,
            "region": self.region,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "provide_citations": provide_citations,
            "conversation_logs_enabled": True,
        }

        if knowledge_base_uuids:
            payload["knowledge_base_uuid"] = knowledge_base_uuids

        if description:
            payload["description"] = description

        if tags:
            payload["tags"] = tags

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/agents", headers=self.headers, json=payload
            )
            if response.status_code != 200:
                logger.error(
                    f"Agent creation failed: {response.status_code} - {response.text}"
                )
            response.raise_for_status()
            result = response.json()
            agent = result.get("agent", {})
            logger.info(
                f"Created agent: {agent.get('uuid')} with URL: {agent.get('url')}"
            )
            return agent

    async def get_agent(self, agent_uuid: str) -> dict[str, Any]:
        """
        Retrieve an existing agent

        Args:
            agent_uuid: UUID of the agent

        Returns:
            Agent object
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/agents/{agent_uuid}", headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            return result.get("agent", {})

    async def wait_for_agent_deployment(
        self, agent_uuid: str, max_wait_seconds: int = 30, poll_interval: int = 5
    ) -> dict[str, Any]:
        """
        Wait for an agent deployment to complete

        Args:
            agent_uuid: UUID of the agent
            max_wait_seconds: Maximum time to wait in seconds (default: 30)
            poll_interval: Time between polls in seconds (default: 5)

        Returns:
            Agent object with deployment URL once ready

        Raises:
            TimeoutError: If deployment doesn't complete within max_wait_seconds
        """
        import asyncio

        start_time = asyncio.get_event_loop().time()

        while True:
            agent = await self.get_agent(agent_uuid)
            deployment = agent.get("deployment", {})
            status = deployment.get("status", "UNKNOWN")
            deployment_url = deployment.get("url")

            logger.info(f"Agent {agent_uuid} deployment status: {status}")

            # Check if deployment is complete
            if status == "STATUS_RUNNING" and deployment_url:
                logger.info(
                    f"Agent {agent_uuid} deployment complete with URL: {deployment_url}"
                )
                return agent

            # Check for failed status
            if status in ["STATUS_FAILED", "STATUS_CANCELED"]:
                logger.error(
                    f"Agent {agent_uuid} deployment failed with status: {status}"
                )
                raise Exception(f"Agent deployment failed with status: {status}")

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= max_wait_seconds:
                logger.warning(
                    f"Agent {agent_uuid} deployment timeout after {elapsed}s"
                )
                raise TimeoutError(
                    f"Agent deployment did not complete within {max_wait_seconds} seconds"
                )

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def update_agent(
        self,
        agent_uuid: str,
        instruction: str | None = None,
        name: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing agent

        Args:
            agent_uuid: UUID of the agent to update
            instruction: Updated instruction
            name: Updated name
            temperature: Updated temperature
            max_tokens: Updated max tokens

        Returns:
            Updated agent object
        """
        payload = {}

        if instruction is not None:
            payload["instruction"] = instruction
        if name is not None:
            payload["name"] = name
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{self.base_url}/agents/{agent_uuid}",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("agent", {})

    async def create_agent_access_key(
        self, agent_uuid: str, key_name: str = "default-key"
    ) -> dict[str, Any]:
        """
        Create an access key for an agent endpoint

        Args:
            agent_uuid: UUID of the agent
            key_name: Name for the access key

        Returns:
            Access key object with 'key' field containing the secret key
        """
        payload = {"name": key_name}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/agents/{agent_uuid}/api_keys",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Created access key for agent {agent_uuid}")
            # API returns: {"api_key_info": {"secret_key": "...", "name": "...", ...}}
            return result.get("api_key_info", {})

    async def attach_knowledge_base(
        self, agent_uuid: str, knowledge_base_uuid: str
    ) -> dict[str, Any]:
        """
        Attach a knowledge base to an agent

        Args:
            agent_uuid: UUID of the agent
            knowledge_base_uuid: UUID of the knowledge base

        Returns:
            Updated agent object
        """
        payload = {"agent_uuid": agent_uuid, "knowledge_base_uuid": knowledge_base_uuid}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/agents/{agent_uuid}/knowledge_bases/{knowledge_base_uuid}",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("agent", {})

    async def list_knowledge_bases(self) -> list[dict[str, Any]]:
        """
        List all knowledge bases

        Returns:
            List of knowledge base objects
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/knowledge_bases", headers=self.headers
            )
            response.raise_for_status()
            result = response.json()
            return result.get("knowledge_bases", [])

    async def list_agents(self) -> list[dict[str, Any]]:
        """
        List all agents

        Returns:
            List of agent objects
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/agents", headers=self.headers)
            response.raise_for_status()
            result = response.json()
            return result.get("agents", [])

    async def delete_agent(self, agent_uuid: str) -> dict[str, Any]:
        """
        Delete an agent

        Args:
            agent_uuid: UUID of the agent to delete

        Returns:
            Deletion confirmation
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/agents/{agent_uuid}", headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def delete_knowledge_base(self, knowledge_base_uuid: str) -> dict[str, Any]:
        """
        Delete a knowledge base

        Args:
            knowledge_base_uuid: UUID of the knowledge base to delete

        Returns:
            Deletion confirmation
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/knowledge_bases/{knowledge_base_uuid}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()

    async def create_presigned_url_for_file(
        self,
        knowledge_base_uuid: str,
        filename: str,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        """
        Get a presigned URL for file upload

        Args:
            knowledge_base_uuid: UUID of the knowledge base
            filename: Name of the file to upload
            content_type: MIME type of the file

        Returns:
            Presigned URL response with url and key
        """
        payload = {
            "knowledge_base_uuid": knowledge_base_uuid,
            "filename": filename,
            "content_type": content_type,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/knowledge_bases/data_sources/file_upload_presigned_urls",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Created presigned URL for file: {filename}")
            return result

    async def add_file_data_source(
        self,
        knowledge_base_uuid: str,
        stored_object_key: str,
        filename: str,
    ) -> dict[str, Any]:
        """
        Add a file data source to knowledge base after upload

        Args:
            knowledge_base_uuid: UUID of the knowledge base
            stored_object_key: Object key returned from presigned URL request
            filename: Display name for the file

        Returns:
            Data source object with uuid
        """
        payload = {
            "knowledge_base_uuid": knowledge_base_uuid,
            "file_upload_data_source": {
                "stored_object_key": stored_object_key,
                "filename": filename,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/knowledge_bases/{knowledge_base_uuid}/data_sources",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(
                f"Added file data source: {result.get('knowledge_base_data_source', {}).get('uuid')}"
            )
            return result.get("knowledge_base_data_source", {})
