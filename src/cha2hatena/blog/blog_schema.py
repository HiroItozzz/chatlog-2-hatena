from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class BaseBlogResponse(BaseModel):
    title: str
    url: str


class HatenaSecretKeys(BaseModel):
    model_config = {"populate_by_name": True}
    hatena_entry_url: str
    hatena_client_key: str = Field(alias="client_id")
    hatena_client_secret: str = Field(alias="client_secret")
    hatena_resource_owner_key: str = Field(alias="token")
    hatena_resource_owner_secret: str = Field(alias="token_secret")

    def get_auth_params(self) -> dict:
        """OAuth1Auth用のパラメータを返す"""
        return self.model_dump(exclude={"hatena_entry_url"}, by_alias=True)


class AbstractBlogPoster(BaseModel, ABC):
    @abstractmethod
    async def blog_post(self): ...


class BlogClientSchema(BaseModel):
    title: str
    content: str
    categories: list[str]
    preset_categories: list[str]
    hatena_secret_keys: HatenaSecretKeys
    qiita_bearer_token: str | None = None
    devto_api_key: str | None = None
    author: str | None = Field(default=None, description="はてなの投稿者名。Noneの場合自分のはてなID")
    updated: datetime | None = Field(default=None, description="はてなの公開時刻設定。")
    tweet: bool | None = Field(default=None, description="QiitaのTwitter連携設定")
    is_draft: bool = Field(default=False, description="デバッグ時は下書き")


class HatenaResponseSchema(BaseBlogResponse):
    content: str
    categories: list[str]
    author: str
    time: datetime
    url_edit: str
    is_draft: bool
    status_code: int | None = None


class QiitaTag(BaseModel):
    name: str
    versions: list = Field(default_factory=list)


class QiitaResponseSchema(BaseBlogResponse):
    content: str = Field(validation_alias="body")
    categories: list[str] = Field(validation_alias="tags")
    is_draft: bool = Field(validation_alias="private")
    created_at: datetime
    coediting: bool
    comments_count: int
    status_code: int | None = None
    message: str = "success"
    type: str = "success"

    @field_validator("categories", mode="before")
    @classmethod
    def tags_to_simple_list(cls, value: list[QiitaTag]) -> list[str]:
        """QiitaTagオブジェクトのリストを文字列リストに変換"""
        if isinstance(value[0], dict):
            return [tag["name"] for tag in value]
        if hasattr(value[0], "name"):
            return [tag.name for tag in value]
        return value


class DevToResponseSchema(BaseBlogResponse):
    content: str = Field(validation_alias="body_markdown")
    categories: list[str] = Field(validation_alias="tags", default_factory=list)
    is_draft: bool = Field(validation_alias="published_at")
    created_at: datetime
    comments_count: int
    positive_reactions_count: int
    status_code: int | None = None
    message: str = "success"
    type: str = "success"

    @field_validator("is_draft", mode="before")
    @classmethod
    def invert_published(cls, value: str | None) -> bool:
        """publishedをis_draftに反転"""
        return value is None