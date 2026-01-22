from enum import StrEnum
from typing import TypeAlias, TypedDict

from .blog.blog_schema import BaseBlogResponse


class BlogServices(StrEnum):
    DEVTO = "Dev.to"
    QIITA = "Qiita"
    HATENA = "はてな"


class TypeSingleResult(TypedDict):
    result: BaseBlogResponse | BaseException
    success: bool


TypeBlogResult: TypeAlias = dict[BlogServices, TypeSingleResult]
