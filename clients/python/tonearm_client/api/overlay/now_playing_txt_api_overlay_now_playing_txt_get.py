from http import HTTPStatus
from typing import Any

import httpx2

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    format_: str | Unset = "{title} — {artist}",
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["format"] = format_

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/overlay/now-playing.txt",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx2.Response
) -> HTTPValidationError | str | None:
    if response.status_code == 200:
        response_200 = response.text
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
) -> Response[HTTPValidationError | str]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    format_: str | Unset = "{title} — {artist}",
) -> Response[HTTPValidationError | str]:
    """Now Playing Txt

     Now-playing as one text line. `?format=` is a template with
    {title} {artist} {album} {elapsed} {duration} placeholders — unknown
    fields and missing values render as ''. Text (not JSON) on purpose:
    OBS's classic Text source wants a plain line.

    Args:
        format_ (str | Unset):  Default: '{title} — {artist}'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | str]
    """

    kwargs = _get_kwargs(
        format_=format_,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    format_: str | Unset = "{title} — {artist}",
) -> HTTPValidationError | str | None:
    """Now Playing Txt

     Now-playing as one text line. `?format=` is a template with
    {title} {artist} {album} {elapsed} {duration} placeholders — unknown
    fields and missing values render as ''. Text (not JSON) on purpose:
    OBS's classic Text source wants a plain line.

    Args:
        format_ (str | Unset):  Default: '{title} — {artist}'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | str
    """

    return sync_detailed(
        client=client,
        format_=format_,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    format_: str | Unset = "{title} — {artist}",
) -> Response[HTTPValidationError | str]:
    """Now Playing Txt

     Now-playing as one text line. `?format=` is a template with
    {title} {artist} {album} {elapsed} {duration} placeholders — unknown
    fields and missing values render as ''. Text (not JSON) on purpose:
    OBS's classic Text source wants a plain line.

    Args:
        format_ (str | Unset):  Default: '{title} — {artist}'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | str]
    """

    kwargs = _get_kwargs(
        format_=format_,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    format_: str | Unset = "{title} — {artist}",
) -> HTTPValidationError | str | None:
    """Now Playing Txt

     Now-playing as one text line. `?format=` is a template with
    {title} {artist} {album} {elapsed} {duration} placeholders — unknown
    fields and missing values render as ''. Text (not JSON) on purpose:
    OBS's classic Text source wants a plain line.

    Args:
        format_ (str | Unset):  Default: '{title} — {artist}'.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx2.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | str
    """

    return (
        await asyncio_detailed(
            client=client,
            format_=format_,
        )
    ).parsed
