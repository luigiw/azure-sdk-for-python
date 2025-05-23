# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""
FILE: file_samples_hello_world_async.py

DESCRIPTION:
    These samples demonstrate common scenarios like instantiating a client,
    creating a file share, and uploading a file to a share.

USAGE:
    python file_samples_hello_world_async.py

    Set the environment variables with your own values before running the sample:
    1) STORAGE_CONNECTION_STRING - the connection string to your storage account
"""

import asyncio
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
DEST_FILE = os.path.join(current_dir, "SampleDestination.txt")
SOURCE_FILE = os.path.join(current_dir, "SampleSource.txt")


class HelloWorldSamplesAsync(object):

    connection_string = os.getenv('STORAGE_CONNECTION_STRING')

    async def create_client_with_connection_string_async(self):
        if self.connection_string is None:
            print("Missing required environment variable: STORAGE_CONNECTION_STRING." + '\n' +
                  "Test: create_client_with_connection_string_async")
            sys.exit(1)


        # Instantiate the ShareServiceClient from a connection string
        from azure.storage.fileshare.aio import ShareServiceClient
        file_service = ShareServiceClient.from_connection_string(self.connection_string)

    async def create_file_share_async(self):
        if self.connection_string is None:
            print("Missing required environment variable: STORAGE_CONNECTION_STRING." + '\n' +
                  "Test: create_file_share_async")
            sys.exit(1)

        # Instantiate the ShareClient from a connection string
        from azure.storage.fileshare.aio import ShareClient
        share = ShareClient.from_connection_string(self.connection_string, share_name="helloworld1async")

        # Create the share
        async with share:
            await share.create_share()

            try:
                # [START get_share_properties]
                properties = await share.get_share_properties()
                # [END get_share_properties]

            finally:
                # Delete the share
                await share.delete_share()

    async def upload_a_file_to_share_async(self):
        if self.connection_string is None:
            print("Missing required environment variable: STORAGE_CONNECTION_STRING." + '\n' +
                  "Test: upload_a_file_to_share_async")
            sys.exit(1)

        # Instantiate the ShareClient from a connection string
        from azure.storage.fileshare.aio import ShareClient
        share = ShareClient.from_connection_string(self.connection_string, share_name='helloworld2async')

        # Create the share
        async with share:
            await share.create_share()

            try:
                # Instantiate the ShareFileClient from a connection string
                # [START create_file_client]
                from azure.storage.fileshare.aio import ShareFileClient
                file = ShareFileClient.from_connection_string(
                    self.connection_string,
                    share_name='helloworld2async',
                    file_path="myfile")
                # [END create_file_client]

                # Upload a file
                async with file:
                    with open(SOURCE_FILE, "rb") as source_file:
                        await file.upload_file(source_file)

            finally:
                # Delete the share
                await share.delete_share()


async def main():
    sample = HelloWorldSamplesAsync()
    await sample.create_client_with_connection_string_async()
    await sample.create_file_share_async()
    await sample.upload_a_file_to_share_async()

if __name__ == '__main__':
    asyncio.run(main())
