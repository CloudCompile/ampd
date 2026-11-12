from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.ok_shuffle import OkShuffle
from ...types import Response


def _get_kwargs(
    mode: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/playback/shuffle/{mode}".format(
            mode=quote(str(mode), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | OkShuffle | None:
    if response.status_code == 200:
        response_200 = OkShuffle.from_dict(response.json())

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
) -> Response[HTTPValidationError | OkShuffle]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    mode: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | OkShuffle]:
    """Shuffle

    Args:
        mode (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | OkShuffle]
    """

    kwargs = _get_kwargs(
        mode=mode,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    mode: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | OkShuffle | None:
    """Shuffle

    Args:
        mode (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | OkShuffle
    """

    return sync_detailed(
        mode=mode,
        client=client,
    ).parsed


async def asyncio_detailed(
    mode: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | OkShuffle]:
    """Shuffle

    Args:
        mode (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | OkShuffle]
    """

    kwargs = _get_kwargs(
        mode=mode,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    mode: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | OkShuffle | None:
    """Shuffle

    Args:
        mode (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | OkShuffle
    """

    return (
        await asyncio_detailed(
            mode=mode,
            client=client,
        )
    ).parsed
