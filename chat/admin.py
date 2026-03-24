from django.contrib import admin

from chat.models import ChatMessage, ChatSession


class ChatMessageInline(admin.StackedInline):
    model = ChatMessage
    extra = 0
    can_delete = False
    max_num = 0
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "role",
                    "content",
                ),
            },
        ),
        (
            "Diagnostics",
            {
                "classes": ("collapse",),
                "fields": (
                    "error_message",
                    "finish_reason",
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "raw_metadata",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )
    readonly_fields = (
        "role",
        "content",
        "error_message",
        "finish_reason",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "raw_metadata",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request, obj=None) -> bool:
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_model_name",
        "get_provider_name",
        "message_count",
        "created_at",
        "updated_at",
    )
    list_filter = ("llm_model__provider", "llm_model", "created_at")
    search_fields = (
        "id",
        "llm_model__name",
        "llm_model__external_model_id",
        "llm_model__provider__name",
        "llm_model__provider__display_name",
    )
    fields = ("llm_model", "created_at", "updated_at")
    readonly_fields = ("llm_model", "created_at", "updated_at")
    inlines = (ChatMessageInline,)

    def has_add_permission(self, request) -> bool:
        return False

    @staticmethod
    def get_model_name(obj: ChatSession) -> str:
        return obj.llm_model.name

    get_model_name.short_description = "model"

    @staticmethod
    def get_provider_name(obj: ChatSession) -> str:
        return obj.llm_model.provider.display_name

    get_provider_name.short_description = "provider"

    @staticmethod
    def message_count(obj: ChatSession) -> int:
        return obj.messages.count()

    message_count.short_description = "messages"
