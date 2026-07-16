from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    user_invite_id = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")  # user | admin
    display_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    invites_sent = relationship("UserInvite", back_populates="invited_by_user", foreign_keys="UserInvite.invited_by_id")


class UserInvite(Base):
    __tablename__ = "user_invites"

    id = Column(String, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    token = Column(String, unique=True, nullable=False)
    invited_by_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invited_by_user = relationship("User", back_populates="invites_sent", foreign_keys=[invited_by_id])
