from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderSeed:
    name: str
    provider_type: str
    api_base_url: str = ""


@dataclass(frozen=True)
class ModelSeed:
    provider_name: str
    name: str
    description: str
    is_active: bool = True
    is_fine_tuned: bool = False
    is_macedonian_optimized: bool = False
    configuration: dict = field(default_factory=dict)


PROVIDER_SEEDS = (
    ProviderSeed(
        name="openai",
        provider_type="openai",
        api_base_url="https://api.openai.com/v1",
    ),
    ProviderSeed(
        name="anthropic",
        provider_type="anthropic",
        api_base_url="https://api.anthropic.com",
    ),
    ProviderSeed(
        name="google",
        provider_type="google",
        api_base_url="https://generativelanguage.googleapis.com",
    ),
    ProviderSeed(
        name="meta",
        provider_type="meta",
    ),
    ProviderSeed(
        name="hugging face",
        provider_type="hugging_face",
        api_base_url="https://router.huggingface.co/v1",
    ),
    ProviderSeed(
        name="other",
        provider_type="other",
    ),
)


MODEL_SEEDS = (
    ModelSeed(
        provider_name="openai",
        name="gpt-5.2",
        description="Latest flagship OpenAI general-purpose model for complex reasoning and agentic tasks.",
        configuration={
            "model_id": "gpt-5.2",
            "source": "official_openai_api",
            "family": "gpt-5",
        },
    ),
    ModelSeed(
        provider_name="openai",
        name="gpt-5-mini",
        description="Popular cost-optimized GPT-5 variant for balanced speed, cost, and capability.",
        configuration={
            "model_id": "gpt-5-mini",
            "source": "official_openai_api",
            "family": "gpt-5",
        },
    ),
    ModelSeed(
        provider_name="openai",
        name="gpt-4.1",
        description="Widely used high-capability non-reasoning OpenAI model.",
        configuration={
            "model_id": "gpt-4.1",
            "source": "official_openai_api",
            "family": "gpt-4.1",
        },
    ),
    ModelSeed(
        provider_name="anthropic",
        name="claude-opus-4.1",
        description="Anthropic's most capable Claude model for high-end reasoning and complex tasks.",
        configuration={
            "model_id": "claude-opus-4-1-20250805",
            "alias": "claude-opus-4-1",
            "source": "official_anthropic_api",
            "family": "claude-4",
        },
    ),
    ModelSeed(
        provider_name="anthropic",
        name="claude-sonnet-4",
        description="High-performance Claude model with strong quality-speed balance.",
        configuration={
            "model_id": "claude-sonnet-4-20250514",
            "alias": "claude-sonnet-4-0",
            "source": "official_anthropic_api",
            "family": "claude-4",
        },
    ),
    ModelSeed(
        provider_name="anthropic",
        name="claude-haiku-3.5",
        description="Fast Anthropic model suited for lower-latency general tasks.",
        configuration={
            "model_id": "claude-3-5-haiku-20241022",
            "alias": "claude-3-5-haiku-latest",
            "source": "official_anthropic_api",
            "family": "claude-3.5",
        },
    ),
    ModelSeed(
        provider_name="google",
        name="gemini-2.5-pro",
        description="State-of-the-art Google reasoning model for complex multimodal and code-heavy tasks.",
        configuration={
            "model_id": "gemini-2.5-pro",
            "source": "official_google_gemini_api",
            "family": "gemini-2.5",
            "channel": "stable",
        },
    ),
    ModelSeed(
        provider_name="google",
        name="gemini-2.5-flash",
        description="Google's balanced price-performance Gemini model for scale and low latency.",
        configuration={
            "model_id": "gemini-2.5-flash",
            "source": "official_google_gemini_api",
            "family": "gemini-2.5",
            "channel": "stable",
        },
    ),
    ModelSeed(
        provider_name="google",
        name="gemini-2.5-flash-lite",
        description="Fast, cost-efficient Gemini model for high-throughput workloads.",
        configuration={
            "model_id": "gemini-2.5-flash-lite",
            "source": "official_google_gemini_api",
            "family": "gemini-2.5",
            "channel": "stable",
        },
    ),
    ModelSeed(
        provider_name="meta",
        name="llama-4-maverick",
        description="Current Meta Llama 4 multimodal model optimized for higher capability workloads.",
        configuration={
            "model_id": "meta-llama/Llama-4-Maverick-17B-128E-Original",
            "source": "official_meta_hugging_face_org",
            "family": "llama-4",
        },
    ),
    ModelSeed(
        provider_name="meta",
        name="llama-4-scout",
        description="Current Meta Llama 4 multimodal model optimized for efficient deployment.",
        configuration={
            "model_id": "meta-llama/Llama-4-Scout-17B-16E-Original",
            "source": "official_meta_hugging_face_org",
            "family": "llama-4",
        },
    ),
    ModelSeed(
        provider_name="meta",
        name="llama-3.3-70b-instruct",
        description="Popular multilingual Meta instruction-tuned model still widely used in production.",
        configuration={
            "model_id": "meta-llama/Llama-3.3-70B-Instruct",
            "source": "official_meta_hugging_face_org",
            "family": "llama-3.3",
        },
    ),
)
