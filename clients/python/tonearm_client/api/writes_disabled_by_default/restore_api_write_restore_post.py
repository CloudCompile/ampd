from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.restore_api_write_restore_post_source import RestoreApiWriteRestorePostSource
from ...models.restore_executed import RestoreExecuted
from ...models.restore_plan import RestorePlan
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: RestoreApiWriteRestorePostSource | Unset = UNSET,
    execute: int | Unset = 0,
    match_budget: int | Unset = 2000,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["execute"] = execute

    params["match_budget"] = match_budget

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/write/restore",
        "params": params,
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | RestoreExecuted | RestorePlan | None:
    if response.status_code == 200:

        def _parse_response_200(data: object) -> RestoreExecuted | RestorePlan:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_0 = RestorePlan.from_dict(data)

                return response_200_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_200_type_1 = RestoreExecuted.from_dict(data)

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
) -> Response[HTTPValidationError | RestoreExecuted | RestorePlan]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: RestoreApiWriteRestorePostSource | Unset = UNSET,
    execute: int | Unset = 0,
    match_budget: int | Unset = 2000,
) -> Response[HTTPValidationError | RestoreExecuted | RestorePlan]:
    """Restore

     Restore playlists from a /api/library/export JSON body.

    DRY-RUN BY DEFAULT: returns the plan (per playlist: exists/create,
    per track: catalog-id / name-match / unmatched-with-reason).
    `?execute=1` runs it: creates missing playlists, adds tracks, verifies
    counts with bounded retries (Apple's applies are async).

    The unmatched report is the contract: nothing is ever dropped silently.

    Args:
        execute (int | Unset):  Default: 0.
        match_budget (int | Unset):  Default: 2000.
        body (RestoreApiWriteRestorePostSource | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RestoreExecuted | RestorePlan]
    """

    kwargs = _get_kwargs(
        body=body,
        execute=execute,
        match_budget=match_budget,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: RestoreApiWriteRestorePostSource | Unset = UNSET,
    execute: int | Unset = 0,
    match_budget: int | Unset = 2000,
) -> HTTPValidationError | RestoreExecuted | RestorePlan | None:
    """Restore

     Restore playlists from a /api/library/export JSON body.

    DRY-RUN BY DEFAULT: returns the plan (per playlist: exists/create,
    per track: catalog-id / name-match / unmatched-with-reason).
    `?execute=1` runs it: creates missing playlists, adds tracks, verifies
    counts with bounded retries (Apple's applies are async).

    The unmatched report is the contract: nothing is ever dropped silently.

    Args:
        execute (int | Unset):  Default: 0.
        match_budget (int | Unset):  Default: 2000.
        body (RestoreApiWriteRestorePostSource | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RestoreExecuted | RestorePlan
    """

    return sync_detailed(
        client=client,
        body=body,
        execute=execute,
        match_budget=match_budget,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: RestoreApiWriteRestorePostSource | Unset = UNSET,
    execute: int | Unset = 0,
    match_budget: int | Unset = 2000,
) -> Response[HTTPValidationError | RestoreExecuted | RestorePlan]:
    """Restore

     Restore playlists from a /api/library/export JSON body.

    DRY-RUN BY DEFAULT: returns the plan (per playlist: exists/create,
    per track: catalog-id / name-match / unmatched-with-reason).
    `?execute=1` runs it: creates missing playlists, adds tracks, verifies
    counts with bounded retries (Apple's applies are async).

    The unmatched report is the contract: nothing is ever dropped silently.

    Args:
        execute (int | Unset):  Default: 0.
        match_budget (int | Unset):  Default: 2000.
        body (RestoreApiWriteRestorePostSource | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RestoreExecuted | RestorePlan]
    """

    kwargs = _get_kwargs(
        body=body,
        execute=execute,
        match_budget=match_budget,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: RestoreApiWriteRestorePostSource | Unset = UNSET,
    execute: int | Unset = 0,
    match_budget: int | Unset = 2000,
) -> HTTPValidationError | RestoreExecuted | RestorePlan | None:
    """Restore

     Restore playlists from a /api/library/export JSON body.

    DRY-RUN BY DEFAULT: returns the plan (per playlist: exists/create,
    per track: catalog-id / name-match / unmatched-with-reason).
    `?execute=1` runs it: creates missing playlists, adds tracks, verifies
    counts with bounded retries (Apple's applies are async).

    The unmatched report is the contract: nothing is ever dropped silently.

    Args:
        execute (int | Unset):  Default: 0.
        match_budget (int | Unset):  Default: 2000.
        body (RestoreApiWriteRestorePostSource | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RestoreExecuted | RestorePlan
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            execute=execute,
            match_budget=match_budget,
        )
    ).parsed
