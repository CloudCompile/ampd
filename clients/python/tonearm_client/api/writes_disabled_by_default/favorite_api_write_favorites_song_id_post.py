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
    song_id: str,
    *,
    library_key: bool | Unset = False,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["library_key"] = library_key

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/write/favorites/{song_id}".format(
            song_id=quote(str(song_id), safe=""),
        ),
        "params": params,
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
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    library_key: bool | Unset = False,
) -> Response[HTTPValidationError | Ok]:
    """Favorite

     Favorite (heart) a song. `library_key=true` for library-keyed tracks.

    Args:
        song_id (str):
        library_key (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Ok]
    """

    kwargs = _get_kwargs(
        song_id=song_id,
        library_key=library_key,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    library_key: bool | Unset = False,
) -> HTTPValidationError | Ok | None:
    """Favorite

     Favorite (heart) a song. `library_key=true` for library-keyed tracks.

    Args:
        song_id (str):
        library_key (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Ok
    """

    return sync_detailed(
        song_id=song_id,
        client=client,
        library_key=library_key,
    ).parsed


async def asyncio_detailed(
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    library_key: bool | Unset = False,
) -> Response[HTTPValidationError | Ok]:
    """Favorite

     Favorite (heart) a song. `library_key=true` for library-keyed tracks.

    Args:
        song_id (str):
        library_key (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Ok]
    """

    kwargs = _get_kwargs(
        song_id=song_id,
        library_key=library_key,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    song_id: str,
    *,
    client: AuthenticatedClient | Client,
    library_key: bool | Unset = False,
) -> HTTPValidationError | Ok | None:
    """Favorite

     Favorite (heart) a song. `library_key=true` for library-keyed tracks.

    Args:
        song_id (str):
        library_key (bool | Unset):  Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Ok
    """

    return (
        await asyncio_detailed(
            song_id=song_id,
            client=client,
            library_key=library_key,
        )
    ).parsed
