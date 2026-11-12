from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.sweep_digest import SweepDigest
from ...types import Response


def _get_kwargs() -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/write/sweeps/digest",
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx2.Response) -> SweepDigest | None:
    if response.status_code == 200:
        response_200 = SweepDigest.from_dict(response.json())

        return response_200

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx2.Response) -> Response[SweepDigest]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[SweepDigest]:
    """Digest

     Dry-run digest: dedupe + never-played from ONE library walk.
    The same payload is emitted as `sweep.digest` on the scheduled cadence
    (TONEARM_DIGEST_INTERVAL + TONEARM_WEBHOOKS=1).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[SweepDigest]
    """

    kwargs = _get_kwargs()

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> SweepDigest | None:
    """Digest

     Dry-run digest: dedupe + never-played from ONE library walk.
    The same payload is emitted as `sweep.digest` on the scheduled cadence
    (TONEARM_DIGEST_INTERVAL + TONEARM_WEBHOOKS=1).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        SweepDigest
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[SweepDigest]:
    """Digest

     Dry-run digest: dedupe + never-played from ONE library walk.
    The same payload is emitted as `sweep.digest` on the scheduled cadence
    (TONEARM_DIGEST_INTERVAL + TONEARM_WEBHOOKS=1).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[SweepDigest]
    """

    kwargs = _get_kwargs()

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> SweepDigest | None:
    """Digest

     Dry-run digest: dedupe + never-played from ONE library walk.
    The same payload is emitted as `sweep.digest` on the scheduled cadence
    (TONEARM_DIGEST_INTERVAL + TONEARM_WEBHOOKS=1).

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        SweepDigest
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed
