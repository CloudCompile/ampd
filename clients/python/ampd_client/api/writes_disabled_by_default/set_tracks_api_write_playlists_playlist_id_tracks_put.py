from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.ok import Ok
from ...types import UNSET, Response, Unset


def _get_kwargs(
    playlist_id: str,
    *,
    body: list[str] | Unset = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/write/playlists/{playlist_id}/tracks".format(
            playlist_id=quote(str(playlist_id), safe=""),
        ),
    }

    if not isinstance(body, Unset):
        _kwargs["json"] = body

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | Ok | None:
    if response.status_code == 200:
        response_200 = Ok.from_dict(response.json())

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
) -> Response[HTTPValidationError | Ok]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    playlist_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: list[str] | Unset = UNSET,
) -> Response[HTTPValidationError | Ok]:
    """Set Tracks

     REPLACE the track list, in order. Body is a bare JSON array of
    library-songs ids. This is both reorder and removal: send the full
    list minus any song you want gone.
    e.g.  curl -X PUT -d '["i.abc","i.def"]' /api/write/playlists/{pid}/tracks

    Args:
        playlist_id (str):
        body (list[str] | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Ok]
    """

    kwargs = _get_kwargs(
        playlist_id=playlist_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    playlist_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: list[str] | Unset = UNSET,
) -> HTTPValidationError | Ok | None:
    """Set Tracks

     REPLACE the track list, in order. Body is a bare JSON array of
    library-songs ids. This is both reorder and removal: send the full
    list minus any song you want gone.
    e.g.  curl -X PUT -d '["i.abc","i.def"]' /api/write/playlists/{pid}/tracks

    Args:
        playlist_id (str):
        body (list[str] | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Ok
    """

    return sync_detailed(
        playlist_id=playlist_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    playlist_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: list[str] | Unset = UNSET,
) -> Response[HTTPValidationError | Ok]:
    """Set Tracks

     REPLACE the track list, in order. Body is a bare JSON array of
    library-songs ids. This is both reorder and removal: send the full
    list minus any song you want gone.
    e.g.  curl -X PUT -d '["i.abc","i.def"]' /api/write/playlists/{pid}/tracks

    Args:
        playlist_id (str):
        body (list[str] | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Ok]
    """

    kwargs = _get_kwargs(
        playlist_id=playlist_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    playlist_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: list[str] | Unset = UNSET,
) -> HTTPValidationError | Ok | None:
    """Set Tracks

     REPLACE the track list, in order. Body is a bare JSON array of
    library-songs ids. This is both reorder and removal: send the full
    list minus any song you want gone.
    e.g.  curl -X PUT -d '["i.abc","i.def"]' /api/write/playlists/{pid}/tracks

    Args:
        playlist_id (str):
        body (list[str] | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Ok
    """

    return (
        await asyncio_detailed(
            playlist_id=playlist_id,
            client=client,
            body=body,
        )
    ).parsed
