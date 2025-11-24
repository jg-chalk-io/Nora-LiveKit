"""Configuration management for the agent system."""

import logging
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    model_config = ConfigDict(extra="allow")

    model: str = Field(..., description="Model identifier")
    timeout: float = Field(30.0, description="Request timeout in seconds")
    api_key: str | None = Field(None, description="API key (optional, uses env var)")


class ProvidersConfig(BaseModel):
    """Configuration for all providers."""

    fallback_chain: list[str] = Field(
        ..., description="Provider names in fallback order"
    )
    providers: dict[str, ProviderConfig] = Field(..., description="Provider configs")


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    model_config = ConfigDict(extra="allow")

    system_prompt: str = Field(..., description="System prompt for the agent")
    transfer_keywords: list[str] = Field(
        default_factory=list, description="Keywords triggering transfer"
    )


class PromptConfig(BaseModel):
    """Configuration for agent prompts."""

    agents: dict[str, AgentConfig] = Field(..., description="Agent configurations")


class AppConfig(BaseModel):
    """Application configuration."""

    model_config = ConfigDict(extra="allow")

    providers: ProvidersConfig = Field(..., description="Provider configuration")
    prompts: PromptConfig = Field(..., description="Agent prompt configuration")
    debug: bool = Field(False, description="Debug mode flag")


def load_config(config_dir: str | Path = "config") -> AppConfig:
    """Load configuration from YAML files.

    Args:
        config_dir: Directory containing config YAML files

    Returns:
        Loaded configuration

    Raises:
        FileNotFoundError: If config files not found
        ValueError: If configuration is invalid
    """
    config_dir = Path(config_dir)

    # Load providers config
    providers_path = config_dir / "providers.yaml"
    if not providers_path.exists():
        raise FileNotFoundError(f"Providers config not found: {providers_path}")

    with open(providers_path, "r") as f:
        providers_data = yaml.safe_load(f)
    logger.info(f"Loaded providers config from {providers_path}")

    # Load prompts config
    prompts_path = config_dir / "prompts.yaml"
    if not prompts_path.exists():
        raise FileNotFoundError(f"Prompts config not found: {prompts_path}")

    with open(prompts_path, "r") as f:
        prompts_data = yaml.safe_load(f)
    logger.info(f"Loaded prompts config from {prompts_path}")

    # Validate and create config objects
    try:
        providers_config = ProvidersConfig(**providers_data)
        prompts_config = PromptConfig(**prompts_data)
        app_config = AppConfig(providers=providers_config, prompts=prompts_config)
        logger.info("Configuration validated successfully")
        return app_config
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {str(e)}")


def get_provider_config(
    app_config: AppConfig, provider_name: str
) -> ProviderConfig:
    """Get configuration for a specific provider.

    Args:
        app_config: Application configuration
        provider_name: Provider name

    Returns:
        Provider configuration

    Raises:
        KeyError: If provider not found
    """
    if provider_name not in app_config.providers.providers:
        raise KeyError(f"Provider not found: {provider_name}")
    return app_config.providers.providers[provider_name]


def get_agent_config(app_config: AppConfig, agent_name: str) -> AgentConfig:
    """Get configuration for a specific agent.

    Args:
        app_config: Application configuration
        agent_name: Agent name

    Returns:
        Agent configuration

    Raises:
        KeyError: If agent not found
    """
    if agent_name not in app_config.prompts.agents:
        raise KeyError(f"Agent not found: {agent_name}")
    return app_config.prompts.agents[agent_name]
