# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
import pytest
from azure.mgmt.loganalytics.aio import LogAnalyticsManagementClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer
from devtools_testutils.aio import recorded_by_proxy_async

AZURE_LOCATION = "eastus"


@pytest.mark.skip("you may need to update the auto-generated test case before run it")
class TestLogAnalyticsManagementLinkedServicesOperationsAsync(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(LogAnalyticsManagementClient, is_async=True)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_begin_create_or_update(self, resource_group):
        response = await (
            await self.client.linked_services.begin_create_or_update(
                resource_group_name=resource_group.name,
                workspace_name="str",
                linked_service_name="str",
                parameters={
                    "id": "str",
                    "name": "str",
                    "provisioningState": "str",
                    "resourceId": "str",
                    "tags": {"str": "str"},
                    "type": "str",
                    "writeAccessResourceId": "str",
                },
                api_version="2020-08-01",
            )
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_begin_delete(self, resource_group):
        response = await (
            await self.client.linked_services.begin_delete(
                resource_group_name=resource_group.name,
                workspace_name="str",
                linked_service_name="str",
                api_version="2020-08-01",
            )
        ).result()  # call '.result()' to poll until service return final result

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_get(self, resource_group):
        response = await self.client.linked_services.get(
            resource_group_name=resource_group.name,
            workspace_name="str",
            linked_service_name="str",
            api_version="2020-08-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_list_by_workspace(self, resource_group):
        response = self.client.linked_services.list_by_workspace(
            resource_group_name=resource_group.name,
            workspace_name="str",
            api_version="2020-08-01",
        )
        result = [r async for r in response]
        # please add some check logic here by yourself
        # ...
