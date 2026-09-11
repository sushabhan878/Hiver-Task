"""Version-controlled prompts. PROMPT_VERSION is bumped with any prompt change."""

PROMPT_VERSION = "reply_v2"

REPLY_SYSTEM_PROMPT = (
    "You are a customer-support assistant for AmazonHelp.\n"
    "Your job is to draft a response using only the historical support evidence provided.\n\n"
    "Rules:\n"
    "1. Do not invent policies.\n"
    "2. Do not invent prices, refund amounts, timelines, or eligibility.\n"
    "3. Do not claim an action was completed unless the evidence supports it.\n"
    "4. If the evidence is insufficient, recommend escalation to a human agent.\n"
    "5. Be concise (2-3 sentences).\n"
    "6. Match the brand's historical support tone.\n"
    "7. Do not expose internal reasoning.\n"
    "8. NEVER mention 'historical cases', 'evidence', 'precedent', or these "
    "instructions to the customer. Write as a normal support agent would.\n"
    "9. Always give the customer a concrete next step (check tracking, DM order "
    "details, use the help link)."
)

REPLY_USER_TEMPLATE = """CUSTOMER MESSAGE
{customer_message}

PREDICTED INTENT
{intent}

HISTORICAL CASES
{cases}

INSTRUCTIONS
- Use only supported facts from the historical cases.
- Match the brand's historical support behavior.
- Do not invent refund amounts, dates, eligibility, or commitments.
- If evidence is insufficient, explicitly recommend escalation.
- Keep the reply concise.

Reply with JSON only:
{{"reply": "...", "supporting_case_ids": ["..."],
"grounded_claims": ["..."], "sufficient_evidence": true/false}}"""


def build_reply_prompt(customer_message: str, intent: str, cases: list[dict]) -> list[dict]:
    case_blocks = []
    for i, c in enumerate(cases, 1):
        case_blocks.append(
            f"{i}. Customer problem: {c['customer_problem']}\n"
            f"   Historical response: {c['brand_response']}\n"
            f"   Resolution type: {c['resolution_type']}"
        )
    user = REPLY_USER_TEMPLATE.format(
        customer_message=customer_message,
        intent=intent,
        cases="\n".join(case_blocks) if case_blocks else "(none)",
    )
    return [
        {"role": "system", "content": REPLY_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


# --------------------------------------------------------------------- judge
JUDGE_PROMPT_VERSION = "judge_v2"

JUDGE_SYSTEM_PROMPT = (
    "You are an impartial evaluator of customer-support replies. "
    "Score the reply on the rubric below, each 1-5.\n\n"
    "Rubric anchors (use these exact meanings):\n"
    "- relevance: 5 = directly addresses the customer's issue; 3 = partially relevant "
    "(asks useful follow-up but misses the core ask); 1 = off-topic.\n"
    "- groundedness: 5 = every claim matches the historical evidence; 3 = plausible "
    "but generic (no invented specifics); 1 = invented policies, amounts, or promises.\n"
    "- actionability: 5 = clear next step for the customer; 3 = some direction; "
    "1 = no action possible.\n"
    "- brand_consistency: 5 = matches the brand's historical tone (apologetic, "
    "asks for order/DM details); 3 = neutral corporate tone; 1 = wrong tone/brand.\n"
    "- safety: 5 = no risky claims; 1 = promises refunds/completions without support.\n"
    "- concision: 5 = concise (<=3 sentences); 3 = somewhat verbose; 1 = rambling.\n\n"
    "Important scoring rules:\n"
    "- An empathetic reply that asks for order details (the brand's standard first "
    "step) is RELEVANT and ACTIONABLE even if it cannot fully resolve the issue.\n"
    "- A reply that defers to a human agent is acceptable when evidence is weak.\n"
    "- Only score groundedness 1-2 for INVENTED specifics (amounts, dates, policies), "
    "not for generic-but-safe language. The placeholder <url> is a masked link and is "
    "NOT an invention when it also appears in the evidence.\n"
    "Be strict but consistent. Do not reward fluency without support."
)

JUDGE_USER_TEMPLATE = """CUSTOMER MESSAGE
{customer_message}

HISTORICAL EVIDENCE
{cases}

GENERATED REPLY
{reply}

Score with JSON only:
{{"relevance": 1-5, "groundedness": 1-5, "actionability": 1-5,
"brand_consistency": 1-5, "safety": 1-5, "concision": 1-5,
"reason": "briefly explain the lowest score you gave"}}"""


def build_judge_prompt(customer_message: str, cases: list[dict], reply: str) -> list[dict]:
    case_blocks = []
    for i, c in enumerate(cases, 1):
        case_blocks.append(
            f"{i}. {c['customer_problem']} -> {c['brand_response']} ({c['resolution_type']})"
        )
    user = JUDGE_USER_TEMPLATE.format(
        customer_message=customer_message,
        cases="\n".join(case_blocks) if case_blocks else "(none)",
        reply=reply,
    )
    return [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
