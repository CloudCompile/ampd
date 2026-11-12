from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.rating_state import RatingState
from ...types import UNSET, Response, Unset


def _get_kwargs(
    song_id: str,
    *,
    fresh: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["fresh"] = fresh

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/write/ratings/songs/{song_id}".format(
            song_id=quote(str(song_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | RatingState | None:
    if response.status_code == 200:
        response_200 = RatingState.from_dict(response.json())

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
) -> Response[HTTPValidationError | RatingState]:
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
    fresh: bool | Unset = False,
) -> Response[HTTPValidationError | RatingState]:
    """Get Rating

     Current rating of a song: null = none, 1 = like.
    Ratings lag server-side after a mutation; `?fresh=1` bypasses cache.

    Args:
        song_id (str):
        fresh (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RatingState]
    """

    kwargs = _get_kwargs(
        song_id=song_id,
        fresh=fresh,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    fresh: bool | Unset = False,
) -> HTTPValidationError | RatingState | None:
    """Get Rating

     Current rating of a song: null = none, 1 = like.
    Ratings lag server-side after a mutation; `?fresh=1` bypasses cache.

    Args:
        song_id (str):
        fresh (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RatingState
    """

    return sync_detailed(
        song_id=song_id,
        client=client,
        fresh=fresh,
    ).parsed


async def asyncio_detailed(
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    fresh: bool | Unset = False,
) -> Response[HTTPValidationError | RatingState]:
    """Get Rating

     Current rating of a song: null = none, 1 = like.
    Ratings lag server-side after a mutation; `?fresh=1` bypasses cache.

    Args:
        song_id (str):
        fresh (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RatingState]
    """

    kwargs = _get_kwargs(
        song_id=song_id,
        fresh=fresh,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    fresh: bool | Unset = False,
) -> HTTPValidationError | RatingState | None:
    """Get Rating

     Current rating of a song: null = none, 1 = like.
    Ratings lag server-side after a mutation; `?fresh=1` bypasses cache.

    Args:
        song_id (str):
        fresh (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RatingState
    """

    return (
        await asyncio_detailed(
            song_id=song_id,
            client=client,
            fresh=fresh,
        )
    ).parsed
