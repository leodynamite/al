#!/usr/bin/env python3
"""
Telegram Mini App Server
Простой HTTP сервер для обслуживания Mini App
"""

import http.server
import socketserver
import os
import json
from urllib.parse import urlparse, parse_qs
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MiniAppHandler(http.server.SimpleHTTPRequestHandler):
    """Обработчик запросов для Mini App"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(__file__), **kwargs)
    
    def do_GET(self):
        """Обработка GET запросов"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            with open('index.html', 'r', encoding='utf-8') as f:
                self.wfile.write(f.read().encode('utf-8'))
        elif parsed_path.path == '/api/metrics':
            self.handle_metrics()
        elif parsed_path.path == '/api/upload':
            self.handle_upload()
        elif parsed_path.path == '/api/generate-script':
            self.handle_generate_script()
        else:
            super().do_GET()
    
    def do_POST(self):
        """Обработка POST запросов"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/upload':
            self.handle_upload_post()
        elif parsed_path.path == '/api/generate-script':
            self.handle_generate_script_post()
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_metrics(self):
        """Получение метрик"""
        try:
            # Симуляция данных метрик
            metrics = {
                'total_leads': 47,
                'hot_leads': 12,
                'conversion_rate': 25.5,
                'meetings_scheduled': 8,
                'today_leads': 5,
                'this_week_leads': 23
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(metrics).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error handling metrics: {e}")
            self.send_response(500)
            self.end_headers()
    
    def handle_upload(self):
        """Обработка загрузки файла (GET)"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            'status': 'ready',
            'supported_formats': ['.csv', '.xlsx', '.xls', '.pdf', '.docx', '.txt'],
            'max_size': '10MB'
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def handle_upload_post(self):
        """Обработка загрузки файла (POST)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Симуляция обработки файла
            response = {
                'status': 'success',
                'message': 'Файл успешно обработан',
                'analysis': {
                    'contacts_found': 25,
                    'leads_identified': 12,
                    'hot_leads': 3
                }
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error handling upload: {e}")
            self.send_response(500)
            self.end_headers()
    
    def handle_generate_script(self):
        """Генерация скрипта (GET)"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Шаблон скрипта
        script_template = {
            'questions': [
                {
                    'id': 'q1',
                    'text': 'В каком районе вы ищете недвижимость?',
                    'type': 'text',
                    'mandatory': True,
                    'weight': 20
                },
                {
                    'id': 'q2',
                    'text': 'Какой у вас бюджет?',
                    'type': 'text',
                    'mandatory': True,
                    'weight': 30
                },
                {
                    'id': 'q3',
                    'text': 'Когда планируете покупку?',
                    'type': 'choice',
                    'options': ['В течение месяца', 'В течение 3 месяцев', 'В течение года', 'Пока присматриваюсь'],
                    'mandatory': True,
                    'weight': 25
                }
            ]
        }
        
        self.wfile.write(json.dumps(script_template).encode('utf-8'))
    
    def handle_generate_script_post(self):
        """Генерация скрипта (POST)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Симуляция генерации скрипта на основе ответов
            script = generate_script_from_answers(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(script).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error generating script: {e}")
            self.send_response(500)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Переопределение логирования для более чистого вывода"""
        pass

def generate_script_from_answers(answers):
    """Генерация скрипта на основе ответов пользователя"""
    
    # Базовый скрипт
    base_script = [
        {
            'id': 'q1',
            'text': 'В каком районе вы ищете недвижимость?',
            'type': 'text',
            'mandatory': True,
            'weight': 20
        },
        {
            'id': 'q2',
            'text': 'Какой у вас бюджет?',
            'type': 'text',
            'mandatory': True,
            'weight': 30
        }
    ]
    
    # Адаптация скрипта на основе ответов
    if answers.get('business_type') == 'Новостройка':
        base_script.append({
            'id': 'q3',
            'text': 'Интересуют ли вас новостройки с отделкой?',
            'type': 'choice',
            'options': ['Да, с отделкой', 'Нет, без отделки', 'Не важно'],
            'mandatory': True,
            'weight': 25
        })
    elif answers.get('business_type') == 'Аренда':
        base_script.append({
            'id': 'q3',
            'text': 'На какой срок планируете аренду?',
            'type': 'choice',
            'options': ['До 1 года', '1-3 года', 'Более 3 лет'],
            'mandatory': True,
            'weight': 25
        })
    
    # Добавление вопроса о срочности
    if answers.get('client_urgency'):
        base_script.append({
            'id': 'q4',
            'text': 'Когда планируете совершить сделку?',
            'type': 'choice',
            'options': ['В течение месяца', 'В течение 3 месяцев', 'В течение года', 'Пока присматриваюсь'],
            'mandatory': True,
            'weight': 20
        })
    
    # Контактная информация
    base_script.append({
        'id': 'q5',
        'text': 'Как с вами лучше связаться?',
        'type': 'choice',
        'options': ['Телефон', 'WhatsApp', 'Telegram', 'Email'],
        'mandatory': True,
        'weight': 10
    })
    
    return {
        'questions': base_script,
        'recommendations': [
            'Используйте открытые вопросы для лучшего понимания потребностей',
            'Задавайте вопросы о бюджете в середине диалога',
            'Всегда уточняйте контактные данные в конце'
        ]
    }

def main():
    """Запуск сервера"""
    PORT = int(os.environ.get('PORT', 8080))
    
    with socketserver.TCPServer(("", PORT), MiniAppHandler) as httpd:
        logger.info(f"Mini App сервер запущен на порту {PORT}")
        logger.info(f"Откройте http://localhost:{PORT} в браузере")
        logger.info("Нажмите Ctrl+C для остановки")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Сервер остановлен")

if __name__ == "__main__":
    main()
