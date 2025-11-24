"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest

from src.config import (
    load_config,
    get_provider_config,
    get_agent_config,
    AppConfig,
    ProviderConfig,
    AgentConfig,
)


class TestProviderConfig:
    """Test ProviderConfig validation."""

    def test_provider_config_creation(self):
        """Test creating provider config."""
        config = ProviderConfig(
            model="gpt-4-turbo",
            timeout=30.0,
        )
        assert config.model == "gpt-4-turbo"
        assert config.timeout == 30.0

    def test_provider_config_with_api_key(self):
        """Test provider config with API key."""
        config = ProviderConfig(
            model="gpt-4",
            api_key="test-key",
        )
        assert config.api_key == "test-key"


class TestAgentConfig:
    """Test AgentConfig validation."""

    def test_agent_config_creation(self):
        """Test creating agent config."""
        config = AgentConfig(
            system_prompt="You are helpful",
            transfer_keywords=["schedule", "appointment"],
        )
        assert config.system_prompt == "You are helpful"
        assert len(config.transfer_keywords) == 2


class TestConfigLoading:
    """Test configuration loading from YAML."""

    def test_load_config_success(self):
        """Test loading valid configuration."""
        # Use project config directory
        config = load_config(Path("/Users/jeremygreven/git-projects/Nora-LiveKit/config"))
        assert config is not None
        assert config.providers is not None
        assert config.prompts is not None

    def test_load_config_missing_providers(self):
        """Test loading config with missing providers file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only prompts.yaml
            config_dir = Path(tmpdir)
            prompts_file = config_dir / "prompts.yaml"
            prompts_file.write_text("""
agents:
  greeter:
    system_prompt: "Test prompt"
""")

            with pytest.raises(FileNotFoundError):
                load_config(config_dir)

    def test_load_config_missing_prompts(self):
        """Test loading config with missing prompts file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only providers.yaml
            config_dir = Path(tmpdir)
            providers_file = config_dir / "providers.yaml"
            providers_file.write_text("""
fallback_chain:
  - openai
providers:
  openai:
    model: gpt-4
""")

            with pytest.raises(FileNotFoundError):
                load_config(config_dir)

    def test_get_provider_config(self):
        """Test getting provider config."""
        config = load_config(Path("/Users/jeremygreven/git-projects/Nora-LiveKit/config"))
        provider_config = get_provider_config(config, "openai")
        assert provider_config.model == "gpt-4-turbo"

    def test_get_provider_config_not_found(self):
        """Test getting non-existent provider."""
        config = load_config(Path("/Users/jeremygreven/git-projects/Nora-LiveKit/config"))
        with pytest.raises(KeyError):
            get_provider_config(config, "nonexistent")

    def test_get_agent_config(self):
        """Test getting agent config."""
        config = load_config(Path("/Users/jeremygreven/git-projects/Nora-LiveKit/config"))
        agent_config = get_agent_config(config, "greeter")
        assert agent_config.system_prompt is not None

    def test_get_agent_config_not_found(self):
        """Test getting non-existent agent."""
        config = load_config(Path("/Users/jeremygreven/git-projects/Nora-LiveKit/config"))
        with pytest.raises(KeyError):
            get_agent_config(config, "nonexistent")

    def test_fallback_chain_order(self):
        """Test fallback chain is in correct order."""
        config = load_config(Path("/Users/jeremygreven/git-projects/Nora-LiveKit/config"))
        fallback = config.providers.fallback_chain
        assert fallback[0] == "openai"
        assert fallback[1] == "anthropic"
        assert fallback[2] == "google"
        assert fallback[3] == "ollama"

    def test_all_providers_configured(self):
        """Test all providers are configured."""
        config = load_config(Path("/Users/jeremygreven/git-projects/Nora-LiveKit/config"))
        providers = config.providers.providers

        expected_providers = ["openai", "anthropic", "google", "ollama"]
        for provider in expected_providers:
            assert provider in providers

    def test_all_agents_configured(self):
        """Test all agents are configured."""
        config = load_config(Path("/Users/jeremygreven/git-projects/Nora-LiveKit/config"))
        agents = config.prompts.agents

        expected_agents = ["greeter", "triage", "support"]
        for agent in expected_agents:
            assert agent in agents
