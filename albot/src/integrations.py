from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx
import smtplib
from email.message import EmailMessage


@dataclass
class Lead:
    name: str
    contact: str
    source: str


class AmoCRMClient:
    """amoCRM API client"""
    
    def __init__(self, subdomain: str, client_id: str, client_secret: str, redirect_uri: str):
        self.subdomain = subdomain
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = f"https://{subdomain}.amocrm.ru"
        self.access_token = None
        self.refresh_token = None
    
    async def get_auth_url(self, user_id: int) -> str:
        """Get amoCRM OAuth authorization URL"""
        return f"{self.base_url}/oauth/authorize?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state={user_id}"
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/oauth2/access_token",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                return data
            else:
                raise Exception(f"Failed to get tokens: {response.text}")
    
    async def save_lead(self, lead_data: Dict[str, Any]) -> str:
        """Save lead to amoCRM"""
        if not self.access_token:
            raise Exception("Not authenticated with amoCRM")
        
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Prepare lead data for amoCRM
            lead_payload = {
                "name": lead_data.get("name", "Новый лид"),
                "price": lead_data.get("budget", 0),
                "responsible_user_id": 0,  # Will be assigned automatically
                "pipeline_id": 0,  # Default pipeline
                "custom_fields_values": [
                    {
                        "field_id": 0,  # Phone field
                        "values": [{"value": lead_data.get("phone", "")}]
                    },
                    {
                        "field_id": 1,  # Email field
                        "values": [{"value": lead_data.get("email", "")}]
                    }
                ]
            }
            
            response = await client.post(
                f"{self.base_url}/api/v4/leads",
                headers=headers,
                json=[lead_payload]
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["_embedded"]["leads"][0]["id"]
            else:
                raise Exception(f"Failed to save lead: {response.text}")
    
    async def update_lead_status(self, lead_id: str, status_id: int) -> bool:
        """Update lead status in amoCRM"""
        if not self.access_token:
            raise Exception("Not authenticated with amoCRM")
        
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = await client.patch(
                f"{self.base_url}/api/v4/leads/{lead_id}",
                headers=headers,
                json=[{
                    "id": int(lead_id),
                    "status_id": status_id
                }]
            )
            
            return response.status_code == 200


class Bitrix24Client:
    """Bitrix24 API client"""
    
    def __init__(self, domain: str, client_id: str, client_secret: str):
        self.domain = domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = f"https://{domain}.bitrix24.ru"
        self.access_token = None
    
    async def get_auth_url(self, user_id: int) -> str:
        """Get Bitrix24 OAuth authorization URL"""
        return f"{self.base_url}/oauth/authorize?client_id={self.client_id}&response_type=code&state={user_id}"
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                return data
            else:
                raise Exception(f"Failed to get tokens: {response.text}")
    
    async def save_lead(self, lead_data: Dict[str, Any]) -> str:
        """Save lead to Bitrix24"""
        if not self.access_token:
            raise Exception("Not authenticated with Bitrix24")
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Prepare lead data for Bitrix24
            lead_payload = {
                "TITLE": lead_data.get("name", "Новый лид"),
                "NAME": lead_data.get("name", ""),
                "PHONE": [{"VALUE": lead_data.get("phone", ""), "VALUE_TYPE": "WORK"}],
                "EMAIL": [{"VALUE": lead_data.get("email", ""), "VALUE_TYPE": "WORK"}],
                "OPPORTUNITY": lead_data.get("budget", 0),
                "SOURCE_ID": "WEB",  # Source
                "COMMENTS": lead_data.get("comment", "")
            }
            
            response = await client.post(
                f"{self.base_url}/rest/crm.lead.add",
                params={
                    "auth": self.access_token,
                    "fields": lead_payload
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("result"):
                    return str(data["result"])
                else:
                    raise Exception(f"Failed to save lead: {data}")
            else:
                raise Exception(f"Failed to save lead: {response.text}")
    
    async def update_lead_status(self, lead_id: str, status_id: str) -> bool:
        """Update lead status in Bitrix24"""
        if not self.access_token:
            raise Exception("Not authenticated with Bitrix24")
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/rest/crm.lead.update",
                params={
                    "auth": self.access_token,
                    "id": lead_id,
                    "fields": {
                        "STATUS_ID": status_id
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("result", False)
            else:
                return False


class CRMClient:
    """Unified CRM client"""
    
    def __init__(self, crm_type: str, **kwargs):
        self.crm_type = crm_type
        if crm_type == "amocrm":
            self.client = AmoCRMClient(**kwargs)
        elif crm_type == "bitrix24":
            self.client = Bitrix24Client(**kwargs)
        else:
            raise ValueError(f"Unsupported CRM type: {crm_type}")
    
    async def get_auth_url(self, user_id: int) -> str:
        """Get CRM OAuth authorization URL"""
        return await self.client.get_auth_url(user_id)
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        return await self.client.exchange_code_for_tokens(code)
    
    async def save_lead(self, lead_data: Dict[str, Any]) -> str:
        """Save lead to CRM"""
        return await self.client.save_lead(lead_data)
    
    async def update_lead_status(self, lead_id: str, status_id: str) -> bool:
        """Update lead status in CRM"""
        return await self.client.update_lead_status(lead_id, status_id)


class SheetsClient:
    async def append_row(self, row: Dict[str, Any]) -> None:
        return None


class CalendarClient:
    async def create_event(self, summary: str, when: str) -> str:
        return "event_123"


async def push_hot_lead_to_manager(lead: Lead) -> None:
    # Заглушка отправки пуша менеджеру
    return None


class YandexCalendarOAuth:
    def __init__(self, client_id: str, client_secret: str, token_url: str, api_base: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.api_base = api_base

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(self.token_url, data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": redirect_uri,
            })
            resp.raise_for_status()
            return resp.json()

    async def create_event(self, access_token: str, summary: str, start_iso: str, end_iso: str) -> str:
        headers = {"Authorization": f"OAuth {access_token}", "Content-Type": "application/json"}
        payload = {"summary": summary, "start": {"dateTime": start_iso}, "end": {"dateTime": end_iso}}
        async with httpx.AsyncClient(base_url=self.api_base, timeout=20, headers=headers) as client:
            # Эндпоинт может отличаться; потребуется уточнение по Yandex Calendar API
            resp = await client.post("/v1/calendars/events", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("id", ""))

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(self.token_url, data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            })
            resp.raise_for_status()
            return resp.json()

    async def revoke(self, access_token: str) -> bool:
        # У Яндекса отзыв делается через settings или отдельный endpoint; оставим заглушку true
        return True

    async def find_next_free_slot(self, access_token: str, start_from_iso: str, duration_minutes: int = 30) -> Dict[str, str] | None:
        # Упростим: возвращаем слот +30 минут от start_from_iso как доступный
        # В реальности нужно опрашивать занятость через API.
        from datetime import datetime, timedelta
        try:
            dt = datetime.fromisoformat(start_from_iso.replace("Z", "+00:00"))
            end = dt + timedelta(minutes=duration_minutes)
            return {"start": dt.isoformat(), "end": end.isoformat()}
        except Exception:
            return None


class AmoCRMClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url
        self.token = token

    async def create_lead(self, payload: Dict[str, Any]) -> str:
        return "amocrm_123"


class Bitrix24Client:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url
        self.token = token

    async def create_lead(self, payload: Dict[str, Any]) -> str:
        return "bitrix_123"


async def generic_webhook(url: str, payload: Dict[str, Any]) -> bool:
    return True


def send_email_smtp(host: str, port: int, user: str, password: str, to_list: List[str], subject: str, body: str) -> bool:
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = ", ".join(to_list)
        msg.set_content(body)
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        return False


class SupabaseClient:
    """Supabase client for database operations"""
    
    def __init__(self, url: str, anon_key: str, encryption_key: str = None):
        self.url = url
        self.anon_key = anon_key
        self.encryption_key = encryption_key
        # TODO: Initialize Supabase client
    
    async def save_lead(self, lead: Dict[str, Any]) -> bool:
        """Save lead to database with encryption"""
        # TODO: Implement lead saving with encryption
        return True
    
    async def delete_user_data(self, user_id: int) -> bool:
        """Delete all user data (GDPR compliance)"""
        # TODO: Implement user data deletion
        return True
    
    # Billing methods
    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user subscription"""
        # TODO: Implement subscription retrieval
        return None
    
    async def save_subscription(self, subscription: Dict[str, Any]) -> bool:
        """Save subscription"""
        # TODO: Implement subscription saving
        return True
    
    async def update_subscription(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update subscription"""
        # TODO: Implement subscription update
        return True
    
    async def increment_dialog_count(self, user_id: int) -> bool:
        """Increment dialog count"""
        # TODO: Implement dialog count increment
        return True
    
    # Analytics methods
    async def save_analytics_events(self, events: List[Dict[str, Any]]) -> bool:
        """Save analytics events to Supabase"""
        try:
            # TODO: Implement Supabase analytics events saving
            # Example structure for events table:
            # CREATE TABLE analytics_events (
            #   id SERIAL PRIMARY KEY,
            #   event_type VARCHAR(50) NOT NULL,
            #   user_id BIGINT NOT NULL,
            #   timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            #   metadata JSONB,
            #   session_id VARCHAR(100)
            # );
            return True
        except Exception as e:
            print(f"Error saving analytics events: {e}")
            return False
    
    async def get_user_metrics(self, user_id: int) -> Dict[str, Any]:
        """Get user metrics from Supabase"""
        try:
            # TODO: Implement user metrics retrieval from Supabase
            # Example queries:
            # - dialogs_today: COUNT(*) WHERE event_type='dialog_completed' AND DATE(timestamp)=CURRENT_DATE
            # - dialogs_week: COUNT(*) WHERE event_type='dialog_completed' AND timestamp >= NOW() - INTERVAL '7 days'
            # - hot_leads: COUNT(*) WHERE event_type='lead_scored' AND metadata->>'status'='hot'
            # - meetings_scheduled: COUNT(*) WHERE event_type='lead_booked'
            
            # Placeholder data for now
            return {
                "dialogs_today": 5,
                "dialogs_week": 23,
                "hot_leads": 3,
                "meetings_scheduled": 2,
                "leads_created": 15,
                "conversion_rate": 0.2,
                "avg_lead_score": 65
            }
        except Exception as e:
            print(f"Error getting user metrics: {e}")
            return {}
    
    async def get_global_metrics(self) -> Dict[str, Any]:
        """Get global metrics"""
        # TODO: Implement global metrics retrieval
        return {}
    
    async def get_conversion_funnel(self, user_id: int) -> Dict[str, Any]:
        """Get conversion funnel"""
        # TODO: Implement conversion funnel retrieval
        return {}
    
    async def export_metrics_json(self) -> str:
        """Export metrics as JSON"""
        # TODO: Implement metrics export
        return "{}"
    
    async def export_metrics_csv(self) -> str:
        """Export metrics as CSV"""
        # TODO: Implement CSV export
        return ""
    
    # Monitoring methods
    async def get_error_rate(self, minutes: int = 5) -> float:
        """Get error rate for specified minutes"""
        # TODO: Implement error rate calculation
        return 0.0
    
    async def get_critical_errors(self, minutes: int = 5) -> int:
        """Get count of critical errors (500, timeouts)"""
        # TODO: Implement critical errors counting
        return 0
    
    async def get_crm_error_rate(self, minutes: int = 5) -> float:
        """Get CRM API error rate"""
        # TODO: Implement CRM error rate calculation
        return 0.0
    
    async def get_consecutive_crm_errors(self) -> int:
        """Get count of consecutive CRM errors"""
        # TODO: Implement consecutive CRM errors counting
        return 0
    
    async def get_message_queue_size(self) -> int:
        """Get message queue size"""
        # TODO: Implement queue size retrieval
        return 0
    
    async def get_message_queue_rate(self, minutes: int = 5) -> int:
        """Get message queue processing rate"""
        # TODO: Implement queue rate calculation
        return 0
    
    async def get_llm_token_usage(self, hours: int = 1) -> Dict[int, int]:
        """Get LLM token usage by user"""
        # TODO: Implement token usage tracking
        return {}
    
    async def get_active_users_count(self) -> int:
        """Get active users count"""
        # TODO: Implement active users count
        return 0
    
    async def get_dialogs_count_today(self) -> int:
        """Get dialogs count for today"""
        # TODO: Implement dialogs count
        return 0
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve alert"""
        # TODO: Implement alert resolution
        return True


# Google Sheets integration
class GoogleSheetsIntegration:
    """Google Sheets integration for data export"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    
    async def get_auth_url(self, user_id: int) -> str:
        """Get Google OAuth authorization URL"""
        # Simplified implementation
        return f"https://accounts.google.com/o/oauth2/auth?client_id={self.client_id}&redirect_uri={self.redirect_uri}&scope=https://www.googleapis.com/auth/spreadsheets&response_type=code&state={user_id}"
    
    async def export_leads(self, user_id: int, leads: List[Dict[str, Any]]) -> str:
        """Export leads to Google Sheets"""
        # Simplified implementation - would create actual spreadsheet
        spreadsheet_id = f"spreadsheet_{user_id}_{int(datetime.now().timestamp())}"
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    
    async def check_integration(self, user_id: int) -> bool:
        """Check if user has Google Sheets integration"""
        # Simplified implementation - would check database
        return False


class EmailNotificationService:
    """Email notification service for hot leads"""
    
    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
    
    async def send_hot_lead_notification(self, lead_data: Dict[str, Any], manager_email: str) -> bool:
        """Send hot lead notification to manager"""
        try:
            # Create HTML email template
            html_body = self._create_hot_lead_email_template(lead_data)
            
            # Create email message
            msg = EmailMessage()
            msg['Subject'] = f"🔥 HOT ЛИД: {lead_data.get('name', 'Неизвестно')}"
            msg['From'] = self.smtp_user
            msg['To'] = manager_email
            msg.set_content(html_body, subtype='html')
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Failed to send hot lead notification: {e}")
            return False
    
    def _create_hot_lead_email_template(self, lead_data: Dict[str, Any]) -> str:
        """Create HTML email template for hot lead"""
        name = lead_data.get('name', 'Неизвестно')
        phone = lead_data.get('phone', 'Не указан')
        email = lead_data.get('email', 'Не указан')
        score = lead_data.get('score', 0)
        budget = lead_data.get('budget', 'Не указан')
        source = lead_data.get('source', 'Telegram')
        created_at = lead_data.get('created_at', 'Только что')
        
        # Status emoji based on score
        status_emoji = "🔥" if score >= 70 else "🟡" if score >= 40 else "❄️"
        status_text = "HOT" if score >= 70 else "WARM" if score >= 40 else "COLD"
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #ff6b6b, #ff8e8e); color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ padding: 30px; }}
                .lead-info {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .field {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #333; }}
                .value {{ color: #666; }}
                .score {{ font-size: 24px; font-weight: bold; color: #ff6b6b; }}
                .actions {{ margin-top: 30px; text-align: center; }}
                .btn {{ display: inline-block; padding: 12px 24px; margin: 5px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
                .btn:hover {{ background: #0056b3; }}
                .footer {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px; text-align: center; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{status_emoji} {status_text} ЛИД</h1>
                    <p>Новый горячий лид требует внимания!</p>
                </div>
                
                <div class="content">
                    <div class="lead-info">
                        <div class="field">
                            <span class="label">👤 Имя:</span>
                            <span class="value">{name}</span>
                        </div>
                        <div class="field">
                            <span class="label">📞 Телефон:</span>
                            <span class="value">{phone}</span>
                        </div>
                        <div class="field">
                            <span class="label">📧 Email:</span>
                            <span class="value">{email}</span>
                        </div>
                        <div class="field">
                            <span class="label">💰 Бюджет:</span>
                            <span class="value">{budget}</span>
                        </div>
                        <div class="field">
                            <span class="label">📊 Score:</span>
                            <span class="score">{score}</span>
                        </div>
                        <div class="field">
                            <span class="label">🌐 Источник:</span>
                            <span class="value">{source}</span>
                        </div>
                        <div class="field">
                            <span class="label">⏰ Время:</span>
                            <span class="value">{created_at}</span>
                        </div>
                    </div>
                    
                    <div class="actions">
                        <a href="tel:{phone}" class="btn">📞 Позвонить</a>
                        <a href="mailto:{email}" class="btn">📧 Написать</a>
                        <a href="https://t.me/your_bot" class="btn">💬 Telegram</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Это уведомление отправлено автоматически AL Bot</p>
                    <p>Не отвечайте на это письмо</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template


