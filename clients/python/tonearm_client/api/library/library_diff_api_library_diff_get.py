from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.diff_added import DiffAdded
from ...models.diff_all import DiffAll
from ...models.diff_removed import DiffRemoved
from ...models.diff_updated import DiffUpdated
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    since: float | Unset = 0.0,
    what: str | Unset = "all",
    limit: int | Unset = 100,
    offset: int | Unset = 0,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["since"] = since

    params["what"] = what

    params["limit"] = limit

    params["offset"] = offset

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/library/diff",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> DiffAdded | DiffAll | DiffRemoved | DiffUpdated | HTTPValidationError | None:
    if response.status_code == 200:

        def _parse_response_200(data: object) -> DiffAdded | DiffAll | DiffRemoved | DiffUpdated:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_0 = DiffAdded.from_dict(data)

                return response_200_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_1 = DiffUpdated.from_dict(data)

                return response_200_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_2 = DiffRemoved.from_dict(data)

                return response_200_type_2
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            response_200_type_3 = DiffAll.from_dict(data)

            return response_200_type_3

        response_200 = _parse_response_200(response.json())

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
) -> Response[DiffAdded | DiffAll | DiffRemoved | DiffUpdated | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    since: float | Unset = 0.0,
    what: str | Unset = "all",
    limit: int | Unset = 100,
    offset: int | Unset = 0,
) -> Response[DiffAdded | DiffAll | DiffRemoved | DiffUpdated | HTTPValidationError]:
    """Library Diff

     What changed in your library since a unix timestamp.

    Apple has no "changed since" filter — this diff is OURS, computed from
    the local store's watermark columns (first_seen / last_seen /
    last_changed) across snapshot walks. So:
      * `since=0` (default) -> the whole library as `added`
      * removals become visible on the FIRST walk AFTER they happen
      * `what` filters: added | updated | removed | all

    Args:
        since (float | Unset):  Default: 0.0.
        what (str | Unset):  Default: 'all'.
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DiffAdded | DiffAll | DiffRemoved | DiffUpdated | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        since=since,
        what=what,
        limit=limit,
        offset=offset,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    since: float | Unset = 0.0,
    what: str | Unset = "all",
    limit: int | Unset = 100,
    offset: int | Unset = 0,
) -> DiffAdded | DiffAll | DiffRemoved | DiffUpdated | HTTPValidationError | None:
    """Library Diff

     What changed in your library since a unix timestamp.

    Apple has no "changed since" filter — this diff is OURS, computed from
    the local store's watermark columns (first_seen / last_seen /
    last_changed) across snapshot walks. So:
      * `since=0` (default) -> the whole library as `added`
      * removals become visible on the FIRST walk AFTER they happen
      * `what` filters: added | updated | removed | all

    Args:
        since (float | Unset):  Default: 0.0.
        what (str | Unset):  Default: 'all'.
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DiffAdded | DiffAll | DiffRemoved | DiffUpdated | HTTPValidationError
    """

    return sync_detailed(
        client=client,
        since=since,
        what=what,
        limit=limit,
        offset=offset,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    since: float | Unset = 0.0,
    what: str | Unset = "all",
    limit: int | Unset = 100,
    offset: int | Unset = 0,
) -> Response[DiffAdded | DiffAll | DiffRemoved | DiffUpdated | HTTPValidationError]:
    """Library Diff

     What changed in your library since a unix timestamp.

    Apple has no "changed since" filter — this diff is OURS, computed from
    the local store's watermark columns (first_seen / last_seen /
    last_changed) across snapshot walks. So:
      * `since=0` (default) -> the whole library as `added`
      * removals become visible on the FIRST walk AFTER they happen
      * `what` filters: added | updated | removed | all

    Args:
        since (float | Unset):  Default: 0.0.
        what (str | Unset):  Default: 'all'.
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DiffAdded | DiffAll | DiffRemoved | DiffUpdated | HTTPValidationError]
    """

    kwargs = _get_kwargs(
        since=since,
        what=what,
        limit=limit,
        offset=offset,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    since: float | Unset = 0.0,
    what: str | Unset = "all",
    limit: int | Unset = 100,
    offset: int | Unset = 0,
) -> DiffAdded | DiffAll | DiffRemoved | DiffUpdated | HTTPValidationError | None:
    """Library Diff

     What changed in your library since a unix timestamp.

    Apple has no "changed since" filter — this diff is OURS, computed from
    the local store's watermark columns (first_seen / last_seen /
    last_changed) across snapshot walks. So:
      * `since=0` (default) -> the whole library as `added`
      * removals become visible on the FIRST walk AFTER they happen
      * `what` filters: added | updated | removed | all

    Args:
        since (float | Unset):  Default: 0.0.
        what (str | Unset):  Default: 'all'.
        limit (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DiffAdded | DiffAll | DiffRemoved | DiffUpdated | HTTPValidationError
    """

    return (
        await asyncio_detailed(
            client=client,
            since=since,
            what=what,
            limit=limit,
            offset=offset,
        )
    ).parsed
