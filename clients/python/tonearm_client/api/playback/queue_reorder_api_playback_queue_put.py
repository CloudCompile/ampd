from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.ok import Ok
from ...models.queue_reorder import QueueReorder
from ...types import Response


def _get_kwargs(
    *,
    body: QueueReorder,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "put",
        "url": "/api/playback/queue",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
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
    *,
    client: AuthenticatedClient | Client,
    body: QueueReorder,
) -> Response[HTTPValidationError | Ok]:
    """Queue Reorder

     Reorder the queue: send the FULL ordered list of item ids (#87 —
    whole-list PUT semantics, last write wins, no deltas). The playhead
    stays on the same track at its new index. Best-effort like every
    transport op: MusicKit has no public reorder, so the queue is rebuilt
    and the playhead is moved back onto the same track.

    Args:
        body (QueueReorder): PUT /api/playback/queue body — the FULL ordered list of queue item
            ids (#87: whole-list PUT, never deltas). The playhead stays on the same
            track at its new index.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Ok]
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
    body: QueueReorder,
) -> HTTPValidationError | Ok | None:
    """Queue Reorder

     Reorder the queue: send the FULL ordered list of item ids (#87 —
    whole-list PUT semantics, last write wins, no deltas). The playhead
    stays on the same track at its new index. Best-effort like every
    transport op: MusicKit has no public reorder, so the queue is rebuilt
    and the playhead is moved back onto the same track.

    Args:
        body (QueueReorder): PUT /api/playback/queue body — the FULL ordered list of queue item
            ids (#87: whole-list PUT, never deltas). The playhead stays on the same
            track at its new index.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Ok
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: QueueReorder,
) -> Response[HTTPValidationError | Ok]:
    """Queue Reorder

     Reorder the queue: send the FULL ordered list of item ids (#87 —
    whole-list PUT semantics, last write wins, no deltas). The playhead
    stays on the same track at its new index. Best-effort like every
    transport op: MusicKit has no public reorder, so the queue is rebuilt
    and the playhead is moved back onto the same track.

    Args:
        body (QueueReorder): PUT /api/playback/queue body — the FULL ordered list of queue item
            ids (#87: whole-list PUT, never deltas). The playhead stays on the same
            track at its new index.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Ok]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: QueueReorder,
) -> HTTPValidationError | Ok | None:
    """Queue Reorder

     Reorder the queue: send the FULL ordered list of item ids (#87 —
    whole-list PUT semantics, last write wins, no deltas). The playhead
    stays on the same track at its new index. Best-effort like every
    transport op: MusicKit has no public reorder, so the queue is rebuilt
    and the playhead is moved back onto the same track.

    Args:
        body (QueueReorder): PUT /api/playback/queue body — the FULL ordered list of queue item
            ids (#87: whole-list PUT, never deltas). The playhead stays on the same
            track at its new index.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Ok
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
