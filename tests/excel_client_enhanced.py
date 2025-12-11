"""
Excel File Creation Client using LangChain with FastMCP.
Uses LLM with tool support to interact with MCP Excel server.
Implements correct API based on: https://github.com/haris-musa/excel-mcp-server/blob/ad5fff248bcd5c819966bc425aeff6ec808f5d38/TOOLS.md
"""

import asyncio
import uuid
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


# Configuration
LLM_API_URL = "https://ollama.ai-gateway.ru/v1"
MCP_SERVER_URL = "https://excel.ai-gateway.ru/mcp"
MODEL_NAME = "gpt-oss"
TEMPERATURE = 0.7
DEBUG = True  # Enable debug logging


class MCPExcelClient:
    """Client for interacting with MCP Excel server using FastMCP."""
    
    def __init__(self, base_url: str = MCP_SERVER_URL):
        self.base_url = base_url.rstrip("/")
        self.debug = DEBUG
        self.client = None
        self.transport = None
    
    def _log_debug(self, message: str):
        """Log debug message if enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    async def initialize(self):
        """Initialize FastMCP client and transport."""
        if self.client is None:
            self._log_debug("Initializing FastMCP client...")
            self.transport = StreamableHttpTransport(url=self.base_url)
            self.client = Client(self.transport)
            self._log_debug("FastMCP client initialized successfully")
    
    async def call_mcp(self, tool_name: str, arguments: dict) -> dict:
        """
        Call MCP Excel server tool using FastMCP.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result dictionary
        """
        try:
            await self.initialize()
            
            self._log_debug(f"Calling MCP tool: {tool_name}")
            self._log_debug(f"Arguments: {arguments}")
            
            async with self.client:
                result = await self.client.call_tool(
                    name=tool_name,
                    arguments=arguments
                )
                
                self._log_debug(f"Tool result: {result}")
                return result
        
        except Exception as e:
            self._log_debug(f"Error calling MCP tool: {str(e)}")
            raise Exception(f"MCP Call Failed: {tool_name}\nError: {str(e)}")


# Initialize MCP client
mcp_client = MCPExcelClient()


def _run_async(coro):
    """Helper to run async code from sync context."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If loop is already running, create a new one in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return loop.run_until_complete(coro)


@tool
def create_workbook(filepath: str) -> str:
    """Create a new Excel workbook."""
    try:
        result = _run_async(mcp_client.call_mcp("create_workbook", {"filepath": filepath}))
        return f"Excel workbook created: {filepath}"
    except Exception as e:
        return f"Error creating workbook: {str(e)}"


@tool
def create_worksheet(filepath: str, sheet_name: str) -> str:
    """Create a new worksheet in an Excel file."""
    try:
        result = _run_async(mcp_client.call_mcp(
            "create_worksheet",
            {"filepath": filepath, "sheet_name": sheet_name}
        ))
        return f"Worksheet '{sheet_name}' created successfully"
    except Exception as e:
        return f"Error creating worksheet: {str(e)}"


@tool
def write_data_to_excel(filepath: str, sheet_name: str, data: list) -> str:
    """Write data to Excel worksheet."""
    try:
        # Data should be in the format: [headers, [row1], [row2], ...]
        # Extract headers and rows
        if data and isinstance(data[0], list):
            headers = data[0]
            rows = data[1:]
            # Convert to list of lists format expected by MCP
            data_rows = [headers] + rows
        else:
            data_rows = data
        
        result = _run_async(mcp_client.call_mcp(
            "write_data_to_excel",
            {
                "filepath": filepath,
                "sheet_name": sheet_name,
                "data": data_rows,
                "start_cell": "A1"
            }
        ))
        return f"Data written successfully: {len(data_rows) - 1} rows"
    except Exception as e:
        return f"Error writing data: {str(e)}"


@tool
def format_range(filepath: str, sheet_name: str, start_cell: str, end_cell: str,
                 bold: bool = False, font_color: str = None, bg_color: str = None) -> str:
    """Apply formatting to a range of cells."""
    try:
        params = {
            "filepath": filepath,
            "sheet_name": sheet_name,
            "start_cell": start_cell,
            "end_cell": end_cell,
            "bold": bold
        }
        if font_color:
            params["font_color"] = font_color
        if bg_color:
            params["bg_color"] = bg_color
        
        result = _run_async(mcp_client.call_mcp("format_range", params))
        return "Range formatted successfully"
    except Exception as e:
        return f"Error formatting range: {str(e)}"


def create_llm_client() -> ChatOpenAI:
    """Create and return LangChain OpenAI client."""
    return ChatOpenAI(
        model=MODEL_NAME,
        temperature=TEMPERATURE,
        api_key="none",
        base_url=LLM_API_URL
    )


def generate_data_with_llm(num_rows: int) -> list:
    """Generate realistic data rows using LLM based on headers."""
    llm = create_llm_client()
    
    headers = ["Имя", "Фамилия", "Пол", "Возраст"]
    
    prompt = f"""Generate {num_rows} rows of realistic Russian person data with the following headers: {headers}
    
Requirements:
- Имя (Name): Russian first names
- Фамилия (Last name): Russian last names
- Пол (Gender): М (male) or Ж (female)
- Возраст (Age): Age between 18 and 80

Return the data as a Python list of lists in this exact format (no markdown, just raw Python):
[[name1, lastname1, gender1, age1], [name2, lastname2, gender2, age2], ...]

Do not include headers in the output, only data rows. Generate exactly {num_rows} rows."""

    response = llm.invoke(prompt)
    response_text = response.content.strip()
    
    # Parse the response as Python list
    try:
        data_rows = eval(response_text)
        if isinstance(data_rows, list) and len(data_rows) == num_rows:
            return data_rows
    except Exception as e:
        print(f"Warning: Failed to parse LLM response, using fallback data: {e}")
    
    # Fallback: generate default data if LLM parsing fails
    return [[f"Имя{i}", f"Фамилия{i}", "М" if i % 2 == 0 else "Ж", 20 + (i % 60)] 
            for i in range(1, num_rows + 1)]


def create_agent():
    """Create LangChain agent with tools."""
    tools = [
        create_workbook,
        create_worksheet,
        write_data_to_excel,
        format_range
    ]
    
    llm = create_llm_client()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant that creates and formats Excel files.
Your task is to help create an Excel spreadsheet methodically:
1. Create a new XLSX workbook
2. Create a worksheet
3. Write headers and data to the worksheet
4. Format the header row with blue background and white text
5. Format data rows with alternating colors

Use the available tools to accomplish each step. Always verify each step completes successfully before moving to the next."""),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=200
    )
    
    return agent_executor


def main(num_rows: int = 10):
    """Main function to execute the Excel creation task.
    
    Args:
        num_rows: Number of data rows to generate (default: 10)
    """
    print("=" * 70)
    print("Excel File Creation and Formatting Client with LangChain")
    print("=" * 70)
    
    # Generate UUID for filename
    file_uuid = str(uuid.uuid4())
    filepath = f"{file_uuid}.xlsx"
    
    print(f"\nGenerating Excel file: {filepath}")
    print(f"Generating {num_rows} data rows using LLM...")
    
    # Define headers
    headers = ["Имя", "Фамилия", "Пол", "Возраст"]
    
    # Generate data using LLM
    data_rows = generate_data_with_llm(num_rows)
    
    print(f"Headers: {headers}")
    print(f"Data rows generated: {len(data_rows)}")
    print(f"Sample data: {data_rows[0] if data_rows else 'No data'}")
    
    # Create agent
    agent_executor = create_agent()
    
    # Prepare the task with specific instructions
    task = f"""Create an Excel file with these specifications:

1. Create workbook: {filepath}
2. Create worksheet: "Data"
3. Write data with headers and {num_rows} rows:
   Headers: {headers}
   Data: {data_rows}
4. Format header row (A1:D1):
   - Background color: 0070C0 (blue)
   - Font color: FFFFFF (white)
   - Bold text
5. Format data rows (A2:D{num_rows + 1}) with alternating colors:
   - Odd rows: background FFFFFF (white)
   - Even rows: background D3D3D3 (light gray)

Execute each step in order. Use the filepath "{filepath}" for all operations."""
    
    try:
        # Run agent
        print("\nStarting agent execution...\n")
        result = agent_executor.invoke({"input": task})
        
        print("\n" + "=" * 70)
        print("TASK COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"\nFile created: {filepath}")
        print(f"\nAgent output:")
        print(result.get("output", "No output"))
        
    except Exception as e:
        print(f"\nError during execution: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    # You can specify the number of rows here (default: 10)
    main(num_rows=20)
