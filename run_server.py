#!/usr/bin/env python3
"""
Запуск Mini App сервера
"""

import subprocess
import sys
import os

def main():
    """Запуск сервера Mini App"""
    print("🚀 Запуск Telegram Mini App сервера...")
    print("📱 Откройте http://localhost:8080 в браузере")
    print("🤖 Убедитесь, что основной бот запущен")
    print("⏹️  Нажмите Ctrl+C для остановки")
    print("-" * 50)
    
    try:
        # Запуск сервера
        subprocess.run([sys.executable, "server.py"], cwd=os.path.dirname(__file__))
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")

if __name__ == "__main__":
    main()
