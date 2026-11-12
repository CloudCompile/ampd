from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.library_item import LibraryItem
from ...types import Response


def _get_kwargs(
    resource: str,
    resource_id: str,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/library/{resource}/{resource_id}".format(
            resource=quote(str(resource), safe=""),
            resource_id=quote(str(resource_id), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | LibraryItem | None:
    if response.status_code == 200:
        response_200 = LibraryItem.from_dict(response.json())

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
) -> Response[HTTPValidationError | LibraryItem]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    resource: str,
    resource_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | LibraryItem]:
    """Get Resource

     One library item, with its relationships (e.g. an album's track list).

    Args:
        resource (str):
        resource_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LibraryItem]
    """

    kwargs = _get_kwargs(
        resource=resource,
        resource_id=resource_id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    resource: str,
    resource_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | LibraryItem | None:
    """Get Resource

     One library item, with its relationships (e.g. an album's track list).

    Args:
        resource (str):
        resource_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LibraryItem
    """

    return sync_detailed(
        resource=resource,
        resource_id=resource_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    resource: str,
    resource_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | LibraryItem]:
    """Get Resource

     One library item, with its relationships (e.g. an album's track list).

    Args:
        resource (str):
        resource_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LibraryItem]
    """

    kwargs = _get_kwargs(
        resource=resource,
        resource_id=resource_id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    resource: str,
    resource_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | LibraryItem | None:
    """Get Resource

     One library item, with its relationships (e.g. an album's track list).

    Args:
        resource (str):
        resource_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LibraryItem
    """

    return (
        await asyncio_detailed(
            resource=resource,
            resource_id=resource_id,
            client=client,
        )
    ).parsed
