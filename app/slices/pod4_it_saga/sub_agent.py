"""Pod 4 IT Service Sub-Agent on Gemini 3.6 Pro."""
from google.adk.agents import LlmAgent

it_service_agent = LlmAgent(
    model="gemini-3.6-pro",
    name="pod4_it_service_agent",
    description="IT Service Sub-Agent for resolving complex cross-domain provisioning tasks.",
    instruction="You are an IT Service specialist agent capable of coordinating complex cross-system saga workflows, managing resources, and recovering from failures."
)
