from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.smartlist_refresh import SmartlistRefresh
from ...types import Response


def _get_kwargs(
    list_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/smartlists/{list_id}/refresh".format(
            list_id=quote(str(list_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | SmartlistRefresh | None:
    if response.status_code == 200:
        response_200 = SmartlistRefresh.from_dict(response.json())

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
) -> Response[HTTPValidationError | SmartlistRefresh]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    list_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | SmartlistRefresh]:
    """Refresh

     Evaluate + materialize: find-or-create the live playlist, then one
    full-list PUT so Apple matches the evaluation exactly. Requires
    TONEARM_ENABLE_WRITES=1 (evaluation-only? use /preview).

    Args:
        list_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SmartlistRefresh]
    """

    kwargs = _get_kwargs(
        list_id=list_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    list_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | SmartlistRefresh | None:
    """Refresh

     Evaluate + materialize: find-or-create the live playlist, then one
    full-list PUT so Apple matches the evaluation exactly. Requires
    TONEARM_ENABLE_WRITES=1 (evaluation-only? use /preview).

    Args:
        list_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SmartlistRefresh
    """

    return sync_detailed(
        list_id=list_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    list_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | SmartlistRefresh]:
    """Refresh

     Evaluate + materialize: find-or-create the live playlist, then one
    full-list PUT so Apple matches the evaluation exactly. Requires
    TONEARM_ENABLE_WRITES=1 (evaluation-only? use /preview).

    Args:
        list_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SmartlistRefresh]
    """

    kwargs = _get_kwargs(
        list_id=list_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    list_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | SmartlistRefresh | None:
    """Refresh

     Evaluate + materialize: find-or-create the live playlist, then one
    full-list PUT so Apple matches the evaluation exactly. Requires
    TONEARM_ENABLE_WRITES=1 (evaluation-only? use /preview).

    Args:
        list_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SmartlistRefresh
    """

    return (
        await asyncio_detailed(
            list_id=list_id,
            client=client,
        )
    ).parsed
