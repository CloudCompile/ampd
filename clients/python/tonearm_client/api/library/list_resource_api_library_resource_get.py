from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.library_list import LibraryList
from ...types import UNSET, Response, Unset


def _get_kwargs(
    resource: str,
    *,
    limit: int | Unset = 100,
    offset: int | Unset = 0,
    term: str | Unset = UNSET,
    extend: str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["limit"] = limit

    params["offset"] = offset

    params["term"] = term

    params["extend"] = extend

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/library/{resource}".format(
            resource=quote(str(resource), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | LibraryList | None:
    if response.status_code == 200:
        response_200 = LibraryList.from_dict(response.json())

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
) -> Response[HTTPValidationError | LibraryList]:
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
    limit: int | Unset = 100,
    offset: int | Unset = 0,
    term: str | Unset = UNSET,
    extend: str | Unset = UNSET,
) -> Response[HTTPValidationError | LibraryList]:
    """List Resource

     List any library resource, fully paginated by the caller.

    Args:
        resource (str):
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.
        term (str | Unset):
        extend (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LibraryList]
    """

    kwargs = _get_kwargs(
        resource=resource,
        limit=limit,
        offset=offset,
        term=term,
        extend=extend,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    resource: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    offset: int | Unset = 0,
    term: str | Unset = UNSET,
    extend: str | Unset = UNSET,
) -> HTTPValidationError | LibraryList | None:
    """List Resource

     List any library resource, fully paginated by the caller.

    Args:
        resource (str):
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.
        term (str | Unset):
        extend (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LibraryList
    """

    return sync_detailed(
        resource=resource,
        client=client,
        limit=limit,
        offset=offset,
        term=term,
        extend=extend,
    ).parsed


async def asyncio_detailed(
    resource: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    offset: int | Unset = 0,
    term: str | Unset = UNSET,
    extend: str | Unset = UNSET,
) -> Response[HTTPValidationError | LibraryList]:
    """List Resource

     List any library resource, fully paginated by the caller.

    Args:
        resource (str):
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.
        term (str | Unset):
        extend (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | LibraryList]
    """

    kwargs = _get_kwargs(
        resource=resource,
        limit=limit,
        offset=offset,
        term=term,
        extend=extend,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    resource: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    offset: int | Unset = 0,
    term: str | Unset = UNSET,
    extend: str | Unset = UNSET,
) -> HTTPValidationError | LibraryList | None:
    """List Resource

     List any library resource, fully paginated by the caller.

    Args:
        resource (str):
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.
        term (str | Unset):
        extend (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | LibraryList
    """

    return (
        await asyncio_detailed(
            resource=resource,
            client=client,
            limit=limit,
            offset=offset,
            term=term,
            extend=extend,
        )
    ).parsed
