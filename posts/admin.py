from django.contrib import admin

from .models import (
    Comment,
    Post,
    Tag,
    PostImage,
    PostVideo,
    PostAudio,
    PostDocument,
    CommentImage,
    CommentVideo,
    CommentAudio,
    CommentDocument,
    PostLike,
    CommentLike,
    PostView,
    PostClick,
    Reply,
)


class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 0


class PostVideoInline(admin.TabularInline):
    model = PostVideo
    extra = 0


class PostAudioInline(admin.TabularInline):
    model = PostAudio
    extra = 0


class PostDocumentInline(admin.TabularInline):
    model = PostDocument
    extra = 0


class CommentImageInline(admin.TabularInline):
    model = CommentImage
    extra = 0


class CommentVideoInline(admin.TabularInline):
    model = CommentVideo
    extra = 0


class CommentAudioInline(admin.TabularInline):
    model = CommentAudio
    extra = 0


class CommentDocumentInline(admin.TabularInline):
    model = CommentDocument
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "author", "created_at"]
    list_filter = ["created_at", "author"]
    search_fields = ["title", "content", "author__username"]
    inlines = [PostImageInline, PostVideoInline, PostAudioInline, PostDocumentInline]
    filter_horizontal = ["tags"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["id", "author", "post", "created_at"]
    list_filter = ["created_at", "author"]
    search_fields = ["body", "author__username"]
    inlines = [
        CommentImageInline,
        CommentVideoInline,
        CommentAudioInline,
        CommentDocumentInline,
    ]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


# Register media models individually (optional)
admin.site.register(PostImage)
admin.site.register(PostVideo)
admin.site.register(PostAudio)
admin.site.register(PostDocument)
admin.site.register(CommentImage)
admin.site.register(CommentVideo)
admin.site.register(CommentAudio)
admin.site.register(CommentDocument)

# Register other models
admin.site.register(PostLike)
admin.site.register(CommentLike)
admin.site.register(PostView)
admin.site.register(PostClick)
admin.site.register(Reply)
