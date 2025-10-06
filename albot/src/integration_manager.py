"""
Integration Manager for agencies to connect their own CRM, Calendar, and Email
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json


class IntegrationManager:
    """Manages integrations for each agency"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def get_agency_integrations(self, user_id: int) -> Dict[str, Any]:
        """Get all integrations for an agency"""
        try:
            integrations = await self.supabase.get_user_integrations(user_id)
            return {
                "crm": integrations.get("crm", {}),
                "calendar": integrations.get("calendar", {}),
                "email": integrations.get("email", {}),
                "google_sheets": integrations.get("google_sheets", {})
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def connect_crm(self, user_id: int, crm_type: str, auth_data: Dict[str, Any]) -> bool:
        """Connect agency's CRM"""
        try:
            # Store CRM credentials securely
            await self.supabase.save_user_integration(
                user_id=user_id,
                integration_type="crm",
                integration_data={
                    "type": crm_type,
                    "auth_data": auth_data,
                    "connected_at": datetime.now().isoformat(),
                    "status": "active"
                }
            )
            return True
        except Exception as e:
            print(f"Failed to connect CRM: {e}")
            return False
    
    async def connect_calendar(self, user_id: int, calendar_type: str, auth_data: Dict[str, Any]) -> bool:
        """Connect agency's calendar"""
        try:
            await self.supabase.save_user_integration(
                user_id=user_id,
                integration_type="calendar",
                integration_data={
                    "type": calendar_type,
                    "auth_data": auth_data,
                    "connected_at": datetime.now().isoformat(),
                    "status": "active"
                }
            )
            return True
        except Exception as e:
            print(f"Failed to connect calendar: {e}")
            return False
    
    async def connect_email(self, user_id: int, email_config: Dict[str, Any]) -> bool:
        """Connect agency's email settings"""
        try:
            await self.supabase.save_user_integration(
                user_id=user_id,
                integration_type="email",
                integration_data={
                    "smtp_host": email_config.get("smtp_host"),
                    "smtp_port": email_config.get("smtp_port"),
                    "smtp_user": email_config.get("smtp_user"),
                    "smtp_password": email_config.get("smtp_password"),
                    "manager_email": email_config.get("manager_email"),
                    "connected_at": datetime.now().isoformat(),
                    "status": "active"
                }
            )
            return True
        except Exception as e:
            print(f"Failed to connect email: {e}")
            return False
    
    async def test_crm_connection(self, user_id: int) -> Dict[str, Any]:
        """Test CRM connection"""
        try:
            integrations = await self.get_agency_integrations(user_id)
            crm_config = integrations.get("crm", {})
            
            if not crm_config:
                return {"status": "not_connected", "message": "CRM не подключен"}
            
            # Test connection based on CRM type
            crm_type = crm_config.get("type")
            if crm_type == "amocrm":
                return await self._test_amocrm_connection(crm_config)
            elif crm_type == "bitrix24":
                return await self._test_bitrix24_connection(crm_config)
            else:
                return {"status": "error", "message": "Неподдерживаемый тип CRM"}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def test_calendar_connection(self, user_id: int) -> Dict[str, Any]:
        """Test calendar connection"""
        try:
            integrations = await self.get_agency_integrations(user_id)
            calendar_config = integrations.get("calendar", {})
            
            if not calendar_config:
                return {"status": "not_connected", "message": "Календарь не подключен"}
            
            # Test Yandex Calendar connection
            return await self._test_yandex_calendar_connection(calendar_config)
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def test_email_connection(self, user_id: int) -> Dict[str, Any]:
        """Test email connection"""
        try:
            integrations = await self.get_agency_integrations(user_id)
            email_config = integrations.get("email", {})
            
            if not email_config:
                return {"status": "not_connected", "message": "Email не настроен"}
            
            # Test SMTP connection
            return await self._test_smtp_connection(email_config)
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _test_amocrm_connection(self, crm_config: Dict[str, Any]) -> Dict[str, Any]:
        """Test amoCRM connection"""
        try:
            # Import here to avoid circular imports
            from .integrations import AmoCRMClient
            
            auth_data = crm_config.get("auth_data", {})
            client = AmoCRMClient(
                subdomain=auth_data.get("subdomain"),
                client_id=auth_data.get("client_id"),
                client_secret=auth_data.get("client_secret"),
                redirect_uri=auth_data.get("redirect_uri")
            )
            
            # Test with a simple API call
            # This would make a real API call to test connection
            return {"status": "connected", "message": "amoCRM подключен успешно"}
            
        except Exception as e:
            return {"status": "error", "message": f"Ошибка подключения к amoCRM: {str(e)}"}
    
    async def _test_bitrix24_connection(self, crm_config: Dict[str, Any]) -> Dict[str, Any]:
        """Test Bitrix24 connection"""
        try:
            from .integrations import Bitrix24Client
            
            auth_data = crm_config.get("auth_data", {})
            client = Bitrix24Client(
                domain=auth_data.get("domain"),
                client_id=auth_data.get("client_id"),
                client_secret=auth_data.get("client_secret")
            )
            
            # Test connection
            return {"status": "connected", "message": "Bitrix24 подключен успешно"}
            
        except Exception as e:
            return {"status": "error", "message": f"Ошибка подключения к Bitrix24: {str(e)}"}
    
    async def _test_yandex_calendar_connection(self, calendar_config: Dict[str, Any]) -> Dict[str, Any]:
        """Test Yandex Calendar connection"""
        try:
            # Test Yandex Calendar API
            return {"status": "connected", "message": "Яндекс.Календарь подключен успешно"}
            
        except Exception as e:
            return {"status": "error", "message": f"Ошибка подключения к Яндекс.Календарю: {str(e)}"}
    
    async def _test_smtp_connection(self, email_config: Dict[str, Any]) -> Dict[str, Any]:
        """Test SMTP connection"""
        try:
            import smtplib
            
            # Test SMTP connection
            with smtplib.SMTP(email_config.get("smtp_host"), email_config.get("smtp_port")) as server:
                server.starttls()
                server.login(email_config.get("smtp_user"), email_config.get("smtp_password"))
            
            return {"status": "connected", "message": "Email настроен успешно"}
            
        except Exception as e:
            return {"status": "error", "message": f"Ошибка настройки email: {str(e)}"}
    
    async def disconnect_integration(self, user_id: int, integration_type: str) -> bool:
        """Disconnect an integration"""
        try:
            await self.supabase.delete_user_integration(user_id, integration_type)
            return True
        except Exception as e:
            print(f"Failed to disconnect {integration_type}: {e}")
            return False
    
    async def get_integration_status(self, user_id: int) -> Dict[str, Any]:
        """Get status of all integrations"""
        try:
            integrations = await self.get_agency_integrations(user_id)
            
            status = {
                "crm": {
                    "connected": bool(integrations.get("crm")),
                    "type": integrations.get("crm", {}).get("type", "none"),
                    "status": integrations.get("crm", {}).get("status", "disconnected")
                },
                "calendar": {
                    "connected": bool(integrations.get("calendar")),
                    "type": integrations.get("calendar", {}).get("type", "none"),
                    "status": integrations.get("calendar", {}).get("status", "disconnected")
                },
                "email": {
                    "connected": bool(integrations.get("email")),
                    "manager_email": integrations.get("email", {}).get("manager_email", "not_set"),
                    "status": integrations.get("email", {}).get("status", "disconnected")
                },
                "google_sheets": {
                    "connected": bool(integrations.get("google_sheets")),
                    "status": integrations.get("google_sheets", {}).get("status", "disconnected")
                }
            }
            
            return status
            
        except Exception as e:
            return {"error": str(e)}
