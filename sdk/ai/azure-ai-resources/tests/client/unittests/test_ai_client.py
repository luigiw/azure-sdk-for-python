import unittest
from unittest.mock import Mock, patch

from azure.ai.resources.client import AIClient
from azure.identity import DefaultAzureCredential

class TestAIClient(unittest.TestCase):
    
    # @patch('azure.identity.DefaultAzureCredential')
    @patch('azure.ai.resources.client._ai_client.MLClient.workspaces')
    def test_ai_client_scope(self, mock_ws_operation):
        mock_ws = Mock()
        mock_ws.kind = "project"
        mock_ws.workspace_hub = "/subscriptions/xxx/resourceGroups/yyy/providers/Microsoft.MachineLearningServices/workspaces/my-hub"
        mock_ws_operation.get.return_value = mock_ws

        ai_client = AIClient(
            subscription_id="subscription_id",
            resource_group_name="resource_group_name",
            project_name="project_name",
            credential=DefaultAzureCredential(),
        )

        assert ai_client.ai_resource_name == "my-hub"

