# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
# pylint: disable=docstring-keyword-should-match-keyword-only

import uuid
from typing import (
    Union, Optional, Any,
    TYPE_CHECKING
)
from typing_extensions import Self

from azure.core.tracing.decorator_async import distributed_trace_async
from azure.storage.blob.aio import BlobLeaseClient

if TYPE_CHECKING:
    from datetime import datetime
    from azure.storage.filedatalake.aio import FileSystemClient
    from ._path_client_async import PathClient


class DataLakeLeaseClient:  # pylint: disable=client-accepts-api-version-keyword
    """Creates a new DataLakeLeaseClient.

    This client provides lease operations on a FileSystemClient, DataLakeDirectoryClient or DataLakeFileClient.

    :param client:
        The client of the file system, directory, or file to lease.
    :type client:
        ~azure.storage.filedatalake.aio.FileSystemClient or
        ~azure.storage.filedatalake.aio.DataLakeDirectoryClient or
        ~azure.storage.filedatalake.aio.DataLakeFileClient
    :param str lease_id:
        A string representing the lease ID of an existing lease. This value does not
        need to be specified in order to acquire a new lease, or break one.
    """

    id: str
    """The ID of the lease currently being maintained. This will be `None` if no
        lease has yet been acquired."""
    etag: Optional[str]
    """The ETag of the lease currently being maintained. This will be `None` if no
        lease has yet been acquired or modified."""
    last_modified: Optional["datetime"]
    """The last modified timestamp of the lease currently being maintained.
        This will be `None` if no lease has yet been acquired or modified."""

    def __init__(  # pylint: disable=missing-client-constructor-parameter-credential, missing-client-constructor-parameter-kwargs
        self, client: Union["FileSystemClient", "PathClient"],
        lease_id: Optional[str] = None
    ) -> None:
        self.id = lease_id or str(uuid.uuid4())
        self.last_modified = None
        self.etag = None

        if hasattr(client, '_blob_client'):
            _client = client._blob_client
        elif hasattr(client, '_container_client'):
            _client = client._container_client
        else:
            raise TypeError("Lease must use any of FileSystemClient, DataLakeDirectoryClient, or DataLakeFileClient.")

        self._blob_lease_client = BlobLeaseClient(_client, lease_id=lease_id)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.release()

    @distributed_trace_async
    async def acquire(self, lease_duration: int = -1, **kwargs: Any) -> None:
        """Requests a new lease.

        If the file/file system does not have an active lease, the DataLake service creates a
        lease on the file/file system and returns a new lease ID.

        :param int lease_duration:
            Specifies the duration of the lease, in seconds, or negative one
            (-1) for a lease that never expires. A non-infinite lease can be
            between 15 and 60 seconds. A lease duration cannot be changed
            using renew or change. Default is -1 (infinite lease).
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :rtype: None
        """
        await self._blob_lease_client.acquire(lease_duration=lease_duration, **kwargs)
        self._update_lease_client_attributes()

    @distributed_trace_async
    async def renew(self, **kwargs: Any) -> None:
        """Renews the lease.

        The lease can be renewed if the lease ID specified in the
        lease client matches that associated with the file system or file. Note that
        the lease may be renewed even if it has expired as long as the file system
        or file has not been leased again since the expiration of that lease. When you
        renew a lease, the lease duration clock resets.

        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :return: None
        """
        await self._blob_lease_client.renew(**kwargs)
        self._update_lease_client_attributes()

    @distributed_trace_async
    async def release(self, **kwargs: Any) -> None:
        """Release the lease.

        The lease may be released if the client lease id specified matches
        that associated with the file system or file. Releasing the lease allows another client
        to immediately acquire the lease for the file system or file as soon as the release is complete.

        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :return: None
        """
        await self._blob_lease_client.release(**kwargs)
        self._update_lease_client_attributes()

    @distributed_trace_async
    async def change(self, proposed_lease_id: str, **kwargs: Any) -> None:
        """Change the lease ID of an active lease.

        :param str proposed_lease_id:
            Proposed lease ID, in a GUID string format. The DataLake service returns 400
            (Invalid request) if the proposed lease ID is not in the correct format.
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword str etag:
            An ETag value, or the wildcard character (*). Used to check if the resource has changed,
            and act according to the condition specified by the `match_condition` parameter.
        :keyword ~azure.core.MatchConditions match_condition:
            The match condition to use upon the etag.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :return: None
        """
        await self._blob_lease_client.change(proposed_lease_id=proposed_lease_id, **kwargs)
        self._update_lease_client_attributes()

    @distributed_trace_async
    async def break_lease(self, lease_break_period: Optional[int] = None, **kwargs: Any) -> int:
        """Break the lease, if the file system or file has an active lease.

        Once a lease is broken, it cannot be renewed. Any authorized request can break the lease;
        the request is not required to specify a matching lease ID. When a lease
        is broken, the lease break period is allowed to elapse, during which time
        no lease operation except break and release can be performed on the file system or file.
        When a lease is successfully broken, the response indicates the interval
        in seconds until a new lease can be acquired.

        :param int lease_break_period:
            This is the proposed duration of seconds that the lease
            should continue before it is broken, between 0 and 60 seconds. This
            break period is only used if it is shorter than the time remaining
            on the lease. If longer, the time remaining on the lease is used.
            A new lease will not be available before the break period has
            expired, but the lease may be held for longer than the break
            period. If this header does not appear with a break
            operation, a fixed-duration lease breaks after the remaining lease
            period elapses, and an infinite lease breaks immediately.
        :keyword ~datetime.datetime if_modified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only
            if the resource has been modified since the specified time.
        :keyword ~datetime.datetime if_unmodified_since:
            A DateTime value. Azure expects the date value passed in to be UTC.
            If timezone is included, any non-UTC datetimes will be converted to UTC.
            If a date is passed in without timezone info, it is assumed to be UTC.
            Specify this header to perform the operation only if
            the resource has not been modified since the specified date/time.
        :keyword int timeout:
            Sets the server-side timeout for the operation in seconds. For more details see
            https://learn.microsoft.com/rest/api/storageservices/setting-timeouts-for-blob-service-operations.
            This value is not tracked or validated on the client. To configure client-side network timesouts
            see `here <https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/storage/azure-storage-file-datalake
            #other-client--per-operation-configuration>`_.
        :return: Approximate time remaining in the lease period, in seconds.
        :rtype: int
        """
        return await self._blob_lease_client.break_lease(lease_break_period=lease_break_period, **kwargs)

    def _update_lease_client_attributes(self) -> None:
        self.id = self._blob_lease_client.id
        self.last_modified = self._blob_lease_client.last_modified
        self.etag = self._blob_lease_client.etag
