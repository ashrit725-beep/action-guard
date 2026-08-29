"""Request/response models for the Vexen API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from .catalog import GRANT_KINDS, POLICY_EFFECTS


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    organization: Optional[str] = Field(default=None, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    job_title: Optional[str] = Field(default=None, max_length=80)
    timezone: Optional[str] = Field(default=None, max_length=64)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class NotificationPrefs(BaseModel):
    approval_requests: bool = True
    blocked_actions: bool = True
    high_risk_agents: bool = True
    weekly_digest: bool = False


class AgentDefaults(BaseModel):
    default_status: str = "active"
    default_purchase_limit: float = Field(default=100.0, ge=0, le=1_000_000)
    default_temp_access_minutes: int = Field(default=60, ge=1, le=10080)
    require_approval_for_sensitive: bool = True
    block_payment_credentials: bool = True

    @field_validator("default_status")
    @classmethod
    def _status(cls, v: str) -> str:
        if v not in ("active", "disabled"):
            raise ValueError("default_status must be active or disabled")
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    industry: Optional[str] = Field(default=None, max_length=60)
    agent_defaults: Optional[AgentDefaults] = None


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    description: Optional[str] = Field(default=None, max_length=300)
    template_id: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=60)
    description: Optional[str] = Field(default=None, max_length=300)
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def _status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("active", "disabled"):
            raise ValueError("status must be active or disabled")
        return v


class PermissionConstraints(BaseModel):
    max_amount: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    hard_max_amount: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    approval_required_above: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    require_approval: Optional[bool] = None
    allow_sensitive: Optional[bool] = None
    temporary: Optional[bool] = None
    max_calls_per_day: Optional[int] = Field(default=None, ge=1, le=1_000_000)
    allowed_resources: Optional[List[str]] = None
    denied_resources: Optional[List[str]] = None
    allowed_actions: Optional[List[str]] = None

    @field_validator("allowed_resources", "denied_resources", "allowed_actions")
    @classmethod
    def _patterns(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        cleaned = [str(item).strip()[:160] for item in v if str(item).strip()]
        return cleaned[:25]


class PermissionUpsert(BaseModel):
    key: str = Field(min_length=3, max_length=80)
    decision: str
    constraints: PermissionConstraints = Field(default_factory=PermissionConstraints)
    expires_in_minutes: Optional[int] = Field(default=None, ge=1, le=525600)

    @field_validator("decision")
    @classmethod
    def _decision(cls, v: str) -> str:
        v = (v or "").upper()
        if v not in GRANT_KINDS:
            raise ValueError("decision must be one of " + ", ".join(GRANT_KINDS))
        return v


class PermissionPatch(BaseModel):
    decision: Optional[str] = None
    constraints: Optional[PermissionConstraints] = None
    expires_in_minutes: Optional[int] = Field(default=None, ge=0, le=525600)

    @field_validator("decision")
    @classmethod
    def _decision(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.upper()
        if v not in GRANT_KINDS:
            raise ValueError("decision must be one of " + ", ".join(GRANT_KINDS))
        return v


class CredentialCreate(BaseModel):
    name: str = Field(default="Primary key", min_length=2, max_length=60)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=730)


class PolicyMatch(BaseModel):
    permissions: List[str] = Field(default_factory=lambda: ["*"])
    agents: List[str] = Field(default_factory=lambda: ["*"])
    resources: List[str] = Field(default_factory=lambda: ["*"])
    amount_gt: Optional[float] = Field(default=None, ge=0)
    sensitive_only: Optional[bool] = None

    @field_validator("permissions", "agents", "resources")
    @classmethod
    def _lists(cls, v: List[str]) -> List[str]:
        cleaned = [str(i).strip()[:120] for i in (v or []) if str(i).strip()]
        return cleaned[:40] or ["*"]


class PolicyParams(BaseModel):
    max_amount: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    max_ttl_minutes: Optional[int] = Field(default=None, ge=1, le=525600)


class PolicyCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: Optional[str] = Field(default=None, max_length=600)
    effect: str
    match: PolicyMatch = Field(default_factory=PolicyMatch)
    params: PolicyParams = Field(default_factory=PolicyParams)
    priority: int = Field(default=50, ge=1, le=99)
    enabled: bool = True
    source: Optional[str] = None
    rationale: Optional[str] = Field(default=None, max_length=800)

    @field_validator("effect")
    @classmethod
    def _effect(cls, v: str) -> str:
        v = (v or "").upper()
        if v not in POLICY_EFFECTS:
            raise ValueError("effect must be one of " + ", ".join(POLICY_EFFECTS))
        return v


class PolicyPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=120)
    description: Optional[str] = Field(default=None, max_length=600)
    effect: Optional[str] = None
    match: Optional[PolicyMatch] = None
    params: Optional[PolicyParams] = None
    priority: Optional[int] = Field(default=None, ge=1, le=99)
    enabled: Optional[bool] = None

    @field_validator("effect")
    @classmethod
    def _effect(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.upper()
        if v not in POLICY_EFFECTS:
            raise ValueError("effect must be one of " + ", ".join(POLICY_EFFECTS))
        return v


class PolicyGenerateRequest(BaseModel):
    prompt: str = Field(min_length=4, max_length=2000)


class PolicyTestRequest(BaseModel):
    agent_id: str
    resource: str = Field(min_length=1, max_length=60)
    action: str = Field(min_length=1, max_length=40)
    resource_id: Optional[str] = Field(default=None, max_length=256)
    amount: Optional[float] = None


class ApprovalDecision(BaseModel):
    decision: str
    note: Optional[str] = Field(default=None, max_length=400)

    @field_validator("decision")
    @classmethod
    def _decision(cls, v: str) -> str:
        v = (v or "").lower()
        if v not in ("approved", "denied"):
            raise ValueError("decision must be approved or denied")
        return v


class AuthorizeRequest(BaseModel):
    """Public API payload. Extra fields are ignored, never trusted."""

    model_config = {"extra": "ignore"}

    resource: str = Field(min_length=1, max_length=60)
    action: str = Field(min_length=1, max_length=40)
    resource_id: Optional[str] = Field(default=None, max_length=256)
    amount: Optional[float] = None
    currency: Optional[str] = Field(default="USD", max_length=8)
    approval_id: Optional[str] = Field(default=None, max_length=64)
    context: Optional[Dict[str, Any]] = None


class SimulatorStart(BaseModel):
    scenario_id: str = Field(min_length=2, max_length=60)


class AssistantTurn(BaseModel):
    role: str = Field(default="user", max_length=12)
    content: str = Field(min_length=1, max_length=1200)


class AssistantChatIn(BaseModel):
    """A short conversation with the in-app helper."""
    messages: List[AssistantTurn] = Field(min_length=1, max_length=14)
    page: Optional[str] = Field(default=None, max_length=60)


class ContactMessageIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    company: Optional[str] = Field(default=None, max_length=100)
    message: str = Field(min_length=10, max_length=4000)
    topic: Optional[str] = Field(default="general", max_length=40)
