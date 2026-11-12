from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.item_list import ItemList
from ...types import UNSET, Response


def _get_kwargs(
    resource: str,
    *,
    ids: str,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["ids"] = ids

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/catalog/{resource}".format(
            resource=quote(str(resource), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | ItemList | None:
    if response.status_code == 200:
        response_200 = ItemList.from_dict(response.json())

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
) -> Response[HTTPValidationError | ItemList]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    resource: str,
    *,
    client: AuthenticatedClient | Client,
    ids: str,
) -> Response[HTTPValidationError | ItemList]:
    """Catalog By Ids

     Fetch specific catalog resources by (comma-separated) id.

    Args:
        resource (str):
        ids (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ItemList]
    """

    kwargs = _get_kwargs(
        resource=resource,
        ids=ids,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    resource: str,
    *,
    client: AuthenticatedClient | Client,
    ids: str,
) -> HTTPValidationError | ItemList | None:
    """Catalog By Ids

     Fetch specific catalog resources by (comma-separated) id.

    Args:
        resource (str):
        ids (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ItemList
    """

    return sync_detailed(
        resource=resource,
        client=client,
        ids=ids,
    ).parsed


async def asyncio_detailed(
    resource: str,
    *,
    client: AuthenticatedClient | Client,
    ids: str,
) -> Response[HTTPValidationError | ItemList]:
    """Catalog By Ids

     Fetch specific catalog resources by (comma-separated) id.

    Args:
        resource (str):
        ids (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ItemList]
    """

    kwargs = _get_kwargs(
        resource=resource,
        ids=ids,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    resource: str,
    *,
    client: AuthenticatedClient | Client,
    ids: str,
) -> HTTPValidationError | ItemList | None:
    """Catalog By Ids

     Fetch specific catalog resources by (comma-separated) id.

    Args:
        resource (str):
        ids (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ItemList
    """

    return (
        await asyncio_detailed(
            resource=resource,
            client=client,
            ids=ids,
        )
    ).parsed
