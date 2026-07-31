from pydantic import BaseModel, ConfigDict, Field


class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=50)


class PostCreate(PostBase): # For user input, inherits from PostBase
    pass


class PostResponse(PostBase): # For non user defined cols
    model_config = ConfigDict(from_attributes=True) # True allows Pydantic to read from DB

    id: int
    date_posted: str # RAM uses string, will convert to datetime when using DB
