#!/usr/bin/env python3
import asyncio
import anthropic
import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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
    
    if not adx_cluster or not adx_database:
        print("❌ Error: ADX_CLUSTER_URI and ADX_DATABASE must be set in .env file")
        return
    
    server_params = StdioServerParameters(
        command="python3",
        args=["mcp-server/adx_server_quiet.py"],
        env={
            "ADX_CLUSTER_URI": adx_cluster,
            "ADX_DATABASE": adx_database, 
            "AZURE_TENANT_ID": azure_tenant
        }
    )
    
    system_prompt = """
                    You are a KQL expert and Azure Data Explorer administrator. You can help with queries and table management.

                    Available tools:
                    1. adx_query - Run KQL queries
                    2. adx_create_table - Create new tables
                    3. adx_ingest_inline - Add data to tables

                    Available tables: AppLogs (Timestamp, Level, Message, Service, Host, UserId)

                    For queries, respond with:
                    QUERY: [KQL query]

                    For table creation, respond with:
                    CREATE_TABLE: [table_name]
                    SCHEMA: [column definitions in Kusto syntax]

                    Examples:
                    - "Show me log levels from the last hour" → QUERY: AppLogs | where Timestamp > ago(1h) | summarize Count = count() by Level
                    - "Show me all errors" → QUERY: AppLogs | where Level == 'ERROR'
                    - "Create a users table with id, name, email" → CREATE_TABLE: Users
                    SCHEMA: Id:int, Name:string, Email:string
                    - "Create a products table" → CREATE_TABLE: Products
                    SCHEMA: ProductId:int, ProductName:string, Price:real, CreatedDate:datetime

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
        
        async with stdio_client(server_params) as (read, write):
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
                
                elif "CREATE_TABLE:" in claude_response:
                    lines = claude_response.split('\n')
                    table_name = None
                    schema = None
                    
                    for line in lines:
                        if line.startswith("CREATE_TABLE:"):
                            table_name = line.split("CREATE_TABLE:")[1].strip()
                        elif line.startswith("SCHEMA:"):
                            schema = line.split("SCHEMA:")[1].strip()
                    
                    if table_name and schema:
                        print(f"🏗️ Creating table: {table_name}")
                        print(f"📋 Schema: {schema}")
                        
                        result = await session.call_tool("adx_create_table", {
                            "input": {
                                "table": table_name,
                                "schema_kql": schema
                            }
                        })
                        
                        print(f"✅ Table Creation Result:")
                        for content in result.content:
                            print(f"  {content.text}")
                    else:
                        print("❌ Could not parse table creation parameters")
                
                else:
                    print("❌ Claude didn't provide a valid command format")
                
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    print("🤖 Claude + ADX MCP Integration (Enhanced)")
    print("Ask questions about your Azure Data Explorer data or create tables!")
    print("Examples:")
    print("  - 'Show me all errors'")
    print("  - 'Create a users table with id, name, email'")
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
