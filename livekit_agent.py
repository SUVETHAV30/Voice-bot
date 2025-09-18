# from langgraph_agent import SearchAgent
# from fastapi import FastAPI, HTTPException

# agent=SearchAgent()
# graph=agent.graph

# from langgraph.graph import StateGraph
# from livekit.agents import AgentSession, Agent
# from livekit.plugins import langchain

# # Define your LangGraph workflow
# # def create_workflow():
# #     workflow = StateGraph(...)
# #     # Add your nodes and edges
# #     return workflow.compile()

# # Use the workflow as an LLM
# session = AgentSession(
#     llm=langchain.LLMAdapter(
#         graph=graph
#     ),
#     # ... stt, tts, vad, turn_detection, etc.
# )