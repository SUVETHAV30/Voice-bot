import asyncio
import os
from typing import Any, List
from langgraph.graph import StateGraph, END
from langgraph.config import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_groq import ChatGroq
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model="deepseek-r1-distill-llama-70b", 
    temperature=0, 
    streaming=True,
    reasoning_format="hidden"  # This prevents <think> tags from appearing in output
)

class AgentState(BaseModel):
    messages: List[Any]
    search_results: str = ""
    response: str = ""

search_tool = DuckDuckGoSearchRun()

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

    # 🔥 FIX: Use RunnableConfig to access writer
    async def _search_node(self, state: AgentState, config: RunnableConfig = None) -> AgentState:
        last_message = state.messages[-1].content if state.messages else ""
        search_query = last_message.replace("search for", "").replace("find", "").strip()

        # Access writer from config
        writer = config.get("writer") if config else None
        if writer:
            writer("🔍 Starting search...")  # No await needed!

        try:
            search_results = search_tool.run(search_query)
            state.search_results = search_results
            if writer:
                writer("✅ Search completed!")
        except Exception as e:                   
            print(f"Search error: {e}")
            state.search_results = f"Search failed: {str(e)}"
            if writer:
                writer(f"❌ Search failed: {str(e)}")

        return state

    # 🔥 FIX: Use RunnableConfig to access writer
    async def _generate_node(self, state: AgentState, config: RunnableConfig = None) -> AgentState:
        prompt = f"""
        You are a friendly, witty voice assistant having a natural phone conversation. 

        User just asked: "{state.messages[-1].content if state.messages else ''}"
        Here's what I found: {state.search_results}

        Instructions:
        - Sound like you're chatting with a good friend, not reading a manual
        - Sprinkle in some light humor or personality when appropriate
        - Keep responses under 30 seconds when spoken aloud
        - Use "um," "well," or "so" occasionally to sound natural
        - If the info is boring, make it interesting with analogies or fun facts
        - End with a friendly follow-up like "Does that help?" or "Want me to dig deeper?"
        - If you don't know something, admit it with humor: "Well, that's stumped me!"
        - Use contractions (it's, don't, can't) to sound conversational
        - Avoid lists or bullet points - speak in flowing sentences
        - If the search results are thin, be honest but offer to try a different angle
        """
        
        # Access writer from config
        writer = config.get("writer") if config else None
        if writer:
            writer("💬 Generating response...")
        
        try:
            response_text = ""
            print("\n💬 Streaming Response:\n")
            
            # 🔥 STREAM TOKENS THROUGH WRITER (with <think> filtering)
            in_think_block = False
            async for chunk in llm.astream([SystemMessage(content=prompt)]):
                if chunk.content:
                    # Filter out <think>...</think> blocks in real-time
                    filtered_content = ""
                    i = 0
                    while i < len(chunk.content):
                        # Check for opening <think> tag
                        if chunk.content[i:i+7] == "<think>":
                            in_think_block = True
                            i += 7
                            continue
                        
                        # Check for closing </think> tag
                        if chunk.content[i:i+8] == "</think>":
                            in_think_block = False
                            i += 8
                            continue
                        
                        # Only add content if we're not in a think block
                        if not in_think_block:
                            filtered_content += chunk.content[i]
                        
                        i += 1
                    
                    # Only stream non-empty filtered content
                    if filtered_content:
                        response_text += filtered_content
                        print(filtered_content, end="", flush=True)  # Console output
                        # Stream filtered token through writer
                        if writer:
                            writer(filtered_content)  # No await needed!

            state.response = response_text
            state.messages.append(AIMessage(content=response_text))

        except Exception as e:
            print(f"LLM error: {e}")
            error_msg = f"I encountered an error: {str(e)}"
            state.response = error_msg
            state.messages.append(AIMessage(content=error_msg))
            if writer:
                writer(error_msg)

        return state

    # 🔥 CORRECT: Use astream_events for proper streaming
    async def run(self, query: str):
        initial_state = AgentState(messages=[HumanMessage(content=query)])

        print("\n🚀 Executing Graph with Event Streaming...\n")
        
        # Use astream_events for proper streaming
        async for event in self.graph.astream_events(initial_state, version="v2"):
            kind = event["event"]
            
            # Filter for custom streaming events
            if kind == "on_custom":
                data = event.get("data")
                if data:
                    yield data
            
            # Stream LLM tokens
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
