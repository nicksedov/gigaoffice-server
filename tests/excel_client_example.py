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
                 bold: bool = False, italic: bool = False, underline: bool = False,
                 font_size: int = None, font_color: str = None, bg_color: str = None,
                 border_style: str = None, border_color: str = None, number_format: str = None,
                 alignment: str = None, wrap_text: bool = False, merge_cells: bool = False) -> str:
    """Apply formatting to a range of cells."""
    try:
        params = {
            "filepath": filepath,
            "sheet_name": sheet_name,
            "start_cell": start_cell,
            "end_cell": end_cell,
            "bold": bold,
            "italic": italic,
            "underline": underline,
            "wrap_text": wrap_text,
            "merge_cells": merge_cells
        }
        if font_size:
            params["font_size"] = font_size
        if font_color:
            params["font_color"] = font_color
        if bg_color:
            params["bg_color"] = bg_color
        if border_style:
            params["border_style"] = border_style
        if border_color:
            params["border_color"] = border_color
        if number_format:
            params["number_format"] = number_format
        if alignment:
            params["alignment"] = alignment
        
        result = _run_async(mcp_client.call_mcp("format_range", params))
        return "Range formatted successfully"
    except Exception as e:
        return f"Error formatting range: {str(e)}"


@tool
def get_workbook_metadata(filepath: str, include_ranges: bool = False) -> str:
    """Get metadata about workbook including sheets and ranges."""
    try:
        result = _run_async(mcp_client.call_mcp(
            "get_workbook_metadata",
            {"filepath": filepath, "include_ranges": include_ranges}
        ))
        return f"Workbook metadata: {result}"
    except Exception as e:
        return f"Error getting workbook metadata: {str(e)}"


@tool
def read_data_from_excel(filepath: str, sheet_name: str, start_cell: str = "A1",
                         end_cell: str = None, preview_only: bool = False) -> str:
    """Read data from Excel worksheet."""
    try:
        params = {
            "filepath": filepath,
            "sheet_name": sheet_name,
            "start_cell": start_cell,
            "preview_only": preview_only
        }
        if end_cell:
            params["end_cell"] = end_cell
        
        result = _run_async(mcp_client.call_mcp("read_data_from_excel", params))
        return f"Data read successfully: {result}"
    except Exception as e:
        return f"Error reading data: {str(e)}"


@tool
def merge_cells(filepath: str, sheet_name: str, start_cell: str, end_cell: str) -> str:
    """Merge a range of cells."""
    try:
        result = _run_async(mcp_client.call_mcp(
            "merge_cells",
            {
                "filepath": filepath,
                "sheet_name": sheet_name,
                "start_cell": start_cell,
                "end_cell": end_cell
            }
        ))
        return "Cells merged successfully"
    except Exception as e:
        return f"Error merging cells: {str(e)}"


@tool
def unmerge_cells(filepath: str, sheet_name: str, start_cell: str, end_cell: str) -> str:
    """Unmerge a previously merged range of cells."""
    try:
        result = _run_async(mcp_client.call_mcp(
            "unmerge_cells",
            {
                "filepath": filepath,
                "sheet_name": sheet_name,
                "start_cell": start_cell,
                "end_cell": end_cell
            }
        ))
        return "Cells unmerged successfully"
    except Exception as e:
        return f"Error unmerging cells: {str(e)}"


@tool
def apply_formula(filepath: str, sheet_name: str, cell: str, formula: str) -> str:
    """Apply Excel formula to cell."""
    try:
        result = _run_async(mcp_client.call_mcp(
            "apply_formula",
            {
                "filepath": filepath,
                "sheet_name": sheet_name,
                "cell": cell,
                "formula": formula
            }
        ))
        return f"Formula applied successfully to {cell}"
    except Exception as e:
        return f"Error applying formula: {str(e)}"


@tool
def validate_formula_syntax(filepath: str, sheet_name: str, cell: str, formula: str) -> str:
    """Validate Excel formula syntax without applying it."""
    try:
        result = _run_async(mcp_client.call_mcp(
            "validate_formula_syntax",
            {
                "filepath": filepath,
                "sheet_name": sheet_name,
                "cell": cell,
                "formula": formula
            }
        ))
        return f"Formula validation result: {result}"
    except Exception as e:
        return f"Error validating formula: {str(e)}"


@tool
def create_chart(filepath: str, sheet_name: str, data_range: str, chart_type: str,
                 target_cell: str, title: str = "", x_axis: str = "", y_axis: str = "") -> str:
    """Create chart in worksheet."""
    try:
        params = {
            "filepath": filepath,
            "sheet_name": sheet_name,
            "data_range": data_range,
            "chart_type": chart_type,
            "target_cell": target_cell
        }
        if title:
            params["title"] = title
        if x_axis:
            params["x_axis"] = x_axis
        if y_axis:
            params["y_axis"] = y_axis
        
        result = _run_async(mcp_client.call_mcp("create_chart", params))
        return f"Chart created successfully at {target_cell}"
    except Exception as e:
        return f"Error creating chart: {str(e)}"


@tool
def create_pivot_table(filepath: str, sheet_name: str, data_range: str, target_cell: str,
                       rows: list, values: list, columns: list = None, agg_func: str = "mean") -> str:
    """Create pivot table in worksheet."""
    try:
        params = {
            "filepath": filepath,
            "sheet_name": sheet_name,
            "data_range": data_range,
            "target_cell": target_cell,
            "rows": rows,
            "values": values,
            "agg_func": agg_func
        }
        if columns:
            params["columns"] = columns
        
        result = _run_async(mcp_client.call_mcp("create_pivot_table", params))
        return "Pivot table created successfully"
    except Exception as e:
        return f"Error creating pivot table: {str(e)}"


@tool
def copy_worksheet(filepath: str, source_sheet: str, target_sheet: str) -> str:
    """Copy worksheet within workbook."""
    try:
        result = _run_async(mcp_client.call_mcp(
            "copy_worksheet",
            {
                "filepath": filepath,
                "source_sheet": source_sheet,
                "target_sheet": target_sheet
            }
        ))
        return f"Worksheet '{source_sheet}' copied to '{target_sheet}' successfully"
    except Exception as e:
        return f"Error copying worksheet: {str(e)}"


@tool
def delete_worksheet(filepath: str, sheet_name: str) -> str:
    """Delete worksheet from workbook."""
    try:
        result = _run_async(mcp_client.call_mcp(
            "delete_worksheet",
            {"filepath": filepath, "sheet_name": sheet_name}
        ))
        return f"Worksheet '{sheet_name}' deleted successfully"
    except Exception as e:
        return f"Error deleting worksheet: {str(e)}"


@tool
def rename_worksheet(filepath: str, old_name: str, new_name: str) -> str:
    """Rename worksheet in workbook."""
    try:
        result = _run_async(mcp_client.call_mcp(
            "rename_worksheet",
            {
                "filepath": filepath,
                "old_name": old_name,
                "new_name": new_name
            }
        ))
        return f"Worksheet renamed from '{old_name}' to '{new_name}' successfully"
    except Exception as e:
        return f"Error renaming worksheet: {str(e)}"


@tool
def copy_range(filepath: str, sheet_name: str, source_start: str, source_end: str,
               target_start: str, target_sheet: str = None) -> str:
    """Copy a range of cells to another location."""
    try:
        params = {
            "filepath": filepath,
            "sheet_name": sheet_name,
            "source_start": source_start,
            "source_end": source_end,
            "target_start": target_start
        }
        if target_sheet:
            params["target_sheet"] = target_sheet
        
        result = _run_async(mcp_client.call_mcp("copy_range", params))
        return "Range copied successfully"
    except Exception as e:
        return f"Error copying range: {str(e)}"


@tool
def delete_range(filepath: str, sheet_name: str, start_cell: str, end_cell: str,
                 shift_direction: str = "up") -> str:
    """Delete a range of cells and shift remaining cells."""
    try:
        result = _run_async(mcp_client.call_mcp(
            "delete_range",
            {
                "filepath": filepath,
                "sheet_name": sheet_name,
                "start_cell": start_cell,
                "end_cell": end_cell,
                "shift_direction": shift_direction
            }
        ))
        return "Range deleted successfully"
    except Exception as e:
        return f"Error deleting range: {str(e)}"


@tool
def validate_excel_range(filepath: str, sheet_name: str, start_cell: str, end_cell: str = None) -> str:
    """Validate if a range exists and is properly formatted."""
    try:
        params = {
            "filepath": filepath,
            "sheet_name": sheet_name,
            "start_cell": start_cell
        }
        if end_cell:
            params["end_cell"] = end_cell
        
        result = _run_async(mcp_client.call_mcp("validate_excel_range", params))
        return f"Range validation result: {result}"
    except Exception as e:
        return f"Error validating range: {str(e)}"


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
    
    prompt = f"""Сгенерируй {num_rows} строк реалистичных данных российских людей со следующими заголовками: {headers}
    
Требования:
- Имя (Name): Русские имена
- Фамилия (Last name): Русские фамилии
- Пол (Gender): М (мужской) или Ж (женский)
- Возраст (Age): Возраст от 18 до 80 лет


Верни данные как список списков Python в точно таком формате (без markdown, только raw Python):
[['Иван', 'Попов', 'М', 24], ['Елена', 'Фролова', 'Ж', 32], ...]


Не включай заголовки в вывод, только строки данных. Сгенерируй ровно {num_rows} строк.
"""

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
        # Workbook operations
        create_workbook,
        create_worksheet,
        get_workbook_metadata,
        
        # Data operations
        write_data_to_excel,
        read_data_from_excel,
        
        # Formatting operations
        format_range,
        merge_cells,
        unmerge_cells,
        
        # Formula operations
        apply_formula,
        validate_formula_syntax,
        
        # Chart operations
        create_chart,
        
        # Pivot table operations
        create_pivot_table,
        
        # Worksheet operations
        copy_worksheet,
        delete_worksheet,
        rename_worksheet,
        
        # Range operations
        copy_range,
        delete_range,
        validate_excel_range
    ]
    
    llm = create_llm_client()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Ты ассистент, который помогает пользователю решать задачи с помощью электронных таблиц.
Твоя задача производить действия c Excel-файлами по шагам согласно плану, описанному в промпте.
Используй доступные инструменты для выполнения каждого этапа. Всегда проверяй что этап завершился успешно при переходе к следующему."""),
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
    # data_rows = generate_data_with_llm(num_rows)
    
    # print(f"Headers: {headers}")
    # print(f"Data rows generated: {len(data_rows)}")
    # print(f"Sample data: {data_rows[0] if data_rows else 'No data'}")
    
    # Create agent
    agent_executor = create_agent()
    
    # Prepare the task with specific instructions
    task = f"""Создай файл Excel со следующими спецификациями:

1. Создать рабочую книгу: {filepath}
2. Создать лист: "Data"
3. Написать данные с заголовками и {num_rows} строками:
   Строка заголовков: {headers}
   Строки данных: Синтезируй правдоподобные данные, соответствующие заголовкам. Примеры: ['Иван', 'Попов', 'М', 24], ['Елена', 'Фролова', 'Ж', 32]
4. Форматировать строку заголовков (ряд 1):
   - Цвет фона: 0070C0 (синий)
   - Цвет шрифта: FFFFFF (белый)
   - Жирный текст
   Остальные параметров форматирования не инициализируй значениями
5. Форматировать строки данных (все ряды со 2 по {num_rows + 1}) чередующимися цветами:
   - Нечетные строки: фон FFFFFF (белый)
   - Четные строки: фон D3D3D3 (светло-серый)
   Остальные параметров форматирования не инициализируй значениями

Выполни каждый шаг по порядку. Используй путь файла "{filepath}" для всех операций.
"""
    
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
    main(num_rows=5)
