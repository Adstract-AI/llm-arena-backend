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
    is_active: bool = False
    is_fine_tuned: bool = False
    is_macedonian_optimized: bool = False
    supports_temperature: bool = False
    supports_top_p: bool = False
    supports_top_k: bool = False
    supports_frequency_penalty: bool = False
    supports_presence_penalty: bool = False
    configuration: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ParameterSamplingSpecSeed:
    parameter_name: str
    value_type: str
    minimum_value: str
    maximum_value: str
    uniform_min: str
    uniform_max: str
    normal_mean: str
    normal_std: str
    beta_alpha: str
    beta_beta: str


@dataclass(frozen=True)
class AgentPromptSeed:
    agent_type: str
    name: str
    system_prompt: str
    is_active: bool = True


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
        supports_temperature=True,
        supports_top_p=True,
        supports_frequency_penalty=True,
        supports_presence_penalty=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_frequency_penalty=True,
        supports_presence_penalty=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_frequency_penalty=True,
        supports_presence_penalty=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_frequency_penalty=True,
        supports_presence_penalty=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_frequency_penalty=True,
        supports_presence_penalty=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_frequency_penalty=True,
        supports_presence_penalty=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_top_k=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_top_k=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_top_k=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_top_k=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_top_k=True,
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
        supports_temperature=True,
        supports_top_p=True,
        supports_top_k=True,
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
        is_active=True,
        configuration={
            "source": "official_finki_endpoint",
            "family": "vezilka",
        },
    ),
    ModelSeed(
        provider_name="finki",
        name="vezilka-4b-it-fp32",
        external_model_id="finki_ukim/vezilka:4b-it-fp32",
        description="Macedonian FINKI Vezilka model in fp32 format with 128K context.",
        is_macedonian_optimized=True,
        is_fine_tuned=True,
        is_active=True,
        configuration={
            "source": "official_finki_endpoint",
            "family": "vezilka",
        },
    ),
    ModelSeed(
        provider_name="finki",
        name="vezilka-4b-it-q4-k-m",
        external_model_id="finki_ukim/vezilka:4b-it-q4_K_M",
        description="Macedonian FINKI Vezilka quantized q4_K_M model with 128K context.",
        is_macedonian_optimized=True,
        is_fine_tuned=True,
        is_active=True,
        configuration={
            "source": "official_finki_endpoint",
            "family": "vezilka",
        },
    ),
    ModelSeed(
        provider_name="finki",
        name="vezilka-4b-it-q8-0",
        external_model_id="finki_ukim/vezilka:4b-it-q8_0",
        description="Macedonian FINKI Vezilka quantized q8_0 model with 128K context.",
        is_macedonian_optimized=True,
        is_fine_tuned=True,
        is_active=True,
        configuration={
            "source": "official_finki_endpoint",
            "family": "vezilka",
        },
    ),
)

PARAMETER_SAMPLING_SPEC_SEEDS = (
    ParameterSamplingSpecSeed(
        parameter_name="temperature",
        value_type="float",
        minimum_value="0.0000",
        maximum_value="2.0000",
        uniform_min="0.2000",
        uniform_max="1.2000",
        normal_mean="0.8000",
        normal_std="0.2500",
        beta_alpha="2.0000",
        beta_beta="2.0000",
    ),
    ParameterSamplingSpecSeed(
        parameter_name="top_p",
        value_type="float",
        minimum_value="0.1000",
        maximum_value="1.0000",
        uniform_min="0.7000",
        uniform_max="1.0000",
        normal_mean="0.9000",
        normal_std="0.0800",
        beta_alpha="5.0000",
        beta_beta="2.0000",
    ),
    ParameterSamplingSpecSeed(
        parameter_name="top_k",
        value_type="int",
        minimum_value="1.0000",
        maximum_value="100.0000",
        uniform_min="20.0000",
        uniform_max="100.0000",
        normal_mean="50.0000",
        normal_std="20.0000",
        beta_alpha="2.0000",
        beta_beta="5.0000",
    ),
    ParameterSamplingSpecSeed(
        parameter_name="frequency_penalty",
        value_type="float",
        minimum_value="-2.0000",
        maximum_value="2.0000",
        uniform_min="-0.5000",
        uniform_max="1.0000",
        normal_mean="0.2500",
        normal_std="0.5000",
        beta_alpha="2.0000",
        beta_beta="2.0000",
    ),
    ParameterSamplingSpecSeed(
        parameter_name="presence_penalty",
        value_type="float",
        minimum_value="-2.0000",
        maximum_value="2.0000",
        uniform_min="-0.5000",
        uniform_max="1.0000",
        normal_mean="0.2500",
        normal_std="0.5000",
        beta_alpha="2.0000",
        beta_beta="2.0000",
    ),
)

AGENT_PROMPT_SEEDS = (
    AgentPromptSeed(
        agent_type="judge",
        name="Default Judge Prompt",
        system_prompt=(
            "You are an impartial judge for a blind LLM arena.\n"
            "You will receive a full multi-turn conversation where the user messages are shared "
            "and the two anonymous assistants are labeled only as A and B.\n"
            "Evaluate which assistant produced the better overall conversation outcome across all turns.\n"
            "Judge based on helpfulness, correctness, completeness, consistency, clarity, and instruction following.\n"
            "Do not favor verbosity by default.\n"
            "Do not mention model identities or speculate about them.\n"
            "Return strict JSON with exactly two keys:\n"
            '1. "choice": one of "A", "B", or "tie"\n'
            '2. "reasoning": a short explanation of the decision\n'
            "Return only the JSON object and nothing else."
        ),
        is_active=True,
    ),
)
