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
        name="meta",
        display_name="Meta",
        description="Meta Llama models available for arena comparisons.",
    ),
    ProviderSeed(
        name="hugging face",
        display_name="Hugging Face",
        description="Models and routing exposed through the Hugging Face platform.",
        api_base_url="https://router.huggingface.co/v1",
    ),
    ProviderSeed(
        name="finki",
        display_name="FINKI",
        description="Macedonian models served through the FINKI OpenAI-compatible endpoint.",
        api_base_url="https://pna.finki.ukim.mk/v1",
    ),
    ProviderSeed(
        name="other",
        display_name="Other",
        description="Fallback provider bucket for uncategorized external model sources.",
    ),
)


MODEL_SEEDS = (
    ModelSeed(
        provider_name="openai",
        name="gpt-5.2",
        external_model_id="gpt-5.2",
        description="Latest flagship OpenAI general-purpose model for complex reasoning and agentic tasks.",
        configuration={
            "source": "official_openai_api",
            "family": "gpt-5",
        },
    ),
    ModelSeed(
        provider_name="openai",
        name="gpt-5-mini",
        external_model_id="gpt-5-mini",
        description="Popular cost-optimized GPT-5 variant for balanced speed, cost, and capability.",
        configuration={
            "source": "official_openai_api",
            "family": "gpt-5",
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
        provider_name="anthropic",
        name="claude-opus-4.1",
        external_model_id="claude-opus-4-1-20250805",
        description="Anthropic's most capable Claude model for high-end reasoning and complex tasks.",
        configuration={
            "alias": "claude-opus-4-1",
            "source": "official_anthropic_api",
            "family": "claude-4",
        },
    ),
    ModelSeed(
        provider_name="anthropic",
        name="claude-sonnet-4",
        external_model_id="claude-sonnet-4-20250514",
        description="High-performance Claude model with strong quality-speed balance.",
        configuration={
            "alias": "claude-sonnet-4-0",
            "source": "official_anthropic_api",
            "family": "claude-4",
        },
    ),
    ModelSeed(
        provider_name="anthropic",
        name="claude-haiku-3.5",
        external_model_id="claude-3-5-haiku-20241022",
        description="Fast Anthropic model suited for lower-latency general tasks.",
        configuration={
            "alias": "claude-3-5-haiku-latest",
            "source": "official_anthropic_api",
            "family": "claude-3.5",
        },
    ),
    ModelSeed(
        provider_name="google",
        name="gemini-2.5-pro",
        external_model_id="gemini-2.5-pro",
        description="State-of-the-art Google reasoning model for complex multimodal and code-heavy tasks.",
        configuration={
            "source": "official_google_gemini_api",
            "family": "gemini-2.5",
            "channel": "stable",
        },
    ),
    ModelSeed(
        provider_name="google",
        name="gemini-2.5-flash",
        external_model_id="gemini-2.5-flash",
        description="Google's balanced price-performance Gemini model for scale and low latency.",
        configuration={
            "source": "official_google_gemini_api",
            "family": "gemini-2.5",
            "channel": "stable",
        },
    ),
    ModelSeed(
        provider_name="google",
        name="gemini-2.5-flash-lite",
        external_model_id="gemini-2.5-flash-lite",
        description="Fast, cost-efficient Gemini model for high-throughput workloads.",
        configuration={
            "source": "official_google_gemini_api",
            "family": "gemini-2.5",
            "channel": "stable",
        },
    ),
    ModelSeed(
        provider_name="meta",
        name="llama-4-maverick",
        external_model_id="meta-llama/Llama-4-Maverick-17B-128E-Original",
        description="Current Meta Llama 4 multimodal model optimized for higher capability workloads.",
        configuration={
            "source": "official_meta_hugging_face_org",
            "family": "llama-4",
        },
    ),
    ModelSeed(
        provider_name="meta",
        name="llama-4-scout",
        external_model_id="meta-llama/Llama-4-Scout-17B-16E-Original",
        description="Current Meta Llama 4 multimodal model optimized for efficient deployment.",
        configuration={
            "source": "official_meta_hugging_face_org",
            "family": "llama-4",
        },
    ),
    ModelSeed(
        provider_name="meta",
        name="llama-3.3-70b-instruct",
        external_model_id="meta-llama/Llama-3.3-70B-Instruct",
        description="Popular multilingual Meta instruction-tuned model still widely used in production.",
        configuration={
            "source": "official_meta_hugging_face_org",
            "family": "llama-3.3",
        },
    ),
    ModelSeed(
        provider_name="finki",
        name="vezilka-4b-it-fp16",
        external_model_id="finki_ukim/vezilka:4b-it-fp16",
        description="Macedonian instruction-tuned FINKI model exposed through the FINKI OpenAI-compatible endpoint.",
        is_macedonian_optimized=True,
        configuration={
            "source": "official_finki_endpoint",
            "family": "vezilka",
        },
    ),
)
