from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.webhook_create import WebhookCreate
from ...models.webhook_hook import WebhookHook
from ...types import Response


def _get_kwargs(
    *,
    body: WebhookCreate,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/webhooks",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | WebhookHook | None:
    if response.status_code == 200:
        response_200 = WebhookHook.from_dict(response.json())

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
) -> Response[HTTPValidationError | WebhookHook]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: WebhookCreate,
) -> Response[HTTPValidationError | WebhookHook]:
    """Create Hook

     Add a webhook. `events` is an optional filter (empty = everything);
    `secret` enables HMAC-SHA256 signing. Adding an existing URL updates it.

    Args:
        body (WebhookCreate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | WebhookHook]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: WebhookCreate,
) -> HTTPValidationError | WebhookHook | None:
    """Create Hook

     Add a webhook. `events` is an optional filter (empty = everything);
    `secret` enables HMAC-SHA256 signing. Adding an existing URL updates it.

    Args:
        body (WebhookCreate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | WebhookHook
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: WebhookCreate,
) -> Response[HTTPValidationError | WebhookHook]:
    """Create Hook

     Add a webhook. `events` is an optional filter (empty = everything);
    `secret` enables HMAC-SHA256 signing. Adding an existing URL updates it.

    Args:
        body (WebhookCreate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | WebhookHook]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: WebhookCreate,
) -> HTTPValidationError | WebhookHook | None:
    """Create Hook

     Add a webhook. `events` is an optional filter (empty = everything);
    `secret` enables HMAC-SHA256 signing. Adding an existing URL updates it.

    Args:
        body (WebhookCreate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | WebhookHook
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
