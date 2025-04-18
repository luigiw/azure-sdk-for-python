# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from typing import Union, TYPE_CHECKING
from urllib.parse import quote, unquote, urlparse

if TYPE_CHECKING:
    from urllib.parse import ParseResult


def _parse_url(account_url: str) -> "ParseResult":
    try:
        if not account_url.lower().startswith('http'):
            account_url = "https://" + account_url
    except AttributeError as exc:
        raise ValueError("account URL must be a string.") from exc
    parsed_url = urlparse(account_url.rstrip('/'))
    if not parsed_url.netloc:
        raise ValueError(f"Invalid URL: {account_url}")
    return parsed_url


def _format_url(scheme: str, hostname: str, file_system_name: Union[str, bytes], query_str: str) -> str:
    if isinstance(file_system_name, str):
        file_system_name = file_system_name.encode('UTF-8')
    return f"{scheme}://{hostname}/{quote(file_system_name)}{query_str}"


def _undelete_path_options(deleted_path_name, deletion_id, url):
    quoted_path = quote(unquote(deleted_path_name.strip('/')))
    url_and_token = url.replace('.dfs.', '.blob.').split('?')
    try:
        url = url_and_token[0] + '/' + quoted_path + url_and_token[1]
    except IndexError:
        url = url_and_token[0] + '/' + quoted_path
    undelete_source = quoted_path + f'?deletionid={deletion_id}' if deletion_id else None
    return quoted_path, url, undelete_source
