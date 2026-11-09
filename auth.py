import hashlib
import json
import os
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum


class UserRole(Enum):
    SUPER_ADMIN = "super_admin"
    NORMAL_USER = "normal_user"


class Permission(Enum):
    APPLY = "apply"
    REVIEW = "review"
    APPROVE = "approve"
    ARCHIVE = "archive"


@dataclass
class User:
    username: str
    password_hash: str
    role: str
    permissions: List[str]
    created_at: str
    created_by: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def can_process_stage(self, stage: str) -> bool:
        if self.role == UserRole.SUPER_ADMIN.value:
            return True
        return stage in self.permissions


class AuthManager:
    def __init__(self, data_file: str = "users.json"):
        self.data_file = data_file
        self.users: Dict[str, User] = {}
        self._load_users()

        if not self.users:
            self._create_default_admin()

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def _create_default_admin(self):
        from datetime import datetime
        admin_user = User(
            username="admin",
            password_hash=self._hash_password("admin"),
            role=UserRole.SUPER_ADMIN.value,
            permissions=[p.value for p in Permission],
            created_at=datetime.now().isoformat(),
            created_by="system"
        )
        self.users["admin"] = admin_user
        self._save_users()
        print("默认超级管理员已创建: admin/admin")

    def _load_users(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for username, user_data in data.items():
                        self.users[username] = User(**user_data)
            except Exception as e:
                print(f"加载用户数据失败: {e}")

    def _save_users(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                data = {username: user.to_dict() for username, user in self.users.items()}
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存用户数据失败: {e}")

    def verify_login(self, username: str, password: str) -> tuple:
        """验证用户登录，返回 (成功与否, 用户对象或错误消息)"""
        if username not in self.users:
            return False, "用户名不存在"

        user = self.users[username]
        password_hash = self._hash_password(password)

        if user.password_hash != password_hash:
            return False, "密码错误"

        return True, user

    def get_user(self, username: str) -> Optional[User]:
        """获取指定用户"""
        return self.users.get(username)

    def user_exists(self, username: str) -> bool:
        """检查用户是否存在"""
        return username in self.users

    def is_super_admin(self, user: User) -> bool:
        """检查用户是否为超级管理员"""
        if not user:
            return False
        return user.role == UserRole.SUPER_ADMIN.value

    def create_user(self, creator: User, username: str, password: str, permissions: List[str]) -> tuple:
        """创建新用户"""
        from datetime import datetime

        if not self.is_super_admin(creator):
            return False, "只有超级管理员可以创建用户"

        if username in self.users:
            return False, "用户名已存在"

        if len(username) < 3:
            return False, "用户名至少需要3个字符"

        if len(password) < 4:
            return False, "密码至少需要4个字符"

        new_user = User(
            username=username,
            password_hash=self._hash_password(password),
            role=UserRole.NORMAL_USER.value,
            permissions=permissions,
            created_at=datetime.now().isoformat(),
            created_by=creator.username
        )

        self.users[username] = new_user
        self._save_users()
        return True, "用户创建成功"

    def update_user_permissions(self, operator: User, username: str, permissions: List[str]) -> tuple:
        """更新用户权限"""
        if not self.is_super_admin(operator):
            return False, "只有超级管理员可以修改权限"

        if username not in self.users:
            return False, "用户不存在"

        if username == "admin":
            return False, "不能修改超级管理员权限"

        user = self.users[username]
        user.permissions = permissions
        self._save_users()
        return True, "权限更新成功"

    def update_user_password(self, operator: User, username: str, new_password: str) -> tuple:
        """更新用户密码"""
        if not self.is_super_admin(operator):
            return False, "只有超级管理员可以修改密码"

        if username not in self.users:
            return False, "用户不存在"

        if len(new_password) < 4:
            return False, "密码至少需要4个字符"

        user = self.users[username]
        user.password_hash = self._hash_password(new_password)
        self._save_users()
        return True, "密码更新成功"

    def delete_user(self, operator: User, username: str) -> tuple:
        """删除用户"""
        if not self.is_super_admin(operator):
            return False, "只有超级管理员可以删除用户"

        if username not in self.users:
            return False, "用户不存在"

        if username == "admin":
            return False, "不能删除超级管理员"

        del self.users[username]
        self._save_users()
        return True, "用户删除成功"

    def get_all_users(self, operator: User) -> List[dict]:
        """获取所有用户列表"""
        if not self.is_super_admin(operator):
            return []
        return [user.to_dict() for user in self.users.values()]

    def get_all_permissions(self) -> List[dict]:
        """获取所有可用权限列表"""
        return [
            {"value": p.value, "label": p.name, "description": self._get_permission_desc(p)}
            for p in Permission
        ]

    def _get_permission_desc(self, permission: Permission) -> str:
        """获取权限描述"""
        descriptions = {
            Permission.APPLY: "可以提交申请",
            Permission.REVIEW: "可以审核申请",
            Permission.APPROVE: "可以审批申请",
            Permission.ARCHIVE: "可以归档申请"
        }
        return descriptions.get(permission, "")


auth_manager = AuthManager()
