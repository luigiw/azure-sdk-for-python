# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
# pylint:disable=protected-access
# pylint:disable=specify-parameter-names-in-call
# pylint:disable=too-many-lines
# pylint:disable=client-method-missing-tracing-decorator
import functools
import datetime
from copy import deepcopy
from typing import Any, Union, cast, Mapping, Optional, List, TYPE_CHECKING
from xml.etree.ElementTree import ElementTree

from azure.core import MatchConditions
from azure.core.paging import ItemPaged
from azure.core.exceptions import ResourceNotFoundError
from azure.core.pipeline import Pipeline
from azure.core.pipeline.policies import (
    HttpLoggingPolicy,
    DistributedTracingPolicy,
    ContentDecodePolicy,
    RequestIdPolicy,
    BearerTokenCredentialPolicy,
)
from azure.core.pipeline.transport import (  # pylint:disable=no-name-in-module,non-abstract-transport-import
    RequestsTransport,
)

from ._generated.models import (
    QueueDescriptionFeed,
    TopicDescriptionEntry,
    TopicDescriptionEntryContent,
    SubscriptionDescriptionEntryContent,
    QueueDescriptionEntry,
    QueueDescriptionEntryContent,
    SubscriptionDescriptionFeed,
    SubscriptionDescriptionEntry,
    RuleDescriptionEntry,
    RuleDescriptionEntryContent,
    RuleDescriptionFeed,
    NamespacePropertiesEntry,
    NamespacePropertiesEntryContent,
    CreateTopicBody,
    CreateTopicBodyContent,
    TopicDescriptionFeed,
    CreateSubscriptionBody,
    CreateSubscriptionBodyContent,
    CreateRuleBody,
    CreateRuleBodyContent,
    CreateQueueBody,
    CreateQueueBodyContent,
)
from ._utils import (
    extract_data_template,
    get_next_template,
    deserialize_rule_key_values,
    serialize_rule_key_values,
    extract_rule_data_template,
    create_properties_from_dict_if_needed,
    _normalize_entity_path_to_full_path_if_needed,
    _validate_entity_name_type,
    _validate_topic_and_subscription_types,
    _validate_topic_subscription_and_rule_types,
)
from ._xml_workaround_policy import ServiceBusXMLWorkaroundPolicy

from .._common.constants import (
    JWT_TOKEN_SCOPE,
    SUPPLEMENTARY_AUTHORIZATION_HEADER,
    DEAD_LETTER_SUPPLEMENTARY_AUTHORIZATION_HEADER,
)
from .._base_handler import (
    _parse_conn_str,
    ServiceBusSharedKeyCredential,
    ServiceBusSASTokenCredential,
)
from ._shared_key_policy import ServiceBusSharedKeyCredentialPolicy
from ._generated._configuration import ServiceBusManagementClientConfiguration
from ._generated import (
    ServiceBusManagementClient as ServiceBusManagementClientImpl,
)
from . import _constants as constants
from ._api_version import DEFAULT_VERSION, ApiVersion
from ._models import (
    AuthorizationRule,
    QueueRuntimeProperties,
    QueueProperties,
    TopicProperties,
    TopicRuntimeProperties,
    SubscriptionProperties,
    SubscriptionRuntimeProperties,
    RuleProperties,
    NamespaceProperties,
    TrueRuleFilter,
    CorrelationRuleFilter,
    SqlRuleFilter,
    SqlRuleAction,
)
from ._handle_response_error import _handle_response_error

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential


class ServiceBusAdministrationClient:  # pylint:disable=too-many-public-methods
    """Use this client to create, update, list, and delete resources of a ServiceBus namespace.

    :param str fully_qualified_namespace: The fully qualified host name for the Service Bus namespace.
    :param credential: To authenticate to manage the entities of the ServiceBus namespace.
    :type credential: TokenCredential
    :keyword api_version: The Service Bus API version to use for requests. Default value is the most
     recent service version that is compatible with the current SDK. Setting to an older version may result
     in reduced feature compatibility.
    :paramtype api_version: str or ApiVersion
    """

    def __init__(
        self,
        fully_qualified_namespace: str,
        credential: "TokenCredential",
        *,
        api_version: Union[str, ApiVersion] = DEFAULT_VERSION,
        **kwargs: Any
    ) -> None:
        self.fully_qualified_namespace = fully_qualified_namespace
        self._api_version = api_version
        self._credential = credential
        self._endpoint = "https://" + fully_qualified_namespace
        self._config = ServiceBusManagementClientConfiguration(
            self._endpoint, credential=self._credential, api_version=api_version, **kwargs
        )
        self._pipeline = self._build_pipeline()
        self._impl = ServiceBusManagementClientImpl(
            endpoint=fully_qualified_namespace,
            credential=self._credential,
            pipeline=self._pipeline,
            api_version=api_version,
            **kwargs
        )

    def __enter__(self) -> "ServiceBusAdministrationClient":
        self._impl.__enter__()
        return self

    def __exit__(self, *exc_details: Any) -> None:
        self._impl.__exit__(*exc_details)

    def _build_pipeline(self, **kwargs):
        transport = kwargs.get("transport")
        policies = kwargs.get("policies")
        credential_policy = (
            ServiceBusSharedKeyCredentialPolicy(self._endpoint, self._credential, "Authorization")
            if isinstance(self._credential, ServiceBusSharedKeyCredential)
            else BearerTokenCredentialPolicy(self._credential, JWT_TOKEN_SCOPE)
        )
        if policies is None:  # [] is a valid policy list
            policies = [
                RequestIdPolicy(**kwargs),
                self._config.headers_policy,
                self._config.user_agent_policy,
                self._config.proxy_policy,
                ContentDecodePolicy(**kwargs),
                ServiceBusXMLWorkaroundPolicy(),
                self._config.redirect_policy,
                self._config.retry_policy,
                credential_policy,
                self._config.logging_policy,
                DistributedTracingPolicy(**kwargs),
                HttpLoggingPolicy(**kwargs),
            ]
        if not transport:
            transport = RequestsTransport(**kwargs)
        return Pipeline(transport, policies)

    def _get_entity_element(self, entity_name: str, enrich: bool = False, **kwargs: Any) -> ElementTree:
        _validate_entity_name_type(entity_name)

        with _handle_response_error():
            element = cast(
                ElementTree,
                self._impl.entity.get(entity_name, enrich=enrich, **kwargs),
            )
        return element

    def _get_subscription_element(
        self, topic_name: str, subscription_name: str, enrich: bool = False, **kwargs: Any
    ) -> ElementTree:
        _validate_topic_and_subscription_types(topic_name, subscription_name)
        with _handle_response_error():
            element = cast(
                ElementTree,
                self._impl.subscription.get(topic_name, subscription_name, enrich=enrich, **kwargs),
            )
        return element

    def _get_rule_element(self, topic_name: str, subscription_name: str, rule_name: str, **kwargs: Any) -> ElementTree:
        _validate_topic_subscription_and_rule_types(topic_name, subscription_name, rule_name)

        with _handle_response_error():
            element = cast(
                ElementTree,
                self._impl.rule.get(topic_name, subscription_name, rule_name, enrich=False, **kwargs),
            )
        return element

    def _create_forward_to_header_tokens(self, entity, kwargs):
        """forward_to requires providing a bearer token in headers for the referenced entity.
        :param any entity: The entity to be created.
        :param any kwargs: The keyword arguments to be appended to the request.
        """
        kwargs["headers"] = kwargs.get("headers", {})

        def _populate_header_within_kwargs(uri, header):
            if not isinstance(self._credential, (ServiceBusSASTokenCredential, ServiceBusSharedKeyCredential)):
                uri = JWT_TOKEN_SCOPE
            token = self._credential.get_token(uri).token
            if not isinstance(
                self._credential,
                (ServiceBusSASTokenCredential, ServiceBusSharedKeyCredential),
            ):
                token = "Bearer {}".format(token)
            kwargs["headers"][header] = token

        if entity.forward_to:
            _populate_header_within_kwargs(entity.forward_to, SUPPLEMENTARY_AUTHORIZATION_HEADER)
        if entity.forward_dead_lettered_messages_to:
            _populate_header_within_kwargs(
                entity.forward_dead_lettered_messages_to,
                DEAD_LETTER_SUPPLEMENTARY_AUTHORIZATION_HEADER,
            )

    @classmethod
    def from_connection_string(
        cls, conn_str: str, *, api_version: Union[str, ApiVersion] = DEFAULT_VERSION, **kwargs: Any
    ) -> "ServiceBusAdministrationClient":
        """Create a client from connection string.

        :param str conn_str: The connection string of the Service Bus Namespace.
        :keyword api_version: The Service Bus API version to use for requests. Default value is the most
         recent service version that is compatible with the current SDK. Setting to an older version may result
         in reduced feature compatibility.
        :paramtype api_version: str or ApiVersion
        :returns: Returns a ServiceBusAdministrationClient.
        :rtype: ~azure.servicebus.management.ServiceBusAdministrationClient
        """
        (endpoint, shared_access_key_name, shared_access_key, _, token, token_expiry, emulator) = _parse_conn_str(
            conn_str
        )
        kwargs["use_tls"] = not emulator
        credential: Union[ServiceBusSharedKeyCredential, ServiceBusSASTokenCredential]
        if token and token_expiry:
            credential = ServiceBusSASTokenCredential(token, token_expiry)
        elif shared_access_key_name and shared_access_key:
            credential = ServiceBusSharedKeyCredential(shared_access_key_name, shared_access_key)  # type: ignore
        if "//" in endpoint:
            endpoint = endpoint[endpoint.index("//") + 2 :]
        return cls(endpoint, credential, api_version=api_version, **kwargs)

    def get_queue(self, queue_name: str, **kwargs: Any) -> QueueProperties:
        """Get the properties of a queue.

        :param str queue_name: The name of the queue.
        :return: The properties of the queue.
        :rtype: ~azure.servicebus.management.QueueProperties
        """
        entry_ele = self._get_entity_element(queue_name, **kwargs)
        entry = QueueDescriptionEntry.deserialize(entry_ele)
        if not entry.content:
            raise ResourceNotFoundError("Queue '{}' does not exist".format(queue_name))
        queue_description = QueueProperties._from_internal_entity(queue_name, entry.content.queue_description)
        return queue_description

    def get_queue_runtime_properties(self, queue_name: str, **kwargs: Any) -> QueueRuntimeProperties:
        """Get the runtime information of a queue.

        :param str queue_name: The name of the queue.
        :return: The runtime information of the queue.
        :rtype: ~azure.servicebus.management.QueueRuntimeProperties
        """
        entry_ele = self._get_entity_element(queue_name, **kwargs)
        entry = QueueDescriptionEntry.deserialize(entry_ele)
        if not entry.content:
            raise ResourceNotFoundError("Queue {} does not exist".format(queue_name))
        runtime_properties = QueueRuntimeProperties._from_internal_entity(queue_name, entry.content.queue_description)
        return runtime_properties

    def create_queue(  # pylint: disable=too-many-locals
        self,
        queue_name: str,
        *,
        authorization_rules: Optional[List[AuthorizationRule]] = None,
        auto_delete_on_idle: Optional[Union[datetime.timedelta, str]] = None,
        dead_lettering_on_message_expiration: Optional[bool] = None,
        default_message_time_to_live: Optional[Union[datetime.timedelta, str]] = None,
        duplicate_detection_history_time_window: Optional[Union[datetime.timedelta, str]] = None,
        enable_batched_operations: Optional[bool] = None,
        enable_express: Optional[bool] = None,
        enable_partitioning: Optional[bool] = None,
        lock_duration: Optional[Union[datetime.timedelta, str]] = None,
        max_delivery_count: Optional[int] = None,
        max_size_in_megabytes: Optional[int] = None,
        requires_duplicate_detection: Optional[bool] = None,
        requires_session: Optional[bool] = None,
        forward_to: Optional[str] = None,
        user_metadata: Optional[str] = None,
        forward_dead_lettered_messages_to: Optional[str] = None,
        max_message_size_in_kilobytes: Optional[int] = None,
        **kwargs: Any
    ) -> QueueProperties:
        """Create a queue.

        :param queue_name: Name of the queue.
        :type queue_name: str
        :keyword authorization_rules: Authorization rules for resource.
        :paramtype authorization_rules: list[~azure.servicebus.management.AuthorizationRule] or None
        :keyword auto_delete_on_idle: ISO 8601 timeSpan idle interval after which the queue is
         automatically deleted. The minimum duration is 5 minutes.
         Input value of either type ~datetime.timedelta or string in ISO 8601 duration format like "PT300S" is accepted.
        :paramtype auto_delete_on_idle: ~datetime.timedelta or str or one
        :keyword dead_lettering_on_message_expiration: A value that indicates whether this queue has dead
         letter support when a message expires.
        :paramtype dead_lettering_on_message_expiration: bool
        :keyword default_message_time_to_live: ISO 8601 default message timespan to live value. This is
         the duration after which the message expires, starting from when the message is sent to Service
         Bus. This is the default value used when TimeToLive is not set on a message itself.
         Input value of either type ~datetime.timedelta or string in ISO 8601 duration format like "PT300S" is accepted.
        :paramtype default_message_time_to_live: ~datetime.timedelta or str or None
        :keyword duplicate_detection_history_time_window: ISO 8601 timeSpan structure that defines the
         duration of the duplicate detection history. The default value is 10 minutes.
         Input value of either type ~datetime.timedelta or string in ISO 8601 duration format like "PT300S" is accepted.
        :paramtype duplicate_detection_history_time_window: ~datetime.timedelta or str or None
        :keyword enable_batched_operations: Value that indicates whether server-side batched operations
         are enabled.
        :paramtype enable_batched_operations: bool
        :keyword enable_express: A value that indicates whether Express Entities are enabled. An express
         queue holds a message in memory temporarily before writing it to persistent storage.
        :paramtype enable_express: bool
        :keyword enable_partitioning: A value that indicates whether the queue is to be partitioned
         across multiple message brokers.
        :paramtype enable_partitioning: bool
        :keyword lock_duration: ISO 8601 timespan duration of a peek-lock; that is, the amount of time
         that the message is locked for other receivers. The maximum value for LockDuration is 5
         minutes; the default value is 1 minute.
         Input value of either type ~datetime.timedelta or string in ISO 8601 duration format like "PT300S" is accepted.
        :paramtype lock_duration: ~datetime.timedelta or str or None
        :keyword max_delivery_count: The maximum delivery count. A message is automatically deadlettered
         after this number of deliveries. Default value is 10.
        :paramtype max_delivery_count: int
        :keyword max_size_in_megabytes: The maximum size of the queue in megabytes, which is the size of
         memory allocated for the queue.
        :paramtype max_size_in_megabytes: int
        :keyword requires_duplicate_detection: A value indicating if this queue requires duplicate
         detection.
        :paramtype requires_duplicate_detection: bool
        :keyword requires_session: A value that indicates whether the queue supports the concept of
         sessions.
        :paramtype requires_session: bool
        :keyword forward_to: The name of the recipient entity to which all the messages sent to the queue
         are forwarded to.
        :paramtype forward_to: str
        :keyword user_metadata: Custom metdata that user can associate with the description. Max length
         is 1024 chars.
        :paramtype user_metadata: str
        :keyword forward_dead_lettered_messages_to: The name of the recipient entity to which all the
         dead-lettered messages of this subscription are forwarded to.
        :paramtype forward_dead_lettered_messages_to: str
        :keyword max_message_size_in_kilobytes: The maximum size in kilobytes of message payload that
         can be accepted by the queue. This feature is only available when using a Premium namespace
         and Service Bus API version "2021-05" or higher.
         The minimum allowed value is 1024 while the maximum allowed value is 102400. Default value is 1024.
        :paramtype max_message_size_in_kilobytes: int
        :returns: Returns properties of queue resource.
        :rtype: ~azure.servicebus.management.QueueProperties
        """
        forward_to = _normalize_entity_path_to_full_path_if_needed(forward_to, self.fully_qualified_namespace)
        forward_dead_lettered_messages_to = _normalize_entity_path_to_full_path_if_needed(
            forward_dead_lettered_messages_to,
            self.fully_qualified_namespace,
        )
        queue = QueueProperties(
            queue_name,
            authorization_rules=authorization_rules,
            auto_delete_on_idle=auto_delete_on_idle,
            dead_lettering_on_message_expiration=dead_lettering_on_message_expiration,
            default_message_time_to_live=default_message_time_to_live,
            duplicate_detection_history_time_window=duplicate_detection_history_time_window,
            availability_status=None,
            enable_batched_operations=enable_batched_operations,
            enable_express=enable_express,
            enable_partitioning=enable_partitioning,
            lock_duration=lock_duration,
            max_delivery_count=max_delivery_count,
            max_size_in_megabytes=max_size_in_megabytes,
            requires_duplicate_detection=requires_duplicate_detection,
            requires_session=requires_session,
            status=kwargs.pop("status", None),
            forward_to=forward_to,
            forward_dead_lettered_messages_to=forward_dead_lettered_messages_to,
            user_metadata=user_metadata,
            max_message_size_in_kilobytes=max_message_size_in_kilobytes,
        )
        to_create = queue._to_internal_entity(self.fully_qualified_namespace)
        create_entity_body = CreateQueueBody(
            content=CreateQueueBodyContent(
                queue_description=to_create,  # type: ignore
            )
        )
        request_body = create_entity_body.serialize(is_xml=True)
        self._create_forward_to_header_tokens(to_create, kwargs)
        with _handle_response_error():
            entry_ele = cast(
                ElementTree,
                self._impl.entity.put(queue_name, request_body, **kwargs),  # type: ignore
            )

        entry = QueueDescriptionEntry.deserialize(entry_ele)
        # Need to cast from Optional[QueueDescriptionEntryContent] to QueueDescriptionEntryContent
        # since we know for certain that `entry.content` will not be None here.
        entry.content = cast(QueueDescriptionEntryContent, entry.content)
        result = QueueProperties._from_internal_entity(queue_name, entry.content.queue_description)
        return result

    def update_queue(self, queue: Union[QueueProperties, Mapping[str, Any]], **kwargs: Any) -> None:
        """Update a queue.

        Before calling this method, you should use `get_queue`, `create_queue` or `list_queues` to get a
        `QueueProperties` instance, then update the properties. Only a portion of properties can
        be updated. Refer to https://learn.microsoft.com/rest/api/servicebus/update-queue.
        You could also pass keyword arguments for updating properties in the form of
        `<property_name>=<property_value>` which will override whatever was specified in
        the `QueueProperties` instance. Refer to ~azure.servicebus.management.QueueProperties for names of properties.

        :param queue: The queue that is returned from `get_queue`, `create_queue` or `list_queues` and
         has the updated properties.
        :type queue: ~azure.servicebus.management.QueueProperties
        :rtype: None
        """
        # we should not mutate the input, making a copy first for update
        queue = deepcopy(create_properties_from_dict_if_needed(queue, QueueProperties))
        to_update = queue._to_internal_entity(self.fully_qualified_namespace, kwargs)

        create_entity_body = CreateQueueBody(
            content=CreateQueueBodyContent(
                queue_description=to_update,
            )
        )
        request_body = create_entity_body.serialize(is_xml=True)
        self._create_forward_to_header_tokens(to_update, kwargs)
        with _handle_response_error():
            self._impl.entity.put(
                queue.name, request_body, match_condition=MatchConditions.IfPresent, **kwargs  # type: ignore
            )

    def delete_queue(self, queue_name: str, **kwargs: Any) -> None:
        """Delete a queue.

        :param str queue_name: The name of the queue or
         a `QueueProperties` with name.
        :rtype: None
        """
        _validate_entity_name_type(queue_name)

        if not queue_name:
            raise ValueError("queue_name must not be None or empty")
        with _handle_response_error():
            self._impl.entity.delete(queue_name, **kwargs)  # type: ignore

    def list_queues(self, **kwargs: Any) -> ItemPaged[QueueProperties]:
        """List the queues of a ServiceBus namespace.

        :returns: An iterable (auto-paging) response of QueueProperties.
        :rtype: ~azure.core.paging.ItemPaged[~azure.servicebus.management.QueueProperties]
        """

        def entry_to_qd(entry):
            qd = QueueProperties._from_internal_entity(entry.title, entry.content.queue_description)
            return qd

        extract_data = functools.partial(extract_data_template, QueueDescriptionFeed, entry_to_qd)
        get_next = functools.partial(
            get_next_template, functools.partial(self._impl.list_entities, constants.ENTITY_TYPE_QUEUES), **kwargs
        )
        return ItemPaged(get_next, extract_data)

    def list_queues_runtime_properties(self, **kwargs: Any) -> ItemPaged[QueueRuntimeProperties]:
        """List the runtime information of the queues in a ServiceBus namespace.

        :returns: An iterable (auto-paging) response of QueueRuntimeProperties.
        :rtype: ~azure.core.paging.ItemPaged[~azure.servicebus.management.QueueRuntimeProperties]
        """

        def entry_to_qr(entry):
            qd = QueueRuntimeProperties._from_internal_entity(entry.title, entry.content.queue_description)
            return qd

        extract_data = functools.partial(extract_data_template, QueueDescriptionFeed, entry_to_qr)
        get_next = functools.partial(
            get_next_template, functools.partial(self._impl.list_entities, constants.ENTITY_TYPE_QUEUES), **kwargs
        )
        return ItemPaged(get_next, extract_data)

    def get_topic(self, topic_name: str, **kwargs: Any) -> TopicProperties:
        """Get the properties of a topic.

        :param str topic_name: The name of the topic.
        :return: The properties of the topic.
        :rtype: ~azure.servicebus.management.TopicProperties
        """
        entry_ele = self._get_entity_element(topic_name, **kwargs)
        entry = TopicDescriptionEntry.deserialize(entry_ele)
        if not entry.content:
            raise ResourceNotFoundError("Topic '{}' does not exist".format(topic_name))
        topic_description = TopicProperties._from_internal_entity(topic_name, entry.content.topic_description)
        return topic_description

    def get_topic_runtime_properties(self, topic_name: str, **kwargs: Any) -> TopicRuntimeProperties:
        """Get a the runtime information of a topic.

        :param str topic_name: The name of the topic.
        :return: The runtime info of the topic.
        :rtype: ~azure.servicebus.management.TopicRuntimeProperties
        """
        entry_ele = self._get_entity_element(topic_name, **kwargs)
        entry = TopicDescriptionEntry.deserialize(entry_ele)
        if not entry.content:
            raise ResourceNotFoundError("Topic {} does not exist".format(topic_name))
        topic_description = TopicRuntimeProperties._from_internal_entity(topic_name, entry.content.topic_description)
        return topic_description

    def create_topic(
        self,
        topic_name: str,
        *,
        default_message_time_to_live: Optional[Union[datetime.timedelta, str]] = None,
        max_size_in_megabytes: Optional[int] = None,
        requires_duplicate_detection: Optional[bool] = None,
        duplicate_detection_history_time_window: Optional[Union[datetime.timedelta, str]] = None,
        enable_batched_operations: Optional[bool] = None,
        size_in_bytes: Optional[int] = None,
        filtering_messages_before_publishing: Optional[bool] = None,
        authorization_rules: Optional[List[AuthorizationRule]] = None,
        support_ordering: Optional[bool] = None,
        auto_delete_on_idle: Optional[Union[datetime.timedelta, str]] = None,
        enable_partitioning: Optional[bool] = None,
        enable_express: Optional[bool] = None,
        user_metadata: Optional[str] = None,
        max_message_size_in_kilobytes: Optional[int] = None,
        **kwargs: Any
    ) -> TopicProperties:
        """Create a topic.

        :param topic_name: Name of the topic.
        :type topic_name: str
        :keyword default_message_time_to_live: ISO 8601 default message timespan to live value. This is
         the duration after which the message expires, starting from when the message is sent to Service
         Bus. This is the default value used when TimeToLive is not set on a message itself.
         Input value of either type ~datetime.timedelta or string in ISO 8601 duration format like "PT300S" is accepted.
        :paramtype default_message_time_to_live: Union[~datetime.timedelta, str]
        :keyword max_size_in_megabytes: The maximum size of the topic in megabytes, which is the size of
         memory allocated for the topic.
        :paramtype max_size_in_megabytes: int
        :keyword requires_duplicate_detection: A value indicating if this topic requires duplicate
         detection.
        :paramtype requires_duplicate_detection: bool
        :keyword duplicate_detection_history_time_window: ISO 8601 timeSpan structure that defines the
         duration of the duplicate detection history. The default value is 10 minutes.
         Input value of either type ~datetime.timedelta or string in ISO 8601 duration format like "PT300S" is accepted.
        :paramtype duplicate_detection_history_time_window: Union[~datetime.timedelta, str]
        :keyword enable_batched_operations: Value that indicates whether server-side batched operations
         are enabled.
        :paramtype enable_batched_operations: bool
        :keyword size_in_bytes: The size of the topic, in bytes.
        :paramtype size_in_bytes: int
        :keyword filtering_messages_before_publishing: Filter messages before publishing.
        :paramtype filtering_messages_before_publishing: bool
        :keyword authorization_rules: Authorization rules for resource.
        :paramtype authorization_rules:
         list[~azure.servicebus.management.AuthorizationRule]
        :keyword support_ordering: A value that indicates whether the topic supports ordering.
        :paramtype support_ordering: bool
        :keyword auto_delete_on_idle: ISO 8601 timeSpan idle interval after which the topic is
         automatically deleted. The minimum duration is 5 minutes.
         Input value of either type ~datetime.timedelta or string in ISO 8601 duration format like "PT300S" is accepted.
        :paramtype auto_delete_on_idle: Union[~datetime.timedelta, str]
        :keyword enable_partitioning: A value that indicates whether the topic is to be partitioned
         across multiple message brokers.
        :paramtype enable_partitioning: bool
        :keyword enable_express: A value that indicates whether Express Entities are enabled. An express
         queue holds a message in memory temporarily before writing it to persistent storage.
        :paramtype enable_express: bool
        :keyword user_metadata: Metadata associated with the topic.
        :paramtype user_metadata: str
        :keyword max_message_size_in_kilobytes: The maximum size in kilobytes of message payload that
         can be accepted by the queue. This feature is only available when using a Premium namespace
         and Service Bus API version "2021-05" or higher.
         The minimum allowed value is 1024 while the maximum allowed value is 102400. Default value is 1024.
        :paramtype max_message_size_in_kilobytes: int
        :return: Returns properties of a topic resource.
        :rtype: ~azure.servicebus.management.TopicProperties
        """
        topic = TopicProperties(
            topic_name,
            default_message_time_to_live=default_message_time_to_live,
            max_size_in_megabytes=max_size_in_megabytes,
            requires_duplicate_detection=requires_duplicate_detection,
            # TODO: ask why default of 10 mins isn't followed below,
            duplicate_detection_history_time_window=duplicate_detection_history_time_window,
            enable_batched_operations=enable_batched_operations,
            size_in_bytes=size_in_bytes,
            authorization_rules=authorization_rules,
            filtering_messages_before_publishing=filtering_messages_before_publishing,
            status=kwargs.pop("status", None),
            support_ordering=support_ordering,
            auto_delete_on_idle=auto_delete_on_idle,
            enable_partitioning=enable_partitioning,
            availability_status=None,
            enable_express=enable_express,
            user_metadata=user_metadata,
            max_message_size_in_kilobytes=max_message_size_in_kilobytes,
            **kwargs
        )
        to_create = topic._to_internal_entity()

        create_entity_body = CreateTopicBody(
            content=CreateTopicBodyContent(
                topic_description=to_create,  # type: ignore
            )
        )
        request_body = create_entity_body.serialize(is_xml=True)
        with _handle_response_error():
            entry_ele = cast(
                ElementTree,
                self._impl.entity.put(topic_name, request_body, **kwargs),  # type: ignore
            )
        entry = TopicDescriptionEntry.deserialize(entry_ele)
        # Need to cast from Optional[TopicDescriptionEntryContent] to TopicDescriptionEntryContent
        # since we know for certain that `entry.content` will not be None here.
        entry.content = cast(TopicDescriptionEntryContent, entry.content)
        result = TopicProperties._from_internal_entity(topic_name, entry.content.topic_description)
        return result

    def update_topic(self, topic: Union[TopicProperties, Mapping[str, Any]], **kwargs: Any) -> None:
        """Update a topic.

        Before calling this method, you should use `get_topic`, `create_topic` or `list_topics` to get a
        `TopicProperties` instance, then update the properties. Only a portion of properties can be updated.
        Refer to https://learn.microsoft.com/rest/api/servicebus/update-topic.
        You could also pass keyword arguments for updating properties in the form of
        `<property_name>=<property_value>` which will override whatever was specified in
        the `TopicProperties` instance. Refer to ~azure.servicebus.management.TopicProperties for names of properties.

        :param topic: The topic that is returned from `get_topic`, `create_topic`, or `list_topics`
         and has the updated properties.
        :type topic: ~azure.servicebus.management.TopicProperties
        :rtype: None
        """
        # we should not mutate the input, making a copy first for update
        topic = deepcopy(create_properties_from_dict_if_needed(topic, TopicProperties))
        to_update = topic._to_internal_entity(kwargs)

        create_entity_body = CreateTopicBody(
            content=CreateTopicBodyContent(
                topic_description=to_update,
            )
        )
        request_body = create_entity_body.serialize(is_xml=True)
        with _handle_response_error():
            self._impl.entity.put(
                topic.name, request_body, match_condition=MatchConditions.IfPresent, **kwargs  # type: ignore
            )

    def delete_topic(self, topic_name: str, **kwargs: Any) -> None:
        """Delete a topic.

        :param str topic_name: The topic to be deleted.
        :rtype: None
        """
        _validate_entity_name_type(topic_name)

        self._impl.entity.delete(topic_name, **kwargs)  # type: ignore

    def list_topics(self, **kwargs: Any) -> ItemPaged[TopicProperties]:
        """List the topics of a ServiceBus namespace.

        :returns: An iterable (auto-paging) response of TopicProperties.
        :rtype: ~azure.core.paging.ItemPaged[~azure.servicebus.management.TopicProperties]
        """

        def entry_to_topic(entry):
            topic = TopicProperties._from_internal_entity(entry.title, entry.content.topic_description)
            return topic

        extract_data = functools.partial(extract_data_template, TopicDescriptionFeed, entry_to_topic)
        get_next = functools.partial(
            get_next_template, functools.partial(self._impl.list_entities, constants.ENTITY_TYPE_TOPICS), **kwargs
        )
        return ItemPaged(get_next, extract_data)

    def list_topics_runtime_properties(self, **kwargs: Any) -> ItemPaged[TopicRuntimeProperties]:
        """List the topics runtime information of a ServiceBus namespace.

        :returns: An iterable (auto-paging) response of TopicRuntimeProperties.
        :rtype: ~azure.core.paging.ItemPaged[~azure.servicebus.management.TopicRuntimeProperties]
        """

        def entry_to_topic(entry):
            topic = TopicRuntimeProperties._from_internal_entity(entry.title, entry.content.topic_description)
            return topic

        extract_data = functools.partial(extract_data_template, TopicDescriptionFeed, entry_to_topic)
        get_next = functools.partial(
            get_next_template, functools.partial(self._impl.list_entities, constants.ENTITY_TYPE_TOPICS), **kwargs
        )
        return ItemPaged(get_next, extract_data)

    def get_subscription(self, topic_name: str, subscription_name: str, **kwargs: Any) -> SubscriptionProperties:
        """Get the properties of a topic subscription.

        :param str topic_name: The topic that owns the subscription.
        :param str subscription_name: name of the subscription.
        :return: An instance of SubscriptionProperties
        :rtype: ~azure.servicebus.management.SubscriptionProperties
        """
        entry_ele = self._get_subscription_element(topic_name, subscription_name, **kwargs)
        entry = SubscriptionDescriptionEntry.deserialize(entry_ele)
        if not entry.content:
            raise ResourceNotFoundError(
                "Subscription('Topic: {}, Subscription: {}') does not exist".format(subscription_name, topic_name)
            )
        subscription = SubscriptionProperties._from_internal_entity(
            subscription_name, entry.content.subscription_description
        )
        return subscription

    def get_subscription_runtime_properties(
        self, topic_name: str, subscription_name: str, **kwargs: Any
    ) -> SubscriptionRuntimeProperties:
        """Get a topic subscription runtime info.

        :param str topic_name: The topic that owns the subscription.
        :param str subscription_name: name of the subscription.
        :return: An instance of SubscriptionRuntimeProperties
        :rtype: ~azure.servicebus.management.SubscriptionRuntimeProperties
        """
        entry_ele = self._get_subscription_element(topic_name, subscription_name, **kwargs)
        entry = SubscriptionDescriptionEntry.deserialize(entry_ele)
        if not entry.content:
            raise ResourceNotFoundError(
                "Subscription('Topic: {}, Subscription: {}') does not exist".format(subscription_name, topic_name)
            )
        subscription = SubscriptionRuntimeProperties._from_internal_entity(
            subscription_name, entry.content.subscription_description
        )
        return subscription

    def create_subscription(
        self,
        topic_name: str,
        subscription_name: str,
        *,
        lock_duration: Optional[Union[datetime.timedelta, str]] = None,
        requires_session: Optional[bool] = None,
        default_message_time_to_live: Optional[Union[datetime.timedelta, str]] = None,
        dead_lettering_on_message_expiration: Optional[bool] = None,
        dead_lettering_on_filter_evaluation_exceptions: Optional[bool] = None,
        max_delivery_count: Optional[int] = None,
        enable_batched_operations: Optional[bool] = None,
        forward_to: Optional[str] = None,
        user_metadata: Optional[str] = None,
        forward_dead_lettered_messages_to: Optional[str] = None,
        auto_delete_on_idle: Optional[Union[datetime.timedelta, str]] = None,
        **kwargs: Any
    ) -> SubscriptionProperties:
        """Create a topic subscription.

        :param str topic_name: The topic that will own the
         to-be-created subscription.
        :param subscription_name: Name of the subscription.
        :type subscription_name: str
        :keyword lock_duration: ISO 8601 timespan duration of a peek-lock; that is, the amount of time
         that the message is locked for other receivers. The maximum value for LockDuration is 5
         minutes; the default value is 1 minute.
         Input value of either type ~datetime.timedelta or string in ISO 8601 duration format like "PT300S" is accepted.
        :paramtype lock_duration: Union[~datetime.timedelta, str]
        :keyword requires_session: A value that indicates whether the queue supports the concept of
         sessions.
        :paramtype requires_session: bool
        :keyword default_message_time_to_live: ISO 8601 default message timespan to live value. This is
         the duration after which the message expires, starting from when the message is sent to Service
         Bus. This is the default value used when TimeToLive is not set on a message itself.
         Input value of either type ~datetime.timedelta or string in ISO 8601 duration format like "PT300S" is accepted.
        :paramtype default_message_time_to_live: Union[~datetime.timedelta, str]
        :keyword dead_lettering_on_message_expiration: A value that indicates whether this subscription
         has dead letter support when a message expires.
        :paramtype dead_lettering_on_message_expiration: bool
        :keyword dead_lettering_on_filter_evaluation_exceptions: A value that indicates whether this
         subscription has dead letter support when a message expires.
        :paramtype dead_lettering_on_filter_evaluation_exceptions: bool
        :keyword max_delivery_count: The maximum delivery count. A message is automatically deadlettered
         after this number of deliveries. Default value is 10.
        :paramtype max_delivery_count: int
        :keyword enable_batched_operations: Value that indicates whether server-side batched operations
         are enabled.
        :paramtype enable_batched_operations: bool
        :keyword forward_to: The name of the recipient entity to which all the messages sent to the
         subscription are forwarded to.
        :paramtype forward_to: str
        :keyword user_metadata: Metadata associated with the subscription. Maximum number of characters
         is 1024.
        :paramtype user_metadata: str
        :keyword forward_dead_lettered_messages_to: The name of the recipient entity to which all the
         messages sent to the subscription are forwarded to.
        :paramtype forward_dead_lettered_messages_to: str
        :keyword auto_delete_on_idle: ISO 8601 timeSpan idle interval after which the subscription is
         automatically deleted. The minimum duration is 5 minutes.
         Input value of either type ~datetime.timedelta or string in ISO 8601 duration format like "PT300S" is accepted.
        :paramtype auto_delete_on_idle: Union[~datetime.timedelta, str]
        :return: Return properties of a topic subscription resource.
        :rtype:  ~azure.servicebus.management.SubscriptionProperties
        """
        _validate_entity_name_type(topic_name, display_name="topic_name")
        forward_to = _normalize_entity_path_to_full_path_if_needed(forward_to, self.fully_qualified_namespace)
        forward_dead_lettered_messages_to = _normalize_entity_path_to_full_path_if_needed(
            forward_dead_lettered_messages_to,
            self.fully_qualified_namespace,
        )

        subscription = SubscriptionProperties(
            subscription_name,
            lock_duration=lock_duration,
            requires_session=requires_session,
            default_message_time_to_live=default_message_time_to_live,
            dead_lettering_on_message_expiration=dead_lettering_on_message_expiration,
            dead_lettering_on_filter_evaluation_exceptions=dead_lettering_on_filter_evaluation_exceptions,
            max_delivery_count=max_delivery_count,
            enable_batched_operations=enable_batched_operations,
            status=kwargs.pop("status", None),
            forward_to=forward_to,
            user_metadata=user_metadata,
            forward_dead_lettered_messages_to=forward_dead_lettered_messages_to,
            auto_delete_on_idle=auto_delete_on_idle,
            availability_status=None,
        )
        to_create = subscription._to_internal_entity(self.fully_qualified_namespace)  # type: ignore  # pylint:disable=protected-access

        create_entity_body = CreateSubscriptionBody(
            content=CreateSubscriptionBodyContent(
                subscription_description=to_create,  # type: ignore
            )
        )
        request_body = create_entity_body.serialize(is_xml=True)
        self._create_forward_to_header_tokens(to_create, kwargs)
        with _handle_response_error():
            entry_ele = cast(
                ElementTree,
                self._impl.subscription.put(topic_name, subscription_name, request_body, **kwargs),  # type: ignore
            )

        entry = SubscriptionDescriptionEntry.deserialize(entry_ele)
        # Need to cast from Optional[SubscriptionDescriptionEntryContent] to SubscriptionDescriptionEntryContent
        # since we know for certain that `entry.content` will not be None here.
        entry.content = cast(SubscriptionDescriptionEntryContent, entry.content)
        result = SubscriptionProperties._from_internal_entity(subscription_name, entry.content.subscription_description)
        return result

    def update_subscription(
        self, topic_name: str, subscription: Union[SubscriptionProperties, Mapping[str, Any]], **kwargs: Any
    ) -> None:
        """Update a subscription.

        Before calling this method, you should use `get_subscription`, `update_subscription` or `list_subscription`
        to get a `SubscriptionProperties` instance, then update the properties.
        You could also pass keyword arguments for updating properties in the form of
        `<property_name>=<property_value>` which will override whatever was specified in
        the `SubscriptionProperties` instance.
        Refer to ~azure.servicebus.management.SubscriptionProperties for names of properties.

        :param str topic_name: The topic that owns the subscription.
        :param ~azure.servicebus.management.SubscriptionProperties subscription: The subscription that is returned
         from `get_subscription`, `update_subscription` or `list_subscription` and has the updated properties.
        :rtype: None
        """
        _validate_entity_name_type(topic_name, display_name="topic_name")
        # we should not mutate the input, making a copy first for update
        subscription = deepcopy(
            create_properties_from_dict_if_needed(subscription, SubscriptionProperties)  # type: ignore
        )
        to_update = subscription._to_internal_entity(self.fully_qualified_namespace, kwargs)

        create_entity_body = CreateSubscriptionBody(
            content=CreateSubscriptionBodyContent(
                subscription_description=to_update,
            )
        )
        request_body = create_entity_body.serialize(is_xml=True)
        self._create_forward_to_header_tokens(to_update, kwargs)
        with _handle_response_error():
            self._impl.subscription.put(
                topic_name, subscription.name, request_body, match_condition=MatchConditions.IfPresent, **kwargs
            )

    def delete_subscription(self, topic_name: str, subscription_name: str, **kwargs: Any) -> None:
        """Delete a topic subscription.

        :param str topic_name: The topic that owns the subscription.
        :param str subscription_name: The subscription to
         be deleted.
        :rtype: None
        """
        _validate_topic_and_subscription_types(topic_name, subscription_name)

        self._impl.subscription.delete(topic_name, subscription_name, **kwargs)  # type: ignore

    def list_subscriptions(self, topic_name: str, **kwargs: Any) -> ItemPaged[SubscriptionProperties]:
        """List the subscriptions of a ServiceBus Topic.

        :param str topic_name: The topic that owns the subscription.
        :returns: An iterable (auto-paging) response of SubscriptionProperties.
        :rtype: ~azure.core.paging.ItemPaged[~azure.servicebus.management.SubscriptionProperties]
        """
        _validate_entity_name_type(topic_name)

        def entry_to_subscription(entry):
            subscription = SubscriptionProperties._from_internal_entity(
                entry.title, entry.content.subscription_description
            )
            return subscription

        extract_data = functools.partial(extract_data_template, SubscriptionDescriptionFeed, entry_to_subscription)
        get_next = functools.partial(
            get_next_template, functools.partial(self._impl.list_subscriptions, topic_name), **kwargs
        )
        return ItemPaged(get_next, extract_data)

    def list_subscriptions_runtime_properties(
        self, topic_name: str, **kwargs: Any
    ) -> ItemPaged[SubscriptionRuntimeProperties]:
        """List the subscriptions runtime information of a ServiceBus Topic.

        :param str topic_name: The topic that owns the subscription.
        :returns: An iterable (auto-paging) response of SubscriptionRuntimeProperties.
        :rtype: ~azure.core.paging.ItemPaged[~azure.servicebus.management.SubscriptionRuntimeProperties]
        """
        _validate_entity_name_type(topic_name)

        def entry_to_subscription(entry):
            subscription = SubscriptionRuntimeProperties._from_internal_entity(
                entry.title, entry.content.subscription_description
            )
            return subscription

        extract_data = functools.partial(extract_data_template, SubscriptionDescriptionFeed, entry_to_subscription)
        get_next = functools.partial(
            get_next_template, functools.partial(self._impl.list_subscriptions, topic_name), **kwargs
        )
        return ItemPaged(get_next, extract_data)

    def get_rule(self, topic_name: str, subscription_name: str, rule_name: str, **kwargs: Any) -> RuleProperties:
        """Get the properties of a topic subscription rule.

        :param str topic_name: The topic that owns the subscription.
        :param str subscription_name: The subscription that
         owns the rule.
        :param str rule_name: Name of the rule.
        :return: The properties of the specified rule.
        :rtype: ~azure.servicebus.management.RuleProperties
        """
        entry_ele = self._get_rule_element(topic_name, subscription_name, rule_name, **kwargs)
        entry = RuleDescriptionEntry.deserialize(entry_ele)
        if not entry.content:
            raise ResourceNotFoundError(
                "Rule('Topic: {}, Subscription: {}, Rule {}') does not exist".format(
                    subscription_name, topic_name, rule_name
                )
            )
        rule_description = RuleProperties._from_internal_entity(rule_name, entry.content.rule_description)
        deserialize_rule_key_values(entry_ele, rule_description)  # to remove after #3535 is released.
        return rule_description

    def create_rule(
        self,
        topic_name: str,
        subscription_name: str,
        rule_name: str,
        *,
        filter: Union[CorrelationRuleFilter, SqlRuleFilter] = TrueRuleFilter(),  # pylint: disable=redefined-builtin
        action: Optional[SqlRuleAction] = None,
        **kwargs: Any
    ) -> RuleProperties:
        """Create a rule for a topic subscription.

        :param str topic_name: The topic that will own the
         to-be-created subscription rule.
        :param str subscription_name: The subscription that
         will own the to-be-created rule.
        :param rule_name: Name of the rule.
        :type rule_name: str
        :keyword filter: The filter of the rule. The default value is ~azure.servicebus.management.TrueRuleFilter
        :paramtype filter: Union[~azure.servicebus.management.CorrelationRuleFilter,
         ~azure.servicebus.management.SqlRuleFilter]
        :keyword action: The action of the rule.
        :paramtype action: Optional[~azure.servicebus.management.SqlRuleAction]
        :return: Rule properties for a topic subscription.
        :rtype: ~azure.servicebus.management.RuleProperties
        """
        _validate_topic_and_subscription_types(topic_name, subscription_name)

        rule = RuleProperties(
            rule_name,
            filter=filter,
            action=action,
            created_at_utc=None,
        )
        to_create = rule._to_internal_entity()

        create_entity_body = CreateRuleBody(
            content=CreateRuleBodyContent(
                rule_description=to_create,  # type: ignore
            )
        )
        request_body = create_entity_body.serialize(is_xml=True)
        serialize_rule_key_values(request_body, rule)
        with _handle_response_error():
            entry_ele = self._impl.rule.put(
                topic_name, subscription_name, rule_name, request_body, **kwargs  # type: ignore
            )
        entry = RuleDescriptionEntry.deserialize(entry_ele)
        # Need to cast from Optional[RuleDescriptionEntryContent] to RuleDescriptionEntryContent
        # since we know for certain that `entry.content` will not be None here.
        entry.content = cast(RuleDescriptionEntryContent, entry.content)
        result = RuleProperties._from_internal_entity(rule_name, entry.content.rule_description)
        deserialize_rule_key_values(entry_ele, result)  # to remove after #3535 is released.
        return result

    def update_rule(
        self, topic_name: str, subscription_name: str, rule: Union[RuleProperties, Mapping[str, Any]], **kwargs: Any
    ) -> None:
        """Update a rule.

        Before calling this method, you should use `get_rule`, `create_rule` or `list_rules` to get a `RuleProperties`
        instance, then update the properties.
        You could also pass keyword arguments for updating properties in the form of
        `<property_name>=<property_value>` which will override whatever was specified in
        the `RuleProperties` instance. Refer to ~azure.servicebus.management.RuleProperties for names of properties.

        :param str topic_name: The topic that owns the subscription.
        :param str subscription_name: The subscription that
         owns this rule.
        :param rule: The rule that is returned from `get_rule`,
         `create_rule`, or `list_rules` and has the updated properties.
        :type rule: ~azure.servicebus.management.RuleProperties

        :rtype: None
        """
        _validate_topic_and_subscription_types(topic_name, subscription_name)
        # we should not mutate the input, making a copy first for update
        rule = deepcopy(create_properties_from_dict_if_needed(rule, RuleProperties))
        to_update = rule._to_internal_entity(kwargs)

        create_entity_body = CreateRuleBody(
            content=CreateRuleBodyContent(
                rule_description=to_update,
            )
        )
        request_body = create_entity_body.serialize(is_xml=True)
        serialize_rule_key_values(request_body, rule)
        with _handle_response_error():
            self._impl.rule.put(
                topic_name,
                subscription_name,
                rule.name,
                request_body,
                match_condition=MatchConditions.IfPresent,
                **kwargs
            )

    def delete_rule(self, topic_name: str, subscription_name: str, rule_name: str, **kwargs: Any) -> None:
        """Delete a topic subscription rule.

        :param str topic_name: The topic that owns the subscription.
        :param str subscription_name: The subscription that
         owns the topic.
        :param str rule_name: The to-be-deleted rule.
        :rtype: None
        """
        _validate_topic_subscription_and_rule_types(topic_name, subscription_name, rule_name)

        self._impl.rule.delete(topic_name, subscription_name, rule_name, **kwargs)

    def list_rules(self, topic_name: str, subscription_name: str, **kwargs: Any) -> ItemPaged[RuleProperties]:
        """List the rules of a topic subscription.

        :param str topic_name: The topic that owns the subscription.
        :param str subscription_name: The subscription that
         owns the rules.
        :return: An iterable (auto-paging) response of RuleProperties.
        :rtype: ~azure.core.paging.ItemPaged[~azure.servicebus.management.RuleProperties]
        """
        _validate_topic_and_subscription_types(topic_name, subscription_name)

        def entry_to_rule(ele, entry):
            """
            `ele` will be removed after https://github.com/Azure/autorest/issues/3535 is released.

            :param any ele: The xml element.
            :param any entry: The xml entry.
            :return: The entry.
            :rtype: ~azure.core.paging.ItemPaged
            """
            rule = entry.content.rule_description
            rule_description = RuleProperties._from_internal_entity(entry.title, rule)
            deserialize_rule_key_values(ele, rule_description)  # to remove after #3535 is released.
            return rule_description

        extract_data = functools.partial(extract_rule_data_template, RuleDescriptionFeed, entry_to_rule)
        get_next = functools.partial(
            get_next_template, functools.partial(self._impl.list_rules, topic_name, subscription_name), **kwargs
        )
        return ItemPaged(get_next, extract_data)

    def get_namespace_properties(self, **kwargs: Any) -> NamespaceProperties:
        """Get the namespace properties

        :return: The namespace properties.
        :rtype: ~azure.servicebus.management.NamespaceProperties
        """
        entry_el = self._impl.namespace.get(**kwargs)  # type: ignore
        namespace_entry = NamespacePropertiesEntry.deserialize(entry_el)
        namespace_entry.content = cast(NamespacePropertiesEntryContent, namespace_entry.content)
        return NamespaceProperties._from_internal_entity(
            namespace_entry.title, namespace_entry.content.namespace_properties
        )

    def close(self) -> None:
        self._impl.close()
