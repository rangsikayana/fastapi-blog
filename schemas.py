from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)  # Uses Pydantic email validation


class UserCreate(UserBase):  # For user input, inherits from UserBase
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = Field(default=None, max_length=120)
    image_file: str | None = Field(
        default=None, min_length=1, max_length=200
    )  # Meant to pass image name only, path is built by SQLAlchemy model
    # Images still added manually, file upload feature will be added later


class UserPublic(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )  # True allows Pydantic to read SQLAlchemy's cols & properties

    id: int
    username: str
    image_file: str | None
    image_path: str


class UserPrivate(UserPublic):
    email: EmailStr


class Token(BaseModel):  # For login response
    access_token: str
    token_type: str


class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class PostCreate(PostBase):  # For user input, inherits from PostBase
    user_id: int  # TEMP: For manual passing, will get from auth sess later


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1)


class PostResponse(PostBase):  # For non user defined cols
    model_config = ConfigDict(
        from_attributes=True
    )  # True allows Pydantic to read SQLAlchemy's cols & properties

    id: int
    user_id: int
    date_posted: datetime
    author: UserPublic  # Returns UserPublic payload in nested JSON
    # UserPublic doesn't return email
