from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.ok_rating import OkRating
from ...types import UNSET, Response, Unset


def _get_kwargs(
    song_id: str,
    *,
    rating: str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["rating"] = rating

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/write/ratings/songs/{song_id}".format(
            song_id=quote(str(song_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | OkRating | None:
    if response.status_code == 200:
        response_200 = OkRating.from_dict(response.json())

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
) -> Response[HTTPValidationError | OkRating]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    rating: str | Unset = UNSET,
) -> Response[HTTPValidationError | OkRating]:
    """Rate Song

     rating: 'like' or 'none'.

    Args:
        song_id (str):
        rating (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | OkRating]
    """

    kwargs = _get_kwargs(
        song_id=song_id,
        rating=rating,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    rating: str | Unset = UNSET,
) -> HTTPValidationError | OkRating | None:
    """Rate Song

     rating: 'like' or 'none'.

    Args:
        song_id (str):
        rating (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | OkRating
    """

    return sync_detailed(
        song_id=song_id,
        client=client,
        rating=rating,
    ).parsed


async def asyncio_detailed(
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    rating: str | Unset = UNSET,
) -> Response[HTTPValidationError | OkRating]:
    """Rate Song

     rating: 'like' or 'none'.

    Args:
        song_id (str):
        rating (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | OkRating]
    """

    kwargs = _get_kwargs(
        song_id=song_id,
        rating=rating,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    rating: str | Unset = UNSET,
) -> HTTPValidationError | OkRating | None:
    """Rate Song

     rating: 'like' or 'none'.

    Args:
        song_id (str):
        rating (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | OkRating
    """

    return (
        await asyncio_detailed(
            song_id=song_id,
            client=client,
            rating=rating,
        )
    ).parsed
