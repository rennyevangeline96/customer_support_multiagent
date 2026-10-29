
import asyncio
import json
import os
import re
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient


# ============================================================
# 1. CONFIGURATION
# ============================================================

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

MAX_AGENT_STEPS = 2
TERMINATION_MESSAGE = "SUPPORT_FLOW_COMPLETE"

AGENT_NAMES = [
    "marketing_agent",
    "it_support_agent",
    "finance_agent",
    "hr_agent",
]

AGENT_LABELS = {
    "marketing_agent": "Marketing",
    "it_support_agent": "IT Support",
    "finance_agent": "Finance",
    "hr_agent": "HR",
}


# ============================================================
# 2. STREAMLIT PAGE
# ============================================================

st.set_page_config(
    page_title="Multi-Agent Customer Support",
    page_icon="🎧",
    layout="wide",
)

st.title("🎧 Multi-Agent Customer Support")
st.write(
    "Ask a question. The Selector Agent identifies the right "
    "department and routes your question to its specialist."
)

st.caption(
    "Powered by AutoGen, OpenAI, and Streamlit."
)


# ============================================================
# 3. SELECTOR AGENT
# ============================================================

SELECTOR_INSTRUCTIONS = """
You are the Selector Agent for a customer support system.

Your only job is to classify the user's question and select
exactly ONE of the following agents.

1. marketing_agent
   Handles marketing campaigns, market research, sales,
   lead generation, customer acquisition, advertising,
   branding, promotions, and conversion rates.

2. it_support_agent
   Handles software errors, login issues, applications,
   computers, networks, technical troubleshooting,
   system access, and technical support.

3. finance_agent
   Handles invoices, billing, payments, refunds,
   budgets, expenses, and financial transactions.

4. hr_agent
   Handles employee leave, attendance, HR policies,
   benefits, onboarding, payroll questions, and workplace
   procedures.

Routing rules:
- Select the single most relevant agent.
- Do not answer the user's question yourself.
- Do not select multiple agents.
- Do not invent department responsibilities.
- If the question is ambiguous, select the best match
  based on the available information.
- If the question is unrelated to these departments,
  select the closest appropriate agent and explain
  that the user may need another department.

Return ONLY valid JSON in this format:

{
  "agent": "marketing_agent",
  "reason": "The question is about market sales."
}

The agent field must be exactly one of the four agent names.
Do not include Markdown fences or any text outside the JSON.
"""


# ============================================================
# 4. DOMAIN AGENTS
# ============================================================

def create_marketing_agent(model_client):
    return AssistantAgent(
        name="marketing_agent",
        model_client=model_client,
        system_message=f"""
You are the Marketing Customer Support Specialist.

You handle:
- Marketing and advertising campaigns
- Market research and customer trends
- Sales growth and lead generation
- Branding and promotions
- Customer acquisition and conversion

Answer the customer's actual question clearly.
Give practical, actionable recommendations.
Ask a clarifying question if essential information is missing.
Do not invent company-specific data, campaign results,
or sales figures.

If the question is outside Marketing, explain the limitation
and suggest contacting the appropriate department.

End your response with this exact marker on its own line:
{TERMINATION_MESSAGE}
""",
    )


def create_it_agent(model_client):
    return AssistantAgent(
        name="it_support_agent",
        model_client=model_client,
        system_message=f"""
You are the IT Customer Support Specialist.

You handle:
- Software and application errors
- Login and account access issues
- Computer and network troubleshooting
- Technical configuration
- System problems and IT support

Give clear, step-by-step troubleshooting instructions.
Do not claim to access or modify the user's systems.
Never ask for passwords, API keys, or other secret credentials.

If the question is outside IT support, explain the limitation
and suggest contacting the appropriate department.

End your response with this exact marker on its own line:
{TERMINATION_MESSAGE}
""",
    )


def create_finance_agent(model_client):
    return AssistantAgent(
        name="finance_agent",
        model_client=model_client,
        system_message=f"""
You are the Finance Customer Support Specialist.

You handle:
- Invoices and billing
- Payments and refunds
- Budgets and expenses
- Financial transactions
- Payment status questions

Explain financial processes clearly.
Do not invent transaction records, account balances,
refund status, or company-specific financial policies.
If account-specific verification is required, explain
that an authorized support representative must check it.

If the question is outside Finance, explain the limitation
and suggest contacting the appropriate department.

End your response with this exact marker on its own line:
{TERMINATION_MESSAGE}
""",
    )


def create_hr_agent(model_client):
    return AssistantAgent(
        name="hr_agent",
        model_client=model_client,
        system_message=f"""
You are the HR Customer Support Specialist.

You handle:
- Leave and attendance
- Employee policies
- Employee benefits
- Onboarding procedures
- Workplace procedures
- General HR questions

Give respectful, clear, practical answers.
Do not invent company-specific policies or employee records.
If a policy or record must be verified, direct the user
to their HR team.

If the question is outside HR, explain the limitation
and suggest contacting the appropriate department.

End your response with this exact marker on its own line:
{TERMINATION_MESSAGE}
""",
    )


# ============================================================
# 5. HELPER FUNCTIONS
# ============================================================

def extract_text(result) -> str:
    """Extract the last agent message as readable text."""

    if not getattr(result, "messages", None):
        return ""

    message = result.messages[-1]
    content = getattr(message, "content", "")

    if isinstance(content, str):
        return content

    return str(content)


def parse_selector_response(text: str) -> dict:
    """Parse the selector's JSON response safely."""

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Recover JSON if the model unexpectedly adds extra text.
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "The Selector Agent did not return valid JSON. "
        "Please try asking the question again."
    )


def get_fallback_agent(question: str) -> str:
    """
    Safe keyword-based fallback if the selector response
    cannot be parsed. This does not call another LLM.
    """

    question_lower = question.lower()

    keywords = {
        "marketing_agent": [
            "marketing", "sales", "campaign", "advertising",
            "advertisement", "leads", "lead generation",
            "promotion", "branding", "market research",
            "customer acquisition", "conversion",
        ],
        "it_support_agent": [
            "computer", "software", "login", "password",
            "network", "internet", "error", "bug",
            "application", "app", "system", "technical",
            "server", "website not working",
        ],
        "finance_agent": [
            "invoice", "billing", "payment", "refund",
            "budget", "expense", "transaction", "bill",
        ],
        "hr_agent": [
            "leave", "attendance", "employee", "payroll",
            "benefits", "hr policy", "onboarding",
            "human resources", "holiday",
        ],
    }

    for agent_name, words in keywords.items():
        if any(word in question_lower for word in words):
            return agent_name

    # Default when no clear keyword match exists.
    return "it_support_agent"


# ============================================================
# 6. TWO-STEP ROUTING WORKFLOW
# ============================================================

async def process_customer_question(question: str) -> dict:
    """
    Step 1: Selector Agent chooses a domain agent.
    Step 2: Only the selected domain agent answers.

    Hard limit: two agent calls per question.
    No agent-to-agent revision loop is used.
    """

    model_client = OpenAIChatCompletionClient(
        model=MODEL,
        api_key=API_KEY,
    )

    try:
        # ----------------------------------------------------
        # STEP 1 — SELECTOR AGENT
        # ----------------------------------------------------

        selector = AssistantAgent(
            name="selector_agent",
            model_client=model_client,
            system_message=SELECTOR_INSTRUCTIONS,
        )

        selector_result = await selector.run(
            task=f"Classify and route this customer question:\n{question}"
        )

        selector_text = extract_text(selector_result)

        try:
            routing = parse_selector_response(selector_text)
            selected_agent = routing.get("agent", "")

            if selected_agent not in AGENT_NAMES:
                selected_agent = get_fallback_agent(question)

            routing_reason = routing.get(
                "reason",
                "Selected based on the question's topic.",
            )

        except ValueError:
            selected_agent = get_fallback_agent(question)
            routing_reason = (
                "Used keyword-based fallback because the "
                "selector response could not be parsed."
            )

        # ----------------------------------------------------
        # STEP 2 — SELECTED DOMAIN AGENT
        # ----------------------------------------------------

        agents = {
            "marketing_agent": create_marketing_agent(model_client),
            "it_support_agent": create_it_agent(model_client),
            "finance_agent": create_finance_agent(model_client),
            "hr_agent": create_hr_agent(model_client),
        }

        specialist = agents[selected_agent]

        specialist_result = await specialist.run(
            task=f"""
Customer question:
{question}

You were selected by the Selector Agent because:
{routing_reason}

Answer the customer directly and helpfully.
Do not repeat the routing explanation unnecessarily.
"""
        )

        answer = extract_text(specialist_result)

        # The completion marker is a workflow signal.
        # Remove it from the displayed answer.
        answer = answer.replace(
            TERMINATION_MESSAGE,
            "",
        ).strip()

        return {
            "question": question,
            "agent": selected_agent,
            "department": AGENT_LABELS[selected_agent],
            "routing_reason": routing_reason,
            "answer": answer,
            "agent_steps": MAX_AGENT_STEPS,
            "termination": TERMINATION_MESSAGE,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    finally:
        await model_client.close()


# ============================================================
# 7. CHAT HISTORY
# ============================================================

if "support_history" not in st.session_state:
    st.session_state.support_history = []


for item in st.session_state.support_history:
    with st.chat_message("user"):
        st.write(item["question"])

    with st.chat_message("assistant"):
        st.caption(
            f"Routed to: {item['department']} "
            f"({item['agent']})"
        )
        st.write(item["answer"])


# ============================================================
# 8. CUSTOMER QUESTION INPUT
# ============================================================

question = st.chat_input("Ask your customer support question...")

if question:

    if not API_KEY:
        st.error(
            "OPENAI_API_KEY is missing. Add it to your .env file "
            "and restart Streamlit."
        )

    elif not question.strip():
        st.warning("Please enter a question.")

    else:
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):

            status = st.status(
                "Processing your question...",
                expanded=True,
            )

            try:
                result = asyncio.run(
                    process_customer_question(question.strip())
                )

                status.update(
                    label="Support workflow completed",
                    state="complete",
                    expanded=False,
                )

                st.caption(
                    f"Routed to: {result['department']} "
                    f"({result['agent']})"
                )

                st.write(result["answer"])

                with st.expander("Routing details"):
                    st.write(
                        "**Selector's reason:**",
                        result["routing_reason"],
                    )
                    st.write(
                        "**Maximum agent steps:**",
                        MAX_AGENT_STEPS,
                    )
                    st.write(
                        "**Termination signal:**",
                        result["termination"],
                    )

                st.session_state.support_history.append(result)

            except Exception as exc:
                status.update(
                    label="Unable to process the question",
                    state="error",
                    expanded=True,
                )

                st.error(f"Error: {exc}")

                st.info(
                    "Check your API key, internet connection, "
                    "and installed AutoGen package versions."
                )


# ============================================================
# 9. SIDEBAR
# ============================================================

with st.sidebar:
    st.header("🏢 Support Departments")

    st.markdown(
        """
        **📈 Marketing**
        - Sales and campaigns
        - Leads and promotions

        **💻 IT Support**
        - Software and technical issues
        - Login and network problems

        **💰 Finance**
        - Invoices and payments
        - Refunds and expenses

        **👥 HR**
        - Leave and attendance
        - Policies and benefits
        """
    )

    st.divider()

    st.metric(
        "Questions answered this session",
        len(st.session_state.support_history),
    )

    st.caption(f"Model: {MODEL}")
    st.caption(f"Maximum agent calls per question: {MAX_AGENT_STEPS}")

    if st.button("Clear Chat History", use_container_width=True):
        st.session_state.support_history = []
        st.rerun()
