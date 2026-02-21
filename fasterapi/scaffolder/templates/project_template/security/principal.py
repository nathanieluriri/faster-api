from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AuthPrincipal(BaseModel):
    user_id: str
    role: Literal["member", "admin"]
    access_token_id: str
    jwt_token: str
    allow_expired: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_member(self) -> bool:
        return self.role == "member"
