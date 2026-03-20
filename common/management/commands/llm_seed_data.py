from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderSeed:
    name: str
    display_name: str
    description: str = ""
    api_base_url: str = ""


@dataclass(frozen=True)
class ModelSeed:
    provider_name: str
    name: str
    external_model_id: str
    description: str
    is_active: bool = True
    is_fine_tuned: bool = False
    is_macedonian_optimized: bool = False
    configuration: dict = field(default_factory=dict)


PROVIDER_SEEDS = (
    ProviderSeed(
        name="openai",
        display_name="OpenAI",
        description="OpenAI foundation models served through the OpenAI API.",
        api_base_url="https://api.openai.com/v1",
    ),
    ProviderSeed(
        name="anthropic",
        display_name="Anthropic",
        description="Anthropic Claude models served through the Anthropic API.",
        api_base_url="https://api.anthropic.com",
    ),
    ProviderSeed(
        name="google",
        display_name="Google",
        description="Google Gemini models served through the Google Generative AI API.",
        api_base_url="https://generativelanguage.googleapis.com",
    ),
    ProviderSeed(
        name="finki",
        display_name="FINKI",
        description="Macedonian models served through the FINKI OpenAI-compatible endpoint.",
        api_base_url="https://pna.finki.ukim.mk/v1",
    )
)

MODEL_SEEDS = (

    ModelSeed(
        provider_name="openai",
        name="gpt-5.4",
        external_model_id="gpt-5.4",
        description="Frontier GPT-5.4 model for agentic, coding, and professional workflows.",
        configuration={
            "source": "official_openai_api",
            "family": "gpt-5.4",
        },
    ),
    ModelSeed(
        provider_name="openai",
        name="gpt-5.4-mini",
        external_model_id="gpt-5.4-mini",
        description="Strong GPT-5.4-class mini model for coding, computer use, and subagent tasks.",
        configuration={
            "source": "official_openai_api",
            "family": "gpt-5.4",
        },
    ),
    ModelSeed(
        provider_name="openai",
        name="gpt-5.4-nano",
        external_model_id="gpt-5.4-nano",
        description="Cheapest GPT-5.4-class model for simple, high-volume workloads.",
        configuration={
            "source": "official_openai_api",
            "family": "gpt-5.4",
        },
    ),
    ModelSeed(
        provider_name="openai",
        name="gpt-4.1",
        external_model_id="gpt-4.1",
        description="Widely used high-capability non-reasoning OpenAI model.",
        configuration={
            "source": "official_openai_api",
            "family": "gpt-4.1",
        },
    ),
    ModelSeed(
        provider_name="openai",
        name="gpt-4.1-mini",
        external_model_id="gpt-4.1-mini",
        description="Smaller GPT-4.1 variant optimized for lower cost and latency.",
        configuration={
            "source": "official_openai_api",
            "family": "gpt-4.1",
        },
    ),
    ModelSeed(
        provider_name="openai",
        name="gpt-4.1-nano",
        external_model_id="gpt-4.1-nano",
        description="Fastest GPT-4.1-class variant for lightweight, high-volume tasks.",
        configuration={
            "source": "official_openai_api",
            "family": "gpt-4.1",
        },
    ),
    ModelSeed(
        provider_name="anthropic",
        name="claude-opus-4.6",
        external_model_id="claude-opus-4-6",
        description="Anthropic's most capable Claude model for agents, coding, and high-end reasoning.",
        configuration={
            "alias": "claude-opus-4-6",
            "source": "official_anthropic_api",
            "family": "claude-4.6",
        },
    ),
    ModelSeed(
        provider_name="anthropic",
        name="claude-sonnet-4.6",
        external_model_id="claude-sonnet-4-6",
        description="Claude model with the best combination of speed and intelligence.",
        configuration={
            "alias": "claude-sonnet-4-6",
            "source": "official_anthropic_api",
            "family": "claude-4.6",
        },
    ),
    ModelSeed(
        provider_name="anthropic",
        name="claude-haiku-4.5",
        external_model_id="claude-haiku-4-5-20251001",
        description="Fast Claude model with near-frontier intelligence.",
        configuration={
            "alias": "claude-haiku-4-5",
            "source": "official_anthropic_api",
            "family": "claude-4.5",
        },
    ),
    ModelSeed(
        provider_name="google",
        name="gemini-3.1-pro-preview",
        external_model_id="gemini-3.1-pro-preview",
        description="Refined Gemini Pro preview model for stronger thinking, token efficiency, and software engineering workflows.",
        configuration={
            "source": "official_google_gemini_api",
            "family": "gemini-3.1",
            "channel": "preview",
        },
    ),
    ModelSeed(
        provider_name="google",
        name="gemini-3-flash-preview",
        external_model_id="gemini-3-flash-preview",
        description="Google's most powerful agentic and multimodal Flash preview model.",
        configuration={
            "source": "official_google_gemini_api",
            "family": "gemini-3",
            "channel": "preview",
        },
    ),
    ModelSeed(
        provider_name="google",
        name="gemini-3.1-flash-lite-preview",
        external_model_id="gemini-3.1-flash-lite-preview",
        description="Google's most cost-efficient Gemini preview model for high-frequency lightweight tasks.",
        configuration={
            "source": "official_google_gemini_api",
            "family": "gemini-3.1",
            "channel": "preview",
        },
    ),
    ModelSeed(
        provider_name="finki",
        name="vezilka-4b-it-fp16",
        external_model_id="finki_ukim/vezilka:4b-it-fp16",
        description="Macedonian instruction-tuned FINKI model exposed through the FINKI OpenAI-compatible endpoint.",
        is_macedonian_optimized=True,
        is_fine_tuned=True,
        configuration={
            "source": "official_finki_endpoint",
            "family": "vezilka",
        },
    ),
)
