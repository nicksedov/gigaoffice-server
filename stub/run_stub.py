#!/usr/bin/env python3
"""
Скрипт запуска сервиса-заглушки GigaOffice
"""

import uvicorn
import sys
import os

def main():
    port = 9060

    """Запуск сервиса-заглушки"""
    print("=" * 60)
    print("🚀 Запуск GigaOffice Stub Service")
    print("=" * 60)
    print(f"📍 URL: http://localhost:{port}")
    print(f"📖 Документация: http://localhost:{port}/docs")
    print(f"🔧 ReDoc: http://localhost:{port}/redoc")
    print(f"❤️  Health: http://localhost:{port}/api/health")
    print("=" * 60)
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Сервис остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
