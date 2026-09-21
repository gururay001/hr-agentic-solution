"""Pod 5 Escalation Sub-Agent on Gemini 3.6 Flash."""
from google.adk.agents import LlmAgent
from agent import config

escalation_agent = LlmAgent(
    model="gemini-3.6-flash",
    name="pod5_escalation_agent",
    description="Empathetic HR Specialist Sub-Agent handling warm handoffs and critical escalations.",
    instruction="You are a senior HR escalation specialist. Provide warm, empathetic, and professional assistance during high-stress escalations or when sentiment is critical."
)
