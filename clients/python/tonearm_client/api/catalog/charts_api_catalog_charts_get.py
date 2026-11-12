from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.charts_api_catalog_charts_get_response_charts_api_catalog_charts_get import (
    ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet,
)
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    types: str | Unset = "songs",
    limit: int | Unset = 25,
    genre: str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["types"] = types

    params["limit"] = limit

    params["genre"] = genre

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/catalog/charts",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet.from_dict(response.json())

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
) -> Response[ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    types: str | Unset = "songs",
    limit: int | Unset = 25,
    genre: str | Unset = UNSET,
) -> Response[ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet | HTTPValidationError]:
    """Charts

     Catalog charts: most-played songs/albums/playlists. `genre` = genre id.

    Args:
        types (str | Unset):  Default: 'songs'.
        limit (int | Unset):  Default: 25.
        genre (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        types=types,
        limit=limit,
        genre=genre,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    types: str | Unset = "songs",
    limit: int | Unset = 25,
    genre: str | Unset = UNSET,
) -> ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet | HTTPValidationError | None:
    """Charts

     Catalog charts: most-played songs/albums/playlists. `genre` = genre id.

    Args:
        types (str | Unset):  Default: 'songs'.
        limit (int | Unset):  Default: 25.
        genre (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        types=types,
        limit=limit,
        genre=genre,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    types: str | Unset = "songs",
    limit: int | Unset = 25,
    genre: str | Unset = UNSET,
) -> Response[ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet | HTTPValidationError]:
    """Charts

     Catalog charts: most-played songs/albums/playlists. `genre` = genre id.

    Args:
        types (str | Unset):  Default: 'songs'.
        limit (int | Unset):  Default: 25.
        genre (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        types=types,
        limit=limit,
        genre=genre,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    types: str | Unset = "songs",
    limit: int | Unset = 25,
    genre: str | Unset = UNSET,
) -> ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet | HTTPValidationError | None:
    """Charts

     Catalog charts: most-played songs/albums/playlists. `genre` = genre id.

    Args:
        types (str | Unset):  Default: 'songs'.
        limit (int | Unset):  Default: 25.
        genre (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ChartsApiCatalogChartsGetResponseChartsApiCatalogChartsGet | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            types=types,
            limit=limit,
            genre=genre,
        )
    ).parsed
