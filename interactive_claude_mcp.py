import asyncio
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from prompts import FORMAT_INSTRUCTIONS, SYSTEM_PROMPT

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=2000, temperature=0)

async def ask_question(question: str):
    """Ask a natural language question and get ADX results"""
    mcp_host = os.environ.get("MCP_HOST", "127.0.0.1")
    mcp_port = os.environ.get("MCP_PORT", "8000")

    base_url = f"http://{mcp_host}:{mcp_port}/mcp"
    async with streamablehttp_client(base_url) as (read, write, get_session_id):
        async with ClientSession(read_stream=read, write_stream=write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(
                model=llm,
                tools=tools,
                prompt=SYSTEM_PROMPT.format(format_instructions=FORMAT_INSTRUCTIONS)
            )
            result = await agent.ainvoke({"messages": [HumanMessage(content=question)]})
            return result["messages"][-1].content


async def main():
    while True:
        question = input("> ")
        if question.lower() in ["quit", "exit", "q"]:
            break
        if question:
            answer = await ask_question(question)
            print(answer)


if __name__ == "__main__":
    asyncio.run(main())
