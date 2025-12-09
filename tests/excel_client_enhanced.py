"""
Excel File Creation Client using LangChain (Enhanced with detailed logging).
Uses LLM with tool support to interact with MCP Excel server.
Implements correct API based on: https://github.com/haris-musa/excel-mcp-server/blob/ad5fff248bcd5c819966bc425aeff6ec808f5d38/TOOLS.md
"""

import json
import uuid
import requests
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI


# Configuration
LLM_API_URL = "https://ollama.ai-gateway.ru/v1"
MCP_SERVER_URL = "http://omv-nas:5020/mcp"
MODEL_NAME = "gpt-oss"
TEMPERATURE = 0.7
DEBUG = True  # Enable debug logging


class MCPExcelClient:
    """Client for interacting with MCP Excel server with enhanced error handling."""
    
    def __init__(self, base_url: str = MCP_SERVER_URL):
        self.base_url = base_url.rstrip("/")
        self.debug = DEBUG
        self.session_id = None
    
    def _log_debug(self, message: str):
        """Log debug message if enabled."""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def _parse_response(self, response_text: str) -> dict:
        """
        Parse MCP server response which may be in JSON or SSE format.
        
        Args:
            response_text: Raw response text from server
            
        Returns:
            Parsed JSON response as dictionary
        """
        # Try direct JSON parsing first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try SSE format parsing (Server-Sent Events)
        if "event:" in response_text and "data:" in response_text:
            self._log_debug("Detected SSE format response, parsing...")
            lines = response_text.strip().split('\n')
            
            for line in lines:
                if line.startswith('data:'):
                    json_str = line[5:].strip()  # Remove 'data:' prefix
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        raise Exception(f"Failed to parse SSE data JSON: {str(e)}\nData: {json_str}")
        
        # If neither format worked, raise error
        raise Exception(
            f"Failed to parse response in JSON or SSE format\n"
            f"Response text: {response_text}"
        )
    
    def initialize_session(self):
        """Initialize a session with the MCP server and get session ID."""
        self._log_debug("Initializing session with MCP server...")
        
        try:
            # Make initial request to establish session
            response = requests.post(
                f"{self.base_url}",
                json={"jsonrpc": "2.0", "method": "ping", "params": {}, "id": "init"},
                timeout=10,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
            )
            
            # Extract session ID from response headers
            if 'mcp-session-id' in response.headers:
                self.session_id = response.headers['mcp-session-id']
                self._log_debug(f"Session ID obtained: {self.session_id}")
                return True
            else:
                self._log_debug("No session ID in response headers")
                return False
        
        except Exception as e:
            self._log_debug(f"Warning: Could not initialize session: {str(e)}")
            return False
    
    def call_mcp(self, method: str, params: dict) -> dict:
        """
        Call MCP Excel server method with detailed error reporting.
        
        Args:
            method: RPC method name
            params: Method parameters
            
        Returns:
            Response result dictionary
        """
        # Initialize session if not already done
        if self.session_id is None:
            self.initialize_session()
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        self._log_debug(f"Calling MCP method: {method}")
        self._log_debug(f"Payload: {json.dumps(payload)}")
        
        try:
            # Prepare headers with session ID if available
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": "Python/3.12"
            }
            
            if self.session_id:
                headers["MCP-Session-Id"] = self.session_id
                self._log_debug(f"Using session ID: {self.session_id}")
            
            # Make the request with proper headers
            response = requests.post(
                f"{self.base_url}/excel/create_workbook",
                #json=payload,
                json={"filepath" : "somepath.xlsx"},
                timeout=30,
                headers=headers
            )
            
            # Update session ID from response if provided
            if 'mcp-session-id' in response.headers:
                new_session_id = response.headers['mcp-session-id']
                if new_session_id != self.session_id:
                    self._log_debug(f"Session ID updated: {new_session_id}")
                    self.session_id = new_session_id
            
            self._log_debug(f"Response Status: {response.status_code}")
            
            # Check for HTTP errors
            if response.status_code >= 400:
                error_details = self._extract_error_details(response)
                raise requests.exceptions.HTTPError(error_details)
            
            # Parse response
            result = self._parse_response(response.text)
            self._log_debug(f"Response Body: {json.dumps(result)}")
            
            # Check for JSON-RPC errors
            if "error" in result:
                error_info = result['error']
                error_msg = self._format_error_info(error_info)
                raise Exception(f"MCP Server Error:\n{error_msg}")
            
            return result.get("result", {})
        
        except requests.exceptions.ConnectionError as e:
            raise Exception(
                f"MCP Connection Error:\n"
                f"  - Cannot connect to {self.base_url}\n"
                f"  - Check if MCP server is running\n"
                f"  - Check host and port: {str(e)}"
            )
        except requests.exceptions.Timeout as e:
            raise Exception(
                f"MCP Timeout Error:\n"
                f"  - Server did not respond within 30 seconds\n"
                f"  - Error: {str(e)}"
            )
        except requests.exceptions.HTTPError as e:
            raise Exception(f"HTTP Error from MCP server:\n{str(e)}")
        except Exception as e:
            raise Exception(f"MCP Call Failed:\n{str(e)}")
    
    def _extract_error_details(self, response: requests.Response) -> str:
        """Extract detailed error information from HTTP response."""
        error_msg = f"HTTP {response.status_code} {response.reason}\n"
        
        # Add response headers
        error_msg += "\nResponse Headers:\n"
        for key, value in response.headers.items():
            error_msg += f"  {key}: {value}\n"
        
        # Add response body
        error_msg += "\nResponse Body:\n"
        try:
            body = response.text
            if body.strip():
                # Try to pretty-print JSON
                try:
                    json_body = json.loads(body)
                    error_msg += json.dumps(json_body, indent=2)
                except json.JSONDecodeError:
                    error_msg += body
            else:
                error_msg += "(empty)"
        except Exception as e:
            error_msg += f"(Could not read body: {str(e)})"
        
        return error_msg
    
    def _format_error_info(self, error_info) -> str:
        """Format error information from JSON-RPC response."""
        if isinstance(error_info, dict):
            msg = error_info.get('message', 'Unknown error')
            code = error_info.get('code', 'N/A')
            data = error_info.get('data')
            
            error_msg = f"  Error Code: {code}\n"
            error_msg += f"  Error Message: {msg}\n"
            if data:
                error_msg += f"  Error Data: {json.dumps(data, indent=2)}\n"
            return error_msg
        else:
            return f"  {str(error_info)}"


# Initialize MCP client
mcp_client = MCPExcelClient()


@tool
def create_workbook(filepath: str) -> str:
    """Create a new Excel workbook."""
    try:
        mcp_client.call_mcp("create_workbook", {"filepath": filepath})
        return f"Excel workbook created: {filepath}"
    except Exception as e:
        return f"Error creating workbook: {str(e)}"


@tool
def create_worksheet(filepath: str, sheet_name: str) -> str:
    """Create a new worksheet in an Excel file."""
    try:
        mcp_client.call_mcp(
            "create_worksheet",
            {"filepath": filepath, "sheet_name": sheet_name}
        )
        return f"Worksheet '{sheet_name}' created successfully"
    except Exception as e:
        return f"Error creating worksheet: {str(e)}"


@tool
def write_data_to_excel(filepath: str, sheet_name: str, data: list) -> str:
    """Write data to Excel worksheet."""
    try:
        # Convert list of lists to list of dicts for MCP API
        if data and isinstance(data[0], list):
            # First row is headers
            headers = data[0]
            data_dicts = [
                {str(headers[i]): row[i] for i in range(len(headers))}
                for row in data[1:]
            ]
        else:
            data_dicts = data
        
        mcp_client.call_mcp(
            "write_data_to_excel",
            {
                "filepath": filepath,
                "sheet_name": sheet_name,
                "data": data_dicts,
                "start_cell": "A1"
            }
        )
        return f"Data written successfully: {len(data_dicts)} rows"
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
        
        mcp_client.call_mcp("format_range", params)
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


def generate_data_rows(num_rows: int) -> list:
    """Generate test data rows with pattern: [i, i*10, i*100]."""
    return [[i, i * 10, i * 100] for i in range(1, num_rows + 1)]


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
        max_iterations=20
    )
    
    return agent_executor


def main():
    """Main function to execute the Excel creation task."""
    print("=" * 70)
    print("Excel File Creation and Formatting Client with LangChain")
    print("=" * 70)
    
    # Generate UUID for filename
    file_uuid = str(uuid.uuid4())
    filepath = f"{file_uuid}.xlsx"
    
    print(f"\nGenerating Excel file: {filepath}")
    
    # Generate data
    headers = ["Колонка 1", "Колонка 2", "Колонка 3"]
    data_rows = generate_data_rows(15)
    
    print(f"Headers: {headers}")
    print(f"Data rows: {len(data_rows)}")
    
    # Create agent
    agent_executor = create_agent()
    
    # Prepare the task with specific instructions
    task = f"""Create an Excel file with these specifications:

1. Create workbook: {filepath}
2. Create worksheet: "Data"
3. Write data (headers + 15 rows):
   Headers: {headers}
   Data: {data_rows}
4. Format header row (A1:C1):
   - Background color: 0070C0 (blue)
   - Font color: FFFFFF (white)
   - Bold text
5. Format data rows (A2:C16) with alternating colors:
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
    main()
