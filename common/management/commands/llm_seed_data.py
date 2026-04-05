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
        description="OpenAI develops widely used general-purpose language models for chat, reasoning, coding, and agentic workflows.",
        api_base_url="https://api.openai.com/v1",
    ),
    ProviderSeed(
        name="anthropic",
        display_name="Anthropic",
        description="Anthropic builds the Claude family of language models with a strong focus on reasoning quality, safety, and assistant behavior.",
        api_base_url="https://api.anthropic.com",
    ),
    ProviderSeed(
        name="google",
        display_name="Google",
        description="Google develops the Gemini family of models for multimodal understanding, reasoning, and fast interactive assistant use cases.",
        api_base_url="https://generativelanguage.googleapis.com",
    ),
    ProviderSeed(
        name="finki",
        display_name="FINKI",
        description="FINKI develops Macedonian-focused Vezilka models intended for local language understanding, generation, and evaluation.",
        api_base_url="https://pna.finki.ukim.mk/v1",
    )
)

MODEL_SEEDS = (

    ModelSeed(
        provider_name="openai",
        name="gpt-5.4",
        external_model_id="gpt-5.4",
        description="Flagship OpenAI GPT-5.4 model focused on strong reasoning, agentic workflows, and high-end coding performance.",
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
        description="Smaller GPT-5.4 variant that balances quality, speed, and cost for coding, assistants, and multi-step tasks.",
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
        description="Lightweight GPT-5.4-class model optimized for very fast, low-cost, high-volume generation workloads.",
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
        description="High-capability OpenAI model well suited for general-purpose chat, analysis, and instruction following.",
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
        description="Compact GPT-4.1 model designed for lower latency and lower-cost usage while keeping solid overall quality.",
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
        description="Fast and inexpensive GPT-4.1-class variant for simple prompts, short generations, and large request volume.",
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
        description="Most capable Claude 4.6 model for deep reasoning, complex coding tasks, and high-judgment agent behavior.",
        supports_temperature=True,
        supports_top_p=True,
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
        description="Balanced Claude 4.6 model that combines strong quality with better speed and efficiency than Opus.",
        supports_temperature=True,
        supports_top_p=True,
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
        description="Fast Claude model intended for low-latency use cases while still offering strong general intelligence.",
        supports_temperature=True,
        supports_top_p=True,
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
        description="High-end Gemini preview model geared toward stronger reasoning, software engineering, and more reliable multi-step work.",
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
        description="Fast Gemini preview model aimed at responsive multimodal, agentic, and interactive assistant experiences.",
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
        description="Most cost-efficient Gemini preview option for lightweight prompts, frequent requests, and latency-sensitive workloads.",
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
        description="Instruction-tuned Macedonian Vezilka model from FINKI in fp16 format, suitable for general chat and evaluation.",
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
        description="Instruction-tuned Macedonian Vezilka model from FINKI in fp32 format, offering maximum precision in this seeded set.",
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
        description="Quantized Macedonian Vezilka variant from FINKI using q4_K_M for lower memory usage and cheaper inference.",
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
        description="Quantized Macedonian Vezilka variant from FINKI using q8_0 to trade some efficiency for higher output fidelity.",
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
