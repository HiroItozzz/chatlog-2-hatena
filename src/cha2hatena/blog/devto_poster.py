import logging
from typing import ClassVar
import json

from httpx import AsyncClient, Response
from pydantic import Field, ValidationError

from .blog_schema import AbstractBlogPoster, DevToResponseSchema

logger = logging.getLogger(__name__)


class DevToPoster(AbstractBlogPoster):
    entry_point: ClassVar[str] = "https://dev.to/api/articles"

    title: str
    body_markdown: str = Field(alias="content", description="マークダウン方式のブログ本文")
    published: bool = Field(default=True, alias="is_draft")  # Qiitaと逆なので注意
    api_key: str = Field(alias="devto_api_key", exclude=True)
    tags: list[str] = Field(
        default_factory=list, 
        alias="categories", 
        max_length=4, 
        description="タグは最大4個まで"
    )
    preset_tags: list[str] = Field(
        default_factory=list,
        alias="preset_categories",
        max_length=4,
        description="プリセットタグ。tagsと合わせて最大4個まで",
        exclude=True
    )
    description: str | None = None
    canonical_url: str | None = None
    series: str | None = None
    main_image: str | None = None

    def model_post_init(self, __context):
        """初期化後にtagsを結合"""
        # publishedをis_draftの逆にする (Dev.toはpublished=True、Qiitaはprivate=False)
        if hasattr(self, 'published'):
            self.published = not self.published
        
        # tagsとpreset_tagsを結合
        all_tags = list(self.tags) + list(self.preset_tags)
        # 最大4個に制限
        self.tags = all_tags[:4]

    async def blog_post(self, httpx_client: AsyncClient) -> dict:
        response = await self.devto_auth(httpx_client)
        return self.parse_response(response)

    async def devto_auth(self, httpx_client: AsyncClient) -> Response:
        logger.debug("Dev.toへのリクエスト開始...")
        
        # Dev.to APIは {"article": {...}} という入れ子構造が必要
        payload = {
            "article": self.model_dump(
                exclude_none=True
            )
        }
        
        logger.debug(f"送信するペイロード: {payload}")
        
        response = await httpx_client.post(
            url=self.entry_point,
            json=payload,
            headers={
                "api-key": self.api_key,
                "Content-Type": "application/json"
            },
        )
        
        logger.debug(f"レスポンス: {response.text}")
        response.raise_for_status()
        return response

    @staticmethod
    def parse_response(response: Response) -> dict:
        try:
            result = DevToResponseSchema.model_validate_json(response.text)
            result.status_code = response.status_code
            logger.warning("Dev.toへの投稿完了")
            return result  # 統一インターフェースで返す
        except ValidationError as e:
            logger.error(f"Dev.to投稿処理でエラー。code:{response.status_code}, error:{e}")
            result = json.loads(response.text)
            result["status_code"] = response.status_code
            return result