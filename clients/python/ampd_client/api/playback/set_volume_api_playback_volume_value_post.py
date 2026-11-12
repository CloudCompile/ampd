from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.ok_volume import OkVolume
from ...types import Response


def _get_kwargs(
    value: float,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/playback/volume/{value}".format(
            value=quote(str(value), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | OkVolume | None:
    if response.status_code == 200:
        response_200 = OkVolume.from_dict(response.json())

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
) -> Response[HTTPValidationError | OkVolume]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    value: float,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | OkVolume]:
    """Set Volume

    Args:
        value (float):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | OkVolume]
    """

    kwargs = _get_kwargs(
        value=value,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    value: float,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | OkVolume | None:
    """Set Volume

    Args:
        value (float):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | OkVolume
    """

    return sync_detailed(
        value=value,
        client=client,
    ).parsed


async def asyncio_detailed(
    value: float,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | OkVolume]:
    """Set Volume

    Args:
        value (float):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | OkVolume]
    """

    kwargs = _get_kwargs(
        value=value,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    value: float,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | OkVolume | None:
    """Set Volume

    Args:
        value (float):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | OkVolume
    """

    return (
        await asyncio_detailed(
            value=value,
            client=client,
        )
    ).parsed
