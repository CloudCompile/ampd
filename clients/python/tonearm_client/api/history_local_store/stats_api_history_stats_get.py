from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.stats import Stats
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    window: str | Unset = "all",
    limit: int | Unset = 25,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["window"] = window

    params["limit"] = limit

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/history/stats",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | Stats | None:
    if response.status_code == 200:
        response_200 = Stats.from_dict(response.json())

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
) -> Response[HTTPValidationError | Stats]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    window: str | Unset = "all",
    limit: int | Unset = 25,
) -> Response[HTTPValidationError | Stats]:
    """Stats

     Top artists / tracks from the LOCAL play archive (not Apple's).
    window: day | week | month | all. Plays dedupe on (track_id, started_at)
    is the writer's guarantee, so counts are play-starts.

    Args:
        window (str | Unset):  Default: 'all'.
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Stats]
    """

    kwargs = _get_kwargs(
        window=window,
        limit=limit,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    window: str | Unset = "all",
    limit: int | Unset = 25,
) -> HTTPValidationError | Stats | None:
    """Stats

     Top artists / tracks from the LOCAL play archive (not Apple's).
    window: day | week | month | all. Plays dedupe on (track_id, started_at)
    is the writer's guarantee, so counts are play-starts.

    Args:
        window (str | Unset):  Default: 'all'.
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Stats
    """

    return sync_detailed(
        client=client,
        window=window,
        limit=limit,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    window: str | Unset = "all",
    limit: int | Unset = 25,
) -> Response[HTTPValidationError | Stats]:
    """Stats

     Top artists / tracks from the LOCAL play archive (not Apple's).
    window: day | week | month | all. Plays dedupe on (track_id, started_at)
    is the writer's guarantee, so counts are play-starts.

    Args:
        window (str | Unset):  Default: 'all'.
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Stats]
    """

    kwargs = _get_kwargs(
        window=window,
        limit=limit,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    window: str | Unset = "all",
    limit: int | Unset = 25,
) -> HTTPValidationError | Stats | None:
    """Stats

     Top artists / tracks from the LOCAL play archive (not Apple's).
    window: day | week | month | all. Plays dedupe on (track_id, started_at)
    is the writer's guarantee, so counts are play-starts.

    Args:
        window (str | Unset):  Default: 'all'.
        limit (int | Unset):  Default: 25.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Stats
    """

    return (
        await asyncio_detailed(
            client=client,
            window=window,
            limit=limit,
        )
    ).parsed
