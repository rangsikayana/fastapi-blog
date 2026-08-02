from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)  # Uses Pydantic email validation
    # password is not included for privacy


class UserCreate(UserBase):  # For user input, inherits from UserBase
    pass


class UserResponse(UserBase):
    model_config = ConfigDict(
        from_attributes=True
    )  # True allows Pydantic to read SQLAlchemy's cols & properties

    id: int
    image_file: str | None
    image_path: str


class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    # author: str = Field(min_length=1, max_length=50) # Replaced by SQLAlchemy's relationship


class PostCreate(PostBase):  # For user input, inherits from PostBase
    user_id: int  # Temporary for manual passing, will get from auth sess later


class PostResponse(PostBase):  # For non user defined cols
    model_config = ConfigDict(
        from_attributes=True
    )  # True allows Pydantic to read SQLAlchemy's cols & properties

    id: int
    user_id: int
    date_posted: datetime
    author: UserResponse  # Returns UserResponse payload in nested JSON response
