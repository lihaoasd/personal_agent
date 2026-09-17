"""请求/响应 Pydantic 模型。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

GoalCategory = Literal["general", "learning", "health", "habit"]
GoalStatus = Literal["active", "paused", "done", "abandoned"]
TaskStatus = Literal["todo", "doing", "done"]
ItemType = Literal["task", "course", "book", "practice"]
ScheduleStatus = Literal["upcoming", "done", "cancelled"]
EventSource = Literal["chat", "template", "backfill"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    reason: str = ""
    category: GoalCategory = "general"
    target_date: Optional[str] = None
    tasks: list["TaskCreate"] = []


class GoalPlanRequest(BaseModel):
    description: str = Field(min_length=1, max_length=1000)
    category: GoalCategory = "general"
    reason: str = ""


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    reason: Optional[str] = None
    category: Optional[GoalCategory] = None
    status: Optional[GoalStatus] = None
    target_date: Optional[str] = None


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    item_type: ItemType = "task"
    planned_date: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[TaskStatus] = None


class ScheduleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_at: str
    end_at: Optional[str] = None
    goal_id: Optional[int] = None
    task_id: Optional[int] = None
    remind_at: Optional[str] = None


class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    remind_at: Optional[str] = None
    status: Optional[ScheduleStatus] = None


class TemplateCreate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    event_type: str = Field(min_length=1, max_length=50)
    amount: Optional[float] = None
    unit: Optional[str] = None
    goal_id: Optional[int] = None
    sort_order: int = 0


class BackfillRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    happened_on: str
    goal_id: Optional[int] = None


class ModelConfigRequest(BaseModel):
    """模型配置保存请求；api_key 为空表示保留已存值。"""

    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class ReviewGenerateRequest(BaseModel):
    period_start: Optional[str] = None
    period_end: Optional[str] = None
