import asyncio
import os
from typing import Any, List
# from livekit_agent import rtc, api
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.tools import DuckDuckGoSearchRun
# from livekit.api.access_token import AccessToken, VideoGrants
from langchain_groq import ChatGroq
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq LLM with streaming enabled
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, streaming=True)


class AgentState(BaseModel):
    messages: List[Any]
    search_results: str = ""
    response: str = ""


search_tool = DuckDuckGoSearchRun()


# def generate_access_token(api_key: str, api_secret: str, room_name: str, participant_name: str):
#     """Generate LiveKit access token"""
#     try:
#         token = AccessToken(api_key, api_secret)
#         token.with_identity(participant_name)
#         token.with_name(participant_name)
#         token.with_grants(VideoGrants(
#             room_join=True,
#             room=room_name,
#             can_publish=True,
#             can_subscribe=True
#         ))
#         return token.to_jwt()
#     except NameError:
#         import jwt, time
#         now = int(time.time())
#         payload = {
#             'iss': api_key,
#             'sub': participant_name,
#             'iat': now,
#             'exp': now + 3600,
#             'video': {
#                 'room': room_name,
#                 'roomJoin': True,
#                 'canPublish': True,
#                 'canSubscribe': True
#             }
#         }
#         return jwt.encode(payload, api_secret, algorithm='HS256')


class SearchAgent:
    def __init__(self):
        self.graph = self._create_graph()

    def _create_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("search", self._search_node)
        workflow.add_node("generate", self._generate_node)

        workflow.set_entry_point("search")
        workflow.add_edge("search", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()

    async def _search_node(self, state: AgentState) -> AgentState:
        last_message = state.messages[-1].content if state.messages else ""
        search_query = last_message.replace("search for", "").replace("find", "").strip()

        try:
            search_results = search_tool.run(search_query)
            state.search_results = search_results
        except Exception as e:
            print(f"Search error: {e}")
            state.search_results = f"Search failed: {str(e)}"

        return state

    async def _generate_node(self, state: AgentState) -> AgentState:
        prompt = f"""
        User Query: {state.messages[-1].content if state.messages else ""}
        Search Results: {state.search_results}

        Provide a concise, helpful response based on the search results.
        Keep it conversational for voice interaction.
        """

        try:
            response_text = ""
            print("\n💬 Streaming Response:\n")
            # STREAM TOKENS FROM LLM
            async for chunk in llm.astream([SystemMessage(content=prompt)]):
                if chunk.content:
                    response_text += chunk.content
                    print(chunk.content, end="", flush=True)  # live stream to console/UI

            state.response = response_text
            state.messages.append(AIMessage(content=response_text))

        except Exception as e:
            print(f"LLM error: {e}")
            state.response = f"I encountered an error: {str(e)}"
            state.messages.append(AIMessage(content=state.response))

        return state

    async def run(self, query: str):
        initial_state = AgentState(messages=[HumanMessage(content=query)])

        print("\n🚀 Executing Graph...\n")
        async for event in self.graph.astream(initial_state):
            # Each event is a dict snapshot of the AgentState
            if "generate" in event:
                chunk = event["generate"].get("response", "")
                if chunk:
                    yield chunk  # 🔴 yield chunk instead of printing



# async def main():
#     agent = SearchAgent()
#     async for chunk in agent.run("search for latest AI news"):
#         print(chunk, end="", flush=True)  # stream chunks live


# if __name__ == "__main__":
#     asyncio.run(main())
