from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

NotificationChannelType = Literal["mobile_push", "persistent_notification"]
NotificationSeverityType = Literal["info", "warning", "critical"]


class NotificationTargetModel(BaseModel):
    id: str
    service: str
    display_name: str
    platform: str = "unknown"
    user_id: str = ""
    active: bool = True


class NotificationConditionModel(BaseModel):
    key: str = Field(..., min_length=1)
    operator: str = Field(default="eq", min_length=1)
    value: str = ""


class NotificationRuleModel(BaseModel):
    id: str
    name: str
    enabled: bool = True
    event_types: list[str] = Field(default_factory=list)
    target_user_ids: list[str] = Field(default_factory=list)
    target_device_ids: list[str] = Field(default_factory=list)
    channels: list[NotificationChannelType] = Field(default_factory=list)
    severity: NotificationSeverityType = "info"
    cooldown_seconds: int = Field(default=0, ge=0)
    quiet_hours_start: str = ""
    quiet_hours_end: str = ""
    conditions: list[NotificationConditionModel] = Field(default_factory=list)
    message_template: str = ""


class NotificationSettingsModel(BaseModel):
    enabled: bool = True
    enabled_event_types: list[str] = Field(default_factory=list)
    default_channels: list[NotificationChannelType] = Field(
        default_factory=lambda: ["mobile_push"]
    )
    default_severity: NotificationSeverityType = "info"


class NotificationHistoryModel(BaseModel):
    id: str
    created_at: str
    event_type: str
    title: str
    message: str
    delivered: bool
    target_id: str = ""
    channels: list[NotificationChannelType] = Field(default_factory=list)
    rule_id: str = ""
    error: str = ""


class NotificationOverviewResponse(BaseModel):
    settings: NotificationSettingsModel
    devices: list[NotificationTargetModel] = Field(default_factory=list)
    rules: list[NotificationRuleModel] = Field(default_factory=list)
    history: list[NotificationHistoryModel] = Field(default_factory=list)


class NotificationDeviceUpdateRequest(BaseModel):
    user_id: str = ""
    active: bool = True


class NotificationSettingsUpdateRequest(BaseModel):
    enabled: bool = True
    enabled_event_types: list[str] = Field(default_factory=list)
    default_channels: list[NotificationChannelType] = Field(
        default_factory=lambda: ["mobile_push"]
    )
    default_severity: NotificationSeverityType = "info"


class NotificationRuleUpsertRequest(BaseModel):
    name: str = Field(..., min_length=1)
    enabled: bool = True
    event_types: list[str] = Field(default_factory=list)
    target_user_ids: list[str] = Field(default_factory=list)
    target_device_ids: list[str] = Field(default_factory=list)
    channels: list[NotificationChannelType] = Field(
        default_factory=lambda: ["mobile_push"]
    )
    severity: NotificationSeverityType = "info"
    cooldown_seconds: int = Field(default=0, ge=0)
    quiet_hours_start: str = ""
    quiet_hours_end: str = ""
    conditions: list[NotificationConditionModel] = Field(default_factory=list)
    message_template: str = ""


class NotificationTestRequest(BaseModel):
    target_id: str = ""
