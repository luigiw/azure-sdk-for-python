# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
import pytest
from azure.mgmt.applicationinsights.aio import ApplicationInsightsManagementClient

from devtools_testutils import AzureMgmtRecordedTestCase, RandomNameResourceGroupPreparer
from devtools_testutils.aio import recorded_by_proxy_async

AZURE_LOCATION = "eastus"


@pytest.mark.skip("you may need to update the auto-generated test case before run it")
class TestApplicationInsightsManagementWorkbooksOperationsAsync(AzureMgmtRecordedTestCase):
    def setup_method(self, method):
        self.client = self.create_mgmt_client(ApplicationInsightsManagementClient, is_async=True)

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_workbooks_list_by_subscription(self, resource_group):
        response = self.client.workbooks.list_by_subscription(
            category="str",
            api_version="2023-06-01",
        )
        result = [r async for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_workbooks_list_by_resource_group(self, resource_group):
        response = self.client.workbooks.list_by_resource_group(
            resource_group_name=resource_group.name,
            category="str",
            api_version="2023-06-01",
        )
        result = [r async for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_workbooks_get(self, resource_group):
        response = await self.client.workbooks.get(
            resource_group_name=resource_group.name,
            resource_name="str",
            api_version="2023-06-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_workbooks_delete(self, resource_group):
        response = await self.client.workbooks.delete(
            resource_group_name=resource_group.name,
            resource_name="str",
            api_version="2023-06-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_workbooks_create_or_update(self, resource_group):
        response = await self.client.workbooks.create_or_update(
            resource_group_name=resource_group.name,
            resource_name="str",
            workbook_properties={
                "location": "str",
                "category": "str",
                "description": "str",
                "displayName": "str",
                "etag": "str",
                "id": "str",
                "identity": {
                    "type": "str",
                    "principalId": "str",
                    "tenantId": "str",
                    "userAssignedIdentities": {"str": {"clientId": "str", "principalId": "str"}},
                },
                "kind": "str",
                "name": "str",
                "revision": "str",
                "serializedData": "str",
                "sourceId": "str",
                "storageUri": "str",
                "systemData": {
                    "createdAt": "2020-02-20 00:00:00",
                    "createdBy": "str",
                    "createdByType": "str",
                    "lastModifiedAt": "2020-02-20 00:00:00",
                    "lastModifiedBy": "str",
                    "lastModifiedByType": "str",
                },
                "tags": ["str"],
                "timeModified": "2020-02-20 00:00:00",
                "type": "str",
                "userId": "str",
                "version": "str",
            },
            api_version="2023-06-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_workbooks_update(self, resource_group):
        response = await self.client.workbooks.update(
            resource_group_name=resource_group.name,
            resource_name="str",
            api_version="2023-06-01",
        )

        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_workbooks_revisions_list(self, resource_group):
        response = self.client.workbooks.revisions_list(
            resource_group_name=resource_group.name,
            resource_name="str",
            api_version="2023-06-01",
        )
        result = [r async for r in response]
        # please add some check logic here by yourself
        # ...

    @RandomNameResourceGroupPreparer(location=AZURE_LOCATION)
    @recorded_by_proxy_async
    async def test_workbooks_revision_get(self, resource_group):
        response = await self.client.workbooks.revision_get(
            resource_group_name=resource_group.name,
            resource_name="str",
            revision_id="str",
            api_version="2023-06-01",
        )

        # please add some check logic here by yourself
        # ...
