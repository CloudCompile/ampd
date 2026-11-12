from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.library_search_api_library_search_get_response_library_search_api_library_search_get import (
    LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet,
)
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    term: str,
    limit: int | Unset = 25,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["term"] = term

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/library/search",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet | None:
    if response.status_code == 200:
        response_200 = LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet.from_dict(
            response.json()
        )

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
) -> Response[HTTPValidationError | LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet]:
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
    limit: int | Unset = 25,
) -> Response[HTTPValidationError | LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet]:
    """Library Search

     Search YOUR library across songs/albums/artists/playlists.

    Args:
        term (str):
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet]
    """

    kwargs = _get_kwargs(
        term=term,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    term: str,
    limit: int | Unset = 25,
) -> HTTPValidationError | LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet | None:
    """Library Search

     Search YOUR library across songs/albums/artists/playlists.

    Args:
        term (str):
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet
    """

    return sync_detailed(
        client=client,
        term=term,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    term: str,
    limit: int | Unset = 25,
) -> Response[HTTPValidationError | LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet]:
    """Library Search

     Search YOUR library across songs/albums/artists/playlists.

    Args:
        term (str):
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet]
    """

    kwargs = _get_kwargs(
        term=term,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    term: str,
    limit: int | Unset = 25,
) -> HTTPValidationError | LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet | None:
    """Library Search

     Search YOUR library across songs/albums/artists/playlists.

    Args:
        term (str):
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LibrarySearchApiLibrarySearchGetResponseLibrarySearchApiLibrarySearchGet
    """

    return (
        await asyncio_detailed(
            client=client,
            term=term,
            limit=limit,
        )
    ).parsed
