from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.webhook_hook import WebhookHook
from ...models.webhook_update import WebhookUpdate
from ...types import Response


def _get_kwargs(
    hook_id: str,
    *,
    body: WebhookUpdate,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/api/webhooks/{hook_id}".format(
            hook_id=quote(str(hook_id), safe=""),
        ),
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
    hook_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: WebhookUpdate,
) -> Response[HTTPValidationError | WebhookHook]:
    """Update Hook

     Partial update. Omitted fields stay as they are; `secret: ""` clears
    the signing secret.

    Args:
        hook_id (str):
        body (WebhookUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | WebhookHook]
    """

    kwargs = _get_kwargs(
        hook_id=hook_id,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    hook_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: WebhookUpdate,
) -> HTTPValidationError | WebhookHook | None:
    """Update Hook

     Partial update. Omitted fields stay as they are; `secret: ""` clears
    the signing secret.

    Args:
        hook_id (str):
        body (WebhookUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | WebhookHook
    """

    return sync_detailed(
        hook_id=hook_id,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    hook_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: WebhookUpdate,
) -> Response[HTTPValidationError | WebhookHook]:
    """Update Hook

     Partial update. Omitted fields stay as they are; `secret: ""` clears
    the signing secret.

    Args:
        hook_id (str):
        body (WebhookUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | WebhookHook]
    """

    kwargs = _get_kwargs(
        hook_id=hook_id,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    hook_id: str,
    *,
    client: AuthenticatedClient | Client,
    body: WebhookUpdate,
) -> HTTPValidationError | WebhookHook | None:
    """Update Hook

     Partial update. Omitted fields stay as they are; `secret: ""` clears
    the signing secret.

    Args:
        hook_id (str):
        body (WebhookUpdate):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | WebhookHook
    """

    return (
        await asyncio_detailed(
            hook_id=hook_id,
            client=client,
            body=body,
        )
    ).parsed
