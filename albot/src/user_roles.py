"""
User roles and permissions system
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


class UserRole(Enum):
    """User roles in the system"""
    ADMIN = "admin"           # Владелец агентства
    MANAGER = "manager"       # Менеджер
    AGENT = "agent"           # Агент
    VIEWER = "viewer"          # Только просмотр


class Permission(Enum):
    """System permissions"""
    # Lead permissions
    VIEW_LEADS = "view_leads"
    CREATE_LEADS = "create_leads"
    EDIT_LEADS = "edit_leads"
    DELETE_LEADS = "delete_leads"
    
    # Script permissions
    VIEW_SCRIPTS = "view_scripts"
    CREATE_SCRIPTS = "create_scripts"
    EDIT_SCRIPTS = "edit_scripts"
    DELETE_SCRIPTS = "delete_scripts"
    
    # Analytics permissions
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_DATA = "export_data"
    
    # Settings permissions
    VIEW_SETTINGS = "view_settings"
    EDIT_SETTINGS = "edit_settings"
    MANAGE_INTEGRATIONS = "manage_integrations"
    
    # User management
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    
    # Billing
    VIEW_BILLING = "view_billing"
    MANAGE_BILLING = "manage_billing"


@dataclass
class UserPermissions:
    """User permissions configuration"""
    role: UserRole
    permissions: List[Permission]
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions


class RoleManager:
    """Manages user roles and permissions"""
    
    def __init__(self):
        self.role_permissions = {
            UserRole.ADMIN: [
                Permission.VIEW_LEADS,
                Permission.CREATE_LEADS,
                Permission.EDIT_LEADS,
                Permission.DELETE_LEADS,
                Permission.VIEW_SCRIPTS,
                Permission.CREATE_SCRIPTS,
                Permission.EDIT_SCRIPTS,
                Permission.DELETE_SCRIPTS,
                Permission.VIEW_ANALYTICS,
                Permission.EXPORT_DATA,
                Permission.VIEW_SETTINGS,
                Permission.EDIT_SETTINGS,
                Permission.MANAGE_INTEGRATIONS,
                Permission.VIEW_USERS,
                Permission.MANAGE_USERS,
                Permission.MANAGE_ROLES,
                Permission.VIEW_BILLING,
                Permission.MANAGE_BILLING
            ],
            UserRole.MANAGER: [
                Permission.VIEW_LEADS,
                Permission.CREATE_LEADS,
                Permission.EDIT_LEADS,
                Permission.VIEW_SCRIPTS,
                Permission.CREATE_SCRIPTS,
                Permission.EDIT_SCRIPTS,
                Permission.VIEW_ANALYTICS,
                Permission.EXPORT_DATA,
                Permission.VIEW_SETTINGS,
                Permission.EDIT_SETTINGS,
                Permission.MANAGE_INTEGRATIONS,
                Permission.VIEW_USERS,
                Permission.VIEW_BILLING
            ],
            UserRole.AGENT: [
                Permission.VIEW_LEADS,
                Permission.CREATE_LEADS,
                Permission.EDIT_LEADS,
                Permission.VIEW_SCRIPTS,
                Permission.VIEW_ANALYTICS
            ],
            UserRole.VIEWER: [
                Permission.VIEW_LEADS,
                Permission.VIEW_SCRIPTS,
                Permission.VIEW_ANALYTICS
            ]
        }
    
    def get_user_permissions(self, role: UserRole) -> UserPermissions:
        """Get permissions for a specific role"""
        permissions = self.role_permissions.get(role, [])
        return UserPermissions(role=role, permissions=permissions)
    
    def check_permission(self, user_role: UserRole, permission: Permission) -> bool:
        """Check if user role has specific permission"""
        user_permissions = self.get_user_permissions(user_role)
        return user_permissions.has_permission(permission)
    
    def get_role_description(self, role: UserRole) -> str:
        """Get human-readable description of role"""
        descriptions = {
            UserRole.ADMIN: "Владелец агентства - полный доступ ко всем функциям",
            UserRole.MANAGER: "Менеджер - управление лидами, скриптами и настройками",
            UserRole.AGENT: "Агент - работа с лидами и просмотр аналитики",
            UserRole.VIEWER: "Наблюдатель - только просмотр данных"
        }
        return descriptions.get(role, "Неизвестная роль")
    
    def get_available_roles(self, current_role: UserRole) -> List[UserRole]:
        """Get roles that can be assigned by current role"""
        if current_role == UserRole.ADMIN:
            return [UserRole.MANAGER, UserRole.AGENT, UserRole.VIEWER]
        elif current_role == UserRole.MANAGER:
            return [UserRole.AGENT, UserRole.VIEWER]
        else:
            return []
    
    def can_manage_user(self, manager_role: UserRole, target_role: UserRole) -> bool:
        """Check if manager can manage target user"""
        if manager_role == UserRole.ADMIN:
            return True
        elif manager_role == UserRole.MANAGER:
            return target_role in [UserRole.AGENT, UserRole.VIEWER]
        else:
            return False


class UserRoleManager:
    """Manages user roles in the system"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.role_manager = RoleManager()
    
    async def get_user_role(self, user_id: int) -> UserRole:
        """Get user role from database"""
        try:
            user_data = await self.supabase.get_user_data(user_id)
            role_str = user_data.get('role', 'agent')
            return UserRole(role_str)
        except Exception:
            return UserRole.AGENT  # Default role
    
    async def set_user_role(self, user_id: int, role: UserRole, assigned_by: int) -> bool:
        """Set user role"""
        try:
            # Check if assigner can assign this role
            assigner_role = await self.get_user_role(assigned_by)
            if not self.role_manager.can_manage_user(assigner_role, role):
                return False
            
            # Update user role
            await self.supabase.update_user_role(user_id, role.value)
            return True
        except Exception:
            return False
    
    async def check_permission(self, user_id: int, permission: Permission) -> bool:
        """Check if user has specific permission"""
        try:
            user_role = await self.get_user_role(user_id)
            return self.role_manager.check_permission(user_role, permission)
        except Exception:
            return False
    
    async def get_user_permissions(self, user_id: int) -> UserPermissions:
        """Get user permissions"""
        try:
            user_role = await self.get_user_role(user_id)
            return self.role_manager.get_user_permissions(user_role)
        except Exception:
            return UserPermissions(UserRole.AGENT, [])
    
    async def can_access_lead(self, user_id: int, lead_id: str) -> bool:
        """Check if user can access specific lead"""
        try:
            # Get user role
            user_role = await self.get_user_role(user_id)
            
            # Get lead data
            lead_data = await self.supabase.get_lead_data(lead_id)
            lead_owner = lead_data.get('created_by')
            
            # Admin can access all leads
            if user_role == UserRole.ADMIN:
                return True
            
            # Manager can access all leads in their agency
            if user_role == UserRole.MANAGER:
                return True  # Assuming all leads in same agency
            
            # Agent can access their own leads
            if user_role == UserRole.AGENT:
                return lead_owner == user_id
            
            # Viewer can only view
            if user_role == UserRole.VIEWER:
                return True
            
            return False
        except Exception:
            return False
    
    async def get_accessible_leads(self, user_id: int) -> List[Dict[str, Any]]:
        """Get leads accessible to user"""
        try:
            user_role = await self.get_user_role(user_id)
            
            if user_role == UserRole.ADMIN:
                # Admin can see all leads
                return await self.supabase.get_all_leads()
            elif user_role == UserRole.MANAGER:
                # Manager can see all leads in agency
                return await self.supabase.get_agency_leads(user_id)
            elif user_role == UserRole.AGENT:
                # Agent can see their own leads
                return await self.supabase.get_user_leads(user_id)
            elif user_role == UserRole.VIEWER:
                # Viewer can see all leads (read-only)
                return await self.supabase.get_agency_leads(user_id)
            else:
                return []
        except Exception:
            return []
    
    async def get_role_management_ui(self, user_id: int) -> str:
        """Get role management UI for user"""
        try:
            user_role = await self.get_user_role(user_id)
            
            if not self.role_manager.check_permission(user_role, Permission.MANAGE_USERS):
                return "❌ У вас нет прав для управления пользователями"
            
            # Get available roles
            available_roles = self.role_manager.get_available_roles(user_role)
            
            ui_text = "👥 *УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ*\n\n"
            ui_text += f"*Ваша роль:* {user_role.value.upper()}\n\n"
            ui_text += "*Доступные роли для назначения:*\n"
            
            for role in available_roles:
                description = self.role_manager.get_role_description(role)
                ui_text += f"• {role.value.upper()}: {description}\n"
            
            return ui_text
            
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
