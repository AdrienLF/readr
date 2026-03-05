from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Topic, Feed
from ..schemas import TopicCreate, TopicUpdate, TopicResponse

router = APIRouter()


@router.get("", response_model=list[TopicResponse])
async def list_topics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Topic).options(selectinload(Topic.feeds)).order_by(Topic.name)
    )
    topics = result.scalars().all()
    return [
        TopicResponse(
            id=t.id,
            name=t.name,
            color=t.color,
            icon=t.icon,
            created_at=t.created_at,
            feed_count=len(t.feeds),
        )
        for t in topics
    ]


@router.post("", response_model=TopicResponse, status_code=201)
async def create_topic(payload: TopicCreate, db: AsyncSession = Depends(get_db)):
    topic = Topic(**payload.model_dump())
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return TopicResponse(id=topic.id, name=topic.name, color=topic.color, icon=topic.icon, created_at=topic.created_at, feed_count=0)


@router.put("/{topic_id}", response_model=TopicResponse)
async def update_topic(topic_id: int, payload: TopicUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Topic).options(selectinload(Topic.feeds)).where(Topic.id == topic_id)
    )
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(404, "Topic not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(topic, field, value)

    await db.commit()
    await db.refresh(topic)
    return TopicResponse(id=topic.id, name=topic.name, color=topic.color, icon=topic.icon, created_at=topic.created_at, feed_count=len(topic.feeds))


@router.delete("/{topic_id}", status_code=204)
async def delete_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    await db.delete(topic)
    await db.commit()
