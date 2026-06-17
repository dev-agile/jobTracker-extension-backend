from enum import Enum as PyEnum
from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, String, func

from ..database import Base

class ActivityType(str, PyEnum):
    LOGIN = "login"
    LOGOUT = "logout"
    JOB_CREATED = "job_created"
    JOB_UPDATED = "job_updated"  


class Activity(Base):
    __tablename__ = "activity"

    id = Column(String, primary_key=True, index=True)
    type = Column(
        Enum(
            ActivityType,
            name="activity_type_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )

    actor_display_name = Column(String, nullable=True)
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    job_id = Column(String, ForeignKey("jobbs.id"), nullable=True)
    user_invite_id = Column(String, ForeignKey("user_invites.id"), nullable=True)
    message = Column(String, nullable=True)
    activity_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
