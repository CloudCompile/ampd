from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.search_hints import SearchHints
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    term: str,
    types: str | Unset = "songs,artists,albums,playlists",
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["term"] = term

    params["types"] = types

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/catalog/hints",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | SearchHints | None:
    if response.status_code == 200:
        response_200 = SearchHints.from_dict(response.json())

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> Response[HTTPValidationError | SearchHints]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    term: str,
    types: str | Unset = "songs,artists,albums,playlists",
) -> Response[HTTPValidationError | SearchHints]:
    """Hints

     Search suggestions (what the web player's autocomplete shows).
    Returns flat rows: {term/title, id, kind}.

    Args:
        term (str):
        types (str | Unset):  Default: 'songs,artists,albums,playlists'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchHints]
    """

    kwargs = _get_kwargs(
        term=term,
        types=types,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    term: str,
    types: str | Unset = "songs,artists,albums,playlists",
) -> HTTPValidationError | SearchHints | None:
    """Hints

     Search suggestions (what the web player's autocomplete shows).
    Returns flat rows: {term/title, id, kind}.

    Args:
        term (str):
        types (str | Unset):  Default: 'songs,artists,albums,playlists'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchHints
    """

    return sync_detailed(
        client=client,
        term=term,
        types=types,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    term: str,
    types: str | Unset = "songs,artists,albums,playlists",
) -> Response[HTTPValidationError | SearchHints]:
    """Hints

     Search suggestions (what the web player's autocomplete shows).
    Returns flat rows: {term/title, id, kind}.

    Args:
        term (str):
        types (str | Unset):  Default: 'songs,artists,albums,playlists'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SearchHints]
    """

    kwargs = _get_kwargs(
        term=term,
        types=types,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    term: str,
    types: str | Unset = "songs,artists,albums,playlists",
) -> HTTPValidationError | SearchHints | None:
    """Hints

     Search suggestions (what the web player's autocomplete shows).
    Returns flat rows: {term/title, id, kind}.

    Args:
        term (str):
        types (str | Unset):  Default: 'songs,artists,albums,playlists'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SearchHints
    """

    return (
        await asyncio_detailed(
            client=client,
            term=term,
            types=types,
        )
    ).parsed
