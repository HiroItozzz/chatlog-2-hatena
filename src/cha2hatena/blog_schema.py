from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field


class AbstractBlogPoster(ABC):
    @abstractmethod
    def blog_post(self): ...


class QiitaRequestSchema(BaseModel):
    body: str
    coediting: bool | None = False
    group_url_name: str | None = None
    private: bool = True
    tags: list[str] = []


class QiitaResponseSchema(BaseModel):
    pass


class HatenaSecretKeys(BaseModel):
    hatena_entry_url: str
    client_id: str = Field(alias="client_key")
    client_secret: str = Field(alias="client_secret")
    token: str = Field(alias="resource_owner_key")
    token_secret: str = Field(alias="resource_owner_secret")

    def get_auth_params(self) -> dict:
        """OAuth1Auth用のパラメータを返す"""
        return self.model_dump(exclude={"hatena_entry_url"})
