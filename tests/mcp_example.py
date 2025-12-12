import uuid
import asyncio
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

async def create_worksheet_http():
    """
    Вызов create_worksheet через HTTP транспорт с использованием FastMCP
    Это рекомендуемый способ для удаленного подключения
    
    Перед запуском, запустите сервер:
    EXCEL_FILES_PATH=/path/to/excel_files FASTMCP_PORT=8000 uvx excel-mcp-server streamable-http
    """
    
    # Создаем транспорт HTTP
    transport = StreamableHttpTransport(
        url="https://excel.ai-gateway.ru/mcp"
    )
    
    file_uuid = str(uuid.uuid4())
    filepath = f"{file_uuid}.xlsx"

    # Создаем клиент
    client = Client(transport)
    
    async with client:
        result = await client.call_tool(
            name="create_workbook",
            arguments={
                "filepath": filepath
            }
        )
        print("Result:", result)


        # Вызываем инструмент create_worksheet
        result = await client.call_tool(
            name="create_worksheet",
            arguments={
                "filepath": filepath,
                "sheet_name": "New Sheet"
            }
        )
        print("Result:", result)

# Запуск
if __name__ == "__main__":
    asyncio.run(create_worksheet_http())
