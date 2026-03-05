from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Rule
from ..schemas import RuleCreate, RuleUpdate, RuleResponse

router = APIRouter()

VALID_FIELDS = {"title", "author", "feed_id", "excerpt"}
VALID_OPS = {"contains", "not_contains", "matches", "equals"}
VALID_ACTIONS = {"mark_read", "save", "bookmark", "mute"}


def _validate_rule(data: RuleCreate | RuleUpdate):
    if data.condition is not None:
        cond = data.condition
        if cond.get("field") not in VALID_FIELDS:
            raise HTTPException(422, f"condition.field must be one of {VALID_FIELDS}")
        if cond.get("op") not in VALID_OPS:
            raise HTTPException(422, f"condition.op must be one of {VALID_OPS}")
        if "value" not in cond:
            raise HTTPException(422, "condition.value is required")
    if data.action is not None:
        if not (data.action in VALID_ACTIONS or data.action.startswith("tag:")):
            raise HTTPException(422, f"action must be one of {VALID_ACTIONS} or 'tag:<id>'")


@router.get("", response_model=list[RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).order_by(Rule.created_at))
    return result.scalars().all()


@router.post("", response_model=RuleResponse, status_code=201)
async def create_rule(data: RuleCreate, db: AsyncSession = Depends(get_db)):
    _validate_rule(data)
    rule = Rule(name=data.name, condition=data.condition, action=data.action, is_active=data.is_active)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: int, data: RuleUpdate, db: AsyncSession = Depends(get_db)):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    _validate_rule(data)
    if data.name is not None:
        rule.name = data.name
    if data.condition is not None:
        rule.condition = data.condition
    if data.action is not None:
        rule.action = data.action
    if data.is_active is not None:
        rule.is_active = data.is_active
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await db.get(Rule, rule_id)
    if not rule:
        raise HTTPException(404, "Rule not found")
    await db.delete(rule)
    await db.commit()
