from rest_framework import serializers
from django.db import transaction

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
)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ["id", "image", "caption", "uploaded_at"]


class PostVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostVideo
        fields = ["id", "video", "caption", "uploaded_at"]


class PostAudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostAudio
        fields = ["id", "audio", "caption", "uploaded_at"]


class PostDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostDocument
        fields = ["id", "document", "caption", "uploaded_at"]


class CommentImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentImage
        fields = ["id", "image", "caption", "uploaded_at"]


class CommentVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentVideo
        fields = ["id", "video", "caption", "uploaded_at"]


class CommentAudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentAudio
        fields = ["id", "audio", "caption", "uploaded_at"]


class CommentDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentDocument
        fields = ["id", "document", "caption", "uploaded_at"]


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    images = CommentImageSerializer(many=True, read_only=True)
    videos = CommentVideoSerializer(many=True, read_only=True)
    audios = CommentAudioSerializer(many=True, read_only=True)
    documents = CommentDocumentSerializer(many=True, read_only=True)

    # Fields for creating media files
    image_files = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    video_files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )
    audio_files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )
    document_files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "body",
            "created_at",
            "images",
            "videos",
            "audios",
            "documents",
            "image_files",
            "video_files",
            "audio_files",
            "document_files",
        ]

    def create(self, validated_data):
        # Extract media files from validated data
        image_files = validated_data.pop("image_files", [])
        video_files = validated_data.pop("video_files", [])
        audio_files = validated_data.pop("audio_files", [])
        document_files = validated_data.pop("document_files", [])

        with transaction.atomic():
            comment = Comment.objects.create(**validated_data)

            # Create related media objects
            for image in image_files:
                CommentImage.objects.create(comment=comment, image=image)

            for video in video_files:
                CommentVideo.objects.create(comment=comment, video=video)

            for audio in audio_files:
                CommentAudio.objects.create(comment=comment, audio=audio)

            for document in document_files:
                CommentDocument.objects.create(comment=comment, document=document)

        return comment


class PostSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    comments = CommentSerializer(many=True, read_only=True)

    # Related media files (read-only)
    images = PostImageSerializer(many=True, read_only=True)
    videos = PostVideoSerializer(many=True, read_only=True)
    audios = PostAudioSerializer(many=True, read_only=True)
    documents = PostDocumentSerializer(many=True, read_only=True)

    # Tags with flexible handling
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of tag IDs to associate with the post",
    )
    tag_objects = serializers.ListField(
        child=TagSerializer(),
        write_only=True,
        required=False,
        help_text="List of tag objects to create/associate with the post",
    )

    # Fields for creating media files
    image_files = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    video_files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )
    audio_files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )
    document_files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "title",
            "content",
            "created_at",
            "source_url",
            "images",
            "videos",
            "audios",
            "documents",
            "comments",
            "tags",
            "tag_ids",
            "tag_objects",
            "image_files",
            "video_files",
            "audio_files",
            "document_files",
        ]

    def create(self, validated_data):
        # Extract media files and tags from validated data
        image_files = validated_data.pop("image_files", [])
        video_files = validated_data.pop("video_files", [])
        audio_files = validated_data.pop("audio_files", [])
        document_files = validated_data.pop("document_files", [])
        tag_ids = validated_data.pop("tag_ids", [])
        tag_objects = validated_data.pop("tag_objects", [])

        with transaction.atomic():
            post = Post.objects.create(**validated_data)

            # Handle tags - prioritize tag_ids over tag_objects
            if tag_ids:
                # Use existing tags by IDs
                existing_tags = Tag.objects.filter(id__in=tag_ids)
                post.tags.set(existing_tags)
            elif tag_objects:
                # Create/get tags from objects
                tags_to_add = []
                for tag_data in tag_objects:
                    tag, created = Tag.objects.get_or_create(
                        name=tag_data["name"], defaults=tag_data
                    )
                    tags_to_add.append(tag)
                post.tags.set(tags_to_add)

            # Create related media objects
            for image in image_files:
                PostImage.objects.create(post=post, image=image)

            for video in video_files:
                PostVideo.objects.create(post=post, video=video)

            for audio in audio_files:
                PostAudio.objects.create(post=post, audio=audio)

            for document in document_files:
                PostDocument.objects.create(post=post, document=document)

        return post

    def update(self, instance, validated_data):
        # Extract media files and tags from validated data
        image_files = validated_data.pop("image_files", [])
        video_files = validated_data.pop("video_files", [])
        audio_files = validated_data.pop("audio_files", [])
        document_files = validated_data.pop("document_files", [])
        tag_ids = validated_data.pop("tag_ids", None)
        tag_objects = validated_data.pop("tag_objects", None)

        with transaction.atomic():
            # Update basic fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # Handle tags if provided - prioritize tag_ids over tag_objects
            if tag_ids is not None:
                existing_tags = Tag.objects.filter(id__in=tag_ids)
                instance.tags.set(existing_tags)
            elif tag_objects is not None:
                tags_to_add = []
                for tag_data in tag_objects:
                    tag, created = Tag.objects.get_or_create(
                        name=tag_data["name"], defaults=tag_data
                    )
                    tags_to_add.append(tag)
                instance.tags.set(tags_to_add)

            # Add new media files (don't replace existing ones)
            for image in image_files:
                PostImage.objects.create(post=instance, image=image)

            for video in video_files:
                PostVideo.objects.create(post=instance, video=video)

            for audio in audio_files:
                PostAudio.objects.create(post=instance, audio=audio)

            for document in document_files:
                PostDocument.objects.create(post=instance, document=document)

        return instance
