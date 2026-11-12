from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.rate_plan import RatePlan
from ...models.rate_report import RateReport
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    artist: str | Unset = UNSET,
    album: str | Unset = UNSET,
    limit: int | Unset = 500,
    execute: int | Unset = 0,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["artist"] = artist

    params["album"] = album

    params["limit"] = limit

    params["execute"] = execute

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/write/sweeps/rate",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | RatePlan | RateReport | None:
    if response.status_code == 200:

        def _parse_response_200(data: object) -> RatePlan | RateReport:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_0 = RatePlan.from_dict(data)

                return response_200_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_200_type_1 = RateReport.from_dict(data)

            return response_200_type_1

        response_200 = _parse_response_200(response.json())

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
) -> Response[HTTPValidationError | RatePlan | RateReport]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    artist: str | Unset = UNSET,
    album: str | Unset = UNSET,
    limit: int | Unset = 500,
    execute: int | Unset = 0,
) -> Response[HTTPValidationError | RatePlan | RateReport]:
    """Rate Execute

     Heart every library song matching the filter, skipping songs that
    already have a rating. Pass ?execute=1 to actually run it.

    Args:
        artist (str | Unset):
        album (str | Unset):
        limit (int | Unset):  Default: 500.
        execute (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RatePlan | RateReport]
    """

    kwargs = _get_kwargs(
        artist=artist,
        album=album,
        limit=limit,
        execute=execute,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    artist: str | Unset = UNSET,
    album: str | Unset = UNSET,
    limit: int | Unset = 500,
    execute: int | Unset = 0,
) -> HTTPValidationError | RatePlan | RateReport | None:
    """Rate Execute

     Heart every library song matching the filter, skipping songs that
    already have a rating. Pass ?execute=1 to actually run it.

    Args:
        artist (str | Unset):
        album (str | Unset):
        limit (int | Unset):  Default: 500.
        execute (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RatePlan | RateReport
    """

    return sync_detailed(
        client=client,
        artist=artist,
        album=album,
        limit=limit,
        execute=execute,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    artist: str | Unset = UNSET,
    album: str | Unset = UNSET,
    limit: int | Unset = 500,
    execute: int | Unset = 0,
) -> Response[HTTPValidationError | RatePlan | RateReport]:
    """Rate Execute

     Heart every library song matching the filter, skipping songs that
    already have a rating. Pass ?execute=1 to actually run it.

    Args:
        artist (str | Unset):
        album (str | Unset):
        limit (int | Unset):  Default: 500.
        execute (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RatePlan | RateReport]
    """

    kwargs = _get_kwargs(
        artist=artist,
        album=album,
        limit=limit,
        execute=execute,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    artist: str | Unset = UNSET,
    album: str | Unset = UNSET,
    limit: int | Unset = 500,
    execute: int | Unset = 0,
) -> HTTPValidationError | RatePlan | RateReport | None:
    """Rate Execute

     Heart every library song matching the filter, skipping songs that
    already have a rating. Pass ?execute=1 to actually run it.

    Args:
        artist (str | Unset):
        album (str | Unset):
        limit (int | Unset):  Default: 500.
        execute (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RatePlan | RateReport
    """

    return (
        await asyncio_detailed(
            client=client,
            artist=artist,
            album=album,
            limit=limit,
            execute=execute,
        )
    ).parsed
