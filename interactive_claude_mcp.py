#!/usr/bin/env python3
import asyncio
import anthropic
import os
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Load environment variables from .env file
load_dotenv()

async def ask_question(question: str):
    """Ask a natural language question and get ADX results"""
    
    # Get API key from environment
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    if not claude_api_key:
        print("❌ Error: CLAUDE_API_KEY not found in .env file")
        return
    
    claude = anthropic.Anthropic(api_key=claude_api_key)
    
    # Get ADX configuration from environment
    adx_cluster = os.getenv("ADX_CLUSTER_URI")
    adx_database = os.getenv("ADX_DATABASE")
    azure_tenant = os.getenv("AZURE_TENANT_ID")
    azure_client_id = os.getenv("AZURE_CLIENT_ID")
    azure_client_secret = os.getenv("AZURE_CLIENT_SECRET")
    
    if not adx_cluster or not adx_database:
        print("❌ Error: ADX_CLUSTER_URI and ADX_DATABASE must be set in .env file")
        return
    if not azure_client_id or not azure_client_secret or not azure_tenant:
        print("❌ Error: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID must be set in .env file")
        return

    # Connect to a running MCP server over Streamable HTTP (preferred).
    mcp_host = os.getenv("MCP_HOST", "127.0.0.1")
    mcp_port = int(os.getenv("MCP_PORT", "8765"))
    
    system_prompt = """
                    You are a KQL expert and Azure Data Explorer administrator. You can help with queries and table management.

                    Available tools:
                    adx_query - Run KQL queries

                    Available tables: AppLogs (Timestamp, Level, Message, Service, Host, UserId)

                    For queries, respond with:
                    QUERY: [KQL query]

                    
                    Examples:
                    - "Show me log levels from the last hour" → QUERY: AppLogs | where Timestamp > ago(1h) | summarize Count = count() by Level
                    - "Show me all errors" → QUERY: AppLogs | where Level == 'ERROR'

                    Respond with the appropriate format. Do not include any explanations, comments, or additional text after the query.
                    """

    try:
        response = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            temperature=0.1,
            system=system_prompt,
            messages=[{"role": "user", "content": question}]
        )
        
        claude_response = response.content[0].text.strip()
        print(f"🤖 Claude's analysis: {claude_response}")
        
        # Connect to the MCP server over Streamable HTTP
        mcp_path = os.getenv("MCP_PATH", "/mcp")
        base_url = f"http://{mcp_host}:{mcp_port}{mcp_path}"
        async with streamablehttp_client(base_url) as (read, write, get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Parse Claude's response
                if "QUERY:" in claude_response:
                    kql_query = claude_response.split("QUERY:")[1].strip().split("\n")[0].strip()
                    print(f"🔍 Executing query: {kql_query}")

                    result = await session.call_tool("adx_query", {"input": {"kql": kql_query}})

                    print(f"📊 Query Results:")
                    for content in result.content:
                        print(f"  {content.text}")
                else:
                    print("❌ Claude didn't provide a valid command format")
    # streamablehttp_client handles connection termination for us
                
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    print("🤖 Claude + ADX MCP Integration (Enhanced)")
    print("Ask questions about your Azure Data Explorer data or create tables!")
    print("Examples:")
    print("  - 'Show me all errors'")
    print("  - 'Show me recent logs'")
    print("Type 'quit' to exit.\n")
    
    while True:
        question = input("❓ Your question: ").strip()
        if question.lower() in ['quit', 'exit', 'q']:
            break
        
        if question:
            print("=" * 50)
            await ask_question(question)
            print("=" * 50)
            print()

if __name__ == "__main__":
    asyncio.run(main())
