import json
import logging
from typing import ClassVar

from httpx import AsyncClient, Response
from pydantic import Field, ValidationError, computed_field, field_serializer

from .blog_schema import AbstractBlogPoster, QiitaResponseSchema, QiitaTag

logger = logging.getLogger(__name__)


class QiitaPoster(AbstractBlogPoster):
    entry_point: ClassVar[str] = "https://qiita.com/api/v2/items"

    title: str
    body: str = Field(alias="content", description="マークダウン方式のブログ本文")
    private: bool | None = Field(default=None, alias="is_draft")
    access_token: str = Field(alias="qiita_bearer_token", exclude=True)
    tweet: bool | None = Field(default=None)
    cats: list[str] = Field(
        alias="categories",
        max_length=4,
        description="ブログのタグ（カテゴリー）。プリセットと合わせて最大5個まで",
        exclude=True,
    )
    preset_cats: list[str] = Field(
        alias="preset_categories",
        max_length=1,
        description="ブログのタグ（カテゴリー）。tagsとあわせて最大5個まで",
        exclude=True,
    )

    @computed_field
    @property
    def tags(self) -> list[str]:
        return self.cats + self.preset_cats

    @field_serializer("tags")
    def tag_serializer(self, value: list[str]) -> list[QiitaTag]:
        schema = [QiitaTag(name=cat) for cat in value]
        return schema

    # ---

    async def blog_post(self, httpx_client: AsyncClient) -> dict:
        response = await self.qiita_auth(httpx_client)
        return self.parse_response(response)

    async def qiita_auth(self, httpx_client: AsyncClient) -> Response:
        logger.debug("Qiitaへのリクエスト開始...")
        logger.debug(f"パラメータ: {self}")
        logger.debug(f"model_dumpの結果：{self.model_dump()}")
        response = await httpx_client.post(
            url=self.entry_point,
            json=self.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"},
        )
        print(response.text)
        response.raise_for_status()
        return response

    @staticmethod
    def parse_response(response: Response) -> dict:
        try:
            result = QiitaResponseSchema.model_validate_json(response.text)
            result.status_code = response.status_code
            if result.status_code == 201:
                logger.warning("Qiitaへの投稿完了")
        except ValidationError:
            logger.error(f"Qiita投稿処理でエラー。code:{response.status_code}")
            result = json.loads(response.text)
            result["status_code"] = response.status_code
        return result

