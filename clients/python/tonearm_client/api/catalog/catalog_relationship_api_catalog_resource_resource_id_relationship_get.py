from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.relationship_page import RelationshipPage
from ...types import UNSET, Response, Unset


def _get_kwargs(
    resource: str,
    resource_id: str,
    relationship: str,
    *,
    limit: int | Unset = 100,
    offset: int | Unset = 0,
    storefront: None | str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["limit"] = limit

    params["offset"] = offset

    json_storefront: None | str | Unset
    if isinstance(storefront, Unset):
        json_storefront = UNSET
    else:
        json_storefront = storefront
    params["storefront"] = json_storefront

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/catalog/{resource}/{resource_id}/{relationship}".format(
            resource=quote(str(resource), safe=""),
            resource_id=quote(str(resource_id), safe=""),
            relationship=quote(str(relationship), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | RelationshipPage | None:
    if response.status_code == 200:
        response_200 = RelationshipPage.from_dict(response.json())

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
) -> Response[HTTPValidationError | RelationshipPage]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    resource: str,
    resource_id: str,
    relationship: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    offset: int | Unset = 0,
    storefront: None | str | Unset = UNSET,
) -> Response[HTTPValidationError | RelationshipPage]:
    """Catalog Relationship

     e.g. /catalog/artists/{id}/albums, /catalog/albums/{id}/tracks.

    Args:
        resource (str):
        resource_id (str):
        relationship (str):
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.
        storefront (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RelationshipPage]
    """

    kwargs = _get_kwargs(
        resource=resource,
        resource_id=resource_id,
        relationship=relationship,
        limit=limit,
        offset=offset,
        storefront=storefront,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    resource: str,
    resource_id: str,
    relationship: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    offset: int | Unset = 0,
    storefront: None | str | Unset = UNSET,
) -> HTTPValidationError | RelationshipPage | None:
    """Catalog Relationship

     e.g. /catalog/artists/{id}/albums, /catalog/albums/{id}/tracks.

    Args:
        resource (str):
        resource_id (str):
        relationship (str):
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.
        storefront (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RelationshipPage
    """

    return sync_detailed(
        resource=resource,
        resource_id=resource_id,
        relationship=relationship,
        client=client,
        limit=limit,
        offset=offset,
        storefront=storefront,
    ).parsed


async def asyncio_detailed(
    resource: str,
    resource_id: str,
    relationship: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    offset: int | Unset = 0,
    storefront: None | str | Unset = UNSET,
) -> Response[HTTPValidationError | RelationshipPage]:
    """Catalog Relationship

     e.g. /catalog/artists/{id}/albums, /catalog/albums/{id}/tracks.

    Args:
        resource (str):
        resource_id (str):
        relationship (str):
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.
        storefront (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | RelationshipPage]
    """

    kwargs = _get_kwargs(
        resource=resource,
        resource_id=resource_id,
        relationship=relationship,
        limit=limit,
        offset=offset,
        storefront=storefront,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    resource: str,
    resource_id: str,
    relationship: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    offset: int | Unset = 0,
    storefront: None | str | Unset = UNSET,
) -> HTTPValidationError | RelationshipPage | None:
    """Catalog Relationship

     e.g. /catalog/artists/{id}/albums, /catalog/albums/{id}/tracks.

    Args:
        resource (str):
        resource_id (str):
        relationship (str):
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.
        storefront (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | RelationshipPage
    """

    return (
        await asyncio_detailed(
            resource=resource,
            resource_id=resource_id,
            relationship=relationship,
            client=client,
            limit=limit,
            offset=offset,
            storefront=storefront,
        )
    ).parsed
