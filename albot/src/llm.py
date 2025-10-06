"""
LLM integration for script generation and analysis.
"""
import json
import httpx
from typing import Dict, Any, List, Optional
from .config import LLMConfig


class LLMClient:
    """Client for LLM API interactions."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def _chat_json(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Send chat request and return JSON response."""
        try:
            response = await self.client.post(
                "/v1/chat/completions",
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            # Fallback to universal script
            return self._get_universal_script()
    
    def _get_universal_script(self) -> Dict[str, Any]:
        """Fallback universal script when LLM fails."""
        return {
            "profile": {
                "object_type": "Недвижимость",
                "avg_check": "Средний",
                "target_audience": "Покупатели недвижимости",
                "sales_channel": "Онлайн",
                "weaknesses": ["Недостаточно данных"]
            },
            "script": [
                {
                    "order": 1,
                    "text": "Какой тип недвижимости вас интересует?",
                    "type": "choice",
                    "mandatory": True,
                    "purpose": "Определение типа объекта"
                },
                {
                    "order": 2,
                    "text": "Какой у вас бюджет?",
                    "type": "text",
                    "mandatory": True,
                    "purpose": "Оценка финансовых возможностей"
                },
                {
                    "order": 3,
                    "text": "В каком районе предпочитаете?",
                    "type": "text",
                    "mandatory": False,
                    "purpose": "Определение локации"
                }
            ],
            "recommendations": [
                "Задавайте открытые вопросы",
                "Уточняйте детали",
                "Предлагайте варианты"
            ]
        }
    
    async def analyze_agency(self, content: str) -> Dict[str, Any]:
        """Analyze agency data and generate script."""
        system_prompt = """Ты эксперт по лидогенерации в недвижимости. 
        Задача — проанализировать данные агентства и выдать краткий профиль (3–5 пунктов) 
        и предложить оптимальный скрипт диалога с клиентом."""
        
        user_prompt = f"""Вот данные агентства (raw_text_or_table): {content}
        
        Instruction: 
        1) Сформируй профиль: тип объекта, средний чек, основная целевая аудитория, основной канал продаж, слабые места (до 3).
        2) Сгенерируй скрипт из 6 вопросов для первичной квалификации: в порядке, с пояснениями зачем вопрос. Пометь какие вопросы — обязательные.
        3) Предложи 3 quick-win совета (до 20 слов каждый).
        
        Return JSON:
        {{
            "profile": {{...}},
            "script": [
                {{"order":1,"text":"...","type":"choice/text/date","mandatory":true,"purpose":"..."}},
                ...
            ],
            "recommendations":["...","...","..."]
        }}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._chat_json(messages)
    
    async def script_from_answers(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Generate script from onboarding answers."""
        system_prompt = """Ты LLM-ассистент для создания скриптов."""
        
        user_prompt = f"""На основе ответов напиши скрипт из 4–6 вопросов.
        Ответы: {answers}
        
        Для каждого вопроса дай: тип ответа (text/number/choice/date), 
        примеры возможных клиентских ответов, признак "горячий" (если ответ указывает на высокий lead_score).
        
        Return JSON:
        {{
            "script": [...],
            "rules_for_scoring": {{...}}
        }}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._chat_json(messages)
    
    async def optimize_script(self, script: Dict[str, Any], dialogues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize script based on dialogue statistics."""
        system_prompt = """Ты аналитик диалогов."""
        
        user_prompt = f"""Даны: скрипт и 200 диалогов (в виде JSON messages).
        Скрипт: {script}
        Диалоги: {dialogues}
        
        Проанализируй эффективность каждого вопроса (response rate, time to answer, % горячих ответов). 
        Предложи до 5 изменений с rationale.
        
        Return JSON:
        {{
            "metrics_by_question": {{...}},
            "suggestions":[{{"change":"...","expected_effect":"..."}}]
        }}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._chat_json(messages)
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text using LLM."""
        system_prompt = """Ты эксперт по извлечению сущностей из текста о недвижимости."""
        
        user_prompt = f"""Извлеки из текста следующие сущности:
        - Budget (бюджет)
        - Region (регион/район)
        - ObjectType (тип объекта)
        - Contact (контактная информация)
        
        Текст: {text}
        
        Return JSON:
        {{
            "budget": "...",
            "region": "...",
            "object_type": "...",
            "contact": "..."
        }}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return await self._chat_json(messages)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
