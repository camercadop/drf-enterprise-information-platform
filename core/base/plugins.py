"""Base plugin classes for the enterprise platform."""


class ViewSetPlugin:
    """Base class for viewset plugins.

    Plugins are stateless and participate in the viewset lifecycle.
    They receive the viewset instance as first argument (which gives access
    to request, action, and serializer context).
    Short-circuit by raising any exception.

    Available hooks:
        on_build_context(viewset, context)
        on_post_destroy(viewset, instance)
        filter_queryset(viewset, qs) -> QuerySet  # must return the (filtered) queryset
    """


class SerializerPlugin:
    """Base class for serializer plugins.

    Plugins are stateless and participate in the serializer lifecycle.
    They receive the serializer instance as first argument (which gives access
    to context/request). Short-circuit by raising any exception.

    Available hooks:
        on_pre_create(serializer, validated_data)
        on_post_create(serializer, instance)
        on_pre_update(serializer, instance, validated_data)
        on_post_update(serializer, instance)
        on_pre_validate(serializer, data)
        on_post_validate(serializer, validated_data)
    """
