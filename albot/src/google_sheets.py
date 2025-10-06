"""
Google Sheets integration for data export
"""
import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import httpx
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    # These will be handled gracefully
    pass


class GoogleSheetsClient:
    """Google Sheets API client"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        
    def get_auth_url(self, user_id: int) -> str:
        """Get Google OAuth authorization URL"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=str(user_id)
        )
        
        return auth_url
    
    async def exchange_code_for_tokens(self, code: str, user_id: int) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes
        )
        flow.redirect_uri = self.redirect_uri
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            return {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expiry.timestamp() if credentials.expiry else None,
                "user_id": user_id
            }
        except Exception as e:
            raise Exception(f"Failed to exchange code for tokens: {str(e)}")
    
    async def create_spreadsheet(self, user_id: int, title: str = "AL Bot Leads") -> str:
        """Create new Google Spreadsheet"""
        try:
            # Get user credentials
            credentials = await self._get_user_credentials(user_id)
            if not credentials:
                raise Exception("User not authenticated with Google")
            
            service = build('sheets', 'v4', credentials=credentials)
            
            # Create spreadsheet
            spreadsheet = {
                'properties': {
                    'title': f"{title} - {datetime.now().strftime('%Y-%m-%d')}"
                },
                'sheets': [{
                    'properties': {
                        'title': 'Leads',
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 10
                        }
                    }
                }]
            }
            
            result = service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = result.get('spreadsheetId')
            
            return spreadsheet_id
            
        except Exception as e:
            raise Exception(f"Failed to create spreadsheet: {str(e)}")
    
    async def export_leads_to_sheets(self, user_id: int, leads: List[Dict[str, Any]], 
                                   spreadsheet_id: Optional[str] = None) -> str:
        """Export leads to Google Sheets"""
        try:
            # Get user credentials
            credentials = await self._get_user_credentials(user_id)
            if not credentials:
                raise Exception("User not authenticated with Google")
            
            service = build('sheets', 'v4', credentials=credentials)
            
            # Create spreadsheet if not provided
            if not spreadsheet_id:
                spreadsheet_id = await self.create_spreadsheet(user_id)
            
            # Prepare data
            headers = ["ID", "Имя", "Телефон", "Email", "Score", "Статус", "Дата создания", "Источник"]
            values = [headers]
            
            for lead in leads:
                row = [
                    lead.get('id', ''),
                    lead.get('name', ''),
                    lead.get('phone', ''),
                    lead.get('email', ''),
                    lead.get('score', 0),
                    lead.get('status', ''),
                    lead.get('created_at', ''),
                    lead.get('source', '')
                ]
                values.append(row)
            
            # Update spreadsheet
            body = {
                'values': values
            }
            
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Leads!A1:H1000',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            # Format headers
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.2,
                                'green': 0.4,
                                'blue': 0.8
                            },
                            'textFormat': {
                                'bold': True,
                                'foregroundColor': {
                                    'red': 1.0,
                                    'green': 1.0,
                                    'blue': 1.0
                                }
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }]
            
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': requests}
            ).execute()
            
            return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            
        except Exception as e:
            raise Exception(f"Failed to export to sheets: {str(e)}")
    
    async def _get_user_credentials(self, user_id: int) -> Optional[Credentials]:
        """Get user's Google credentials"""
        # This would typically fetch from database
        # For now, return None as placeholder
        return None
    
    async def refresh_user_tokens(self, user_id: int) -> bool:
        """Refresh user's access tokens"""
        try:
            # Get stored refresh token
            refresh_token = await self._get_user_refresh_token(user_id)
            if not refresh_token:
                return False
            
            # Refresh tokens
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    await self._save_user_tokens(user_id, data)
                    return True
                else:
                    return False
                    
        except Exception:
            return False
    
    async def _get_user_refresh_token(self, user_id: int) -> Optional[str]:
        """Get user's refresh token from database"""
        # This would typically fetch from database
        return None
    
    async def _save_user_tokens(self, user_id: int, tokens: Dict[str, Any]) -> None:
        """Save user's tokens to database"""
        # This would typically save to database
        pass
