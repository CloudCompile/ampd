from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.ok import Ok
from ...types import Response


def _get_kwargs(
    library_song_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/write/library/{library_song_id}".format(
            library_song_id=quote(str(library_song_id), safe=""),
        ),
    }

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
    library_song_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | Ok]:
    """Remove From Library

     Remove a song from your library by its library id (i.XXX).
    This is NOT the same as unfavoriting. Destructive — no undo.

    Args:
        library_song_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Ok]
    """

    kwargs = _get_kwargs(
        library_song_id=library_song_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    library_song_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | Ok | None:
    """Remove From Library

     Remove a song from your library by its library id (i.XXX).
    This is NOT the same as unfavoriting. Destructive — no undo.

    Args:
        library_song_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Ok
    """

    return sync_detailed(
        library_song_id=library_song_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    library_song_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | Ok]:
    """Remove From Library

     Remove a song from your library by its library id (i.XXX).
    This is NOT the same as unfavoriting. Destructive — no undo.

    Args:
        library_song_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Ok]
    """

    kwargs = _get_kwargs(
        library_song_id=library_song_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    library_song_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | Ok | None:
    """Remove From Library

     Remove a song from your library by its library id (i.XXX).
    This is NOT the same as unfavoriting. Destructive — no undo.

    Args:
        library_song_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Ok
    """

    return (
        await asyncio_detailed(
            library_song_id=library_song_id,
            client=client,
        )
    ).parsed
