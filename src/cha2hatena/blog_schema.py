from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field, field_serializer


class AbstractBlogPoster(BaseModel, ABC):
    @abstractmethod
    async def blog_post(self): ...


class BlogClientSchema(BaseModel):
    title: str
    content: str
    categories: list[str]
    preset_categories: list[str]
    hatena_secret_keys: dict
    qiita_bearer_token: str | None = None
    author: str | None = Field(default=None, description="はてなの投稿者名。Noneの場合自分のはてなID")
    updated: datetime | None = Field(default=None, description="はてなの公開時刻設定。")
    tweet: bool | None = Field(default=None, description="QiitaのTwitter連携設定")
    is_draft: bool = Field(default=False, description="デバッグ時は下書き")


class HatenaResponseSchema(BaseModel):
    # Atom名前空間の要素
    title: str
    author: str
    content: str
    time: datetime
    url: str
    url_edit: str
    categories: list[str]
    # app名前空間の要素
    is_draft: bool
    status_code: int | None = None



class QiitaTag(BaseModel):
    name: str
    versions: list = Field(default_factory=list)


class QiitaResponseSchema(BaseModel):
    title: str
    body: str = Field(serialization_alias="content")
    tags: list[QiitaTag] = Field(serialization_alias="categories")
    url: str
    private: bool = Field(serialization_alias="is_draft")
    created_at: datetime
    coediting: bool
    comments_count: int
    status_code: int | None = None
    message: str = "success"
    type: str = "success"

    @field_serializer("tags")
    def tags_to_simple_list(self, value: list[QiitaTag]) -> list[str]:
        simple_cats = [tag.name for tag in value]
        return simple_cats


class HatenaSecretKeys(BaseModel):
    hatena_entry_url: str
    client_id: str = Field(alias="client_key")
    client_secret: str
    token: str = Field(alias="resource_owner_key")
    token_secret: str = Field(alias="resource_owner_secret")

    def get_auth_params(self) -> dict:
        """OAuth1Auth用のパラメータを返す"""
        return self.model_dump(exclude={"hatena_entry_url"})
