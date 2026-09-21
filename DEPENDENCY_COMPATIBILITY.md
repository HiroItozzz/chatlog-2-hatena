# HTTPX / HTTPX2 と Authlib の互換性

## 発生したエラー

はてなブログへの OAuth 1.0a 投稿時に、次のエラーが発生した。

```text
TypeError: Invalid "auth" argument:
<authlib.integrations.httpx_client.oauth1_client.OAuth1Auth object ...>
```

投稿コードは `httpx.AsyncClient` に `OAuth1Auth` を渡している。

```python
response = await httpx_client.post(url, auth=auth, content=xml_str, headers=headers)
```

## 原因

`httpx2` は、`httpx` のバージョン 2 ではない。Pydantic が引き継いだ、別名の後継 HTTP クライアントパッケージである。そのため、`httpx.Auth` と `httpx2.Auth` は別クラスであり、相互に交換できない。

Authlib 1.8.0 の `httpx_client` 連携には、次の互換性分岐がある。

```python
try:
    import httpx2
except ImportError:
    import httpx as httpx2
```

つまり、Authlib は両方を同時に扱うのではなく、起動時に利用可能な方を一つ選ぶ。`httpx2` が存在する場合、`OAuth1Auth` は `httpx2.Auth` を継承する。

一方で `httpx.AsyncClient` は `httpx.Auth` のインスタンスだけを `auth=` に受け付ける。そのため、`OAuth1Auth` が `httpx2.Auth` である場合は型検査で失敗する。

## なぜ固定版では成功したか

固定構成では `openai==2.13.0` を使用している。OpenAI Python SDK 2 系は `httpx` を使い、`httpx2` を依存に含めない。

```text
openai==2.13.0
  -> httpx2 が導入されない
  -> Authlib 1.8.0 は httpx2 の import に失敗
  -> httpx をフォールバックとして使用する
  -> OAuth1Auth は httpx.Auth
  -> httpx.AsyncClient と互換
```

範囲指定の構成では、`openai>=3.16.2` が `openai 3.16.2` に解決された。このバージョンは `httpx2` に依存する。

```text
openai==3.16.2
  -> httpx2==2.13.0 が導入される
  -> Authlib 1.8.0 は httpx2 を優先する
  -> OAuth1Auth は httpx2.Auth
  -> httpx.AsyncClient とは非互換
  -> TypeError
```

したがって、問題の直接原因は `openai` 3 系の導入によって `httpx2` が環境に入ったことで、Authlib の自動選択先が `httpx` から `httpx2` に変わったことである。

## 対応方針

HTTP クライアントを一方へ統一する必要がある。

- 現在の投稿コード（`httpx.AsyncClient`）を維持するなら、OpenAI SDK を 2 系に固定する。例: `openai==2.13.0` または `openai<3`。
- OpenAI SDK 3 系を使うなら、はてな投稿を含む Authlib 連携を `httpx2.AsyncClient` に移行する。

`httpx` と `httpx2` の混在自体は可能だが、Authlib 1.8.0 の `OAuth1Auth` と、手動で作成した HTTP クライアントは同じ系列にそろえる必要がある。

## 関連リンク

- [HTTPX2 on PyPI](https://pypi.org/project/httpx2/2.13.0/)
- [Authlib: Support httpx2 over httpx](https://github.com/authlib/authlib/issues/904)
- [OpenAI Python 2.13.0 on PyPI](https://pypi.org/project/openai/2.13.0/)
