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

    # Fields for deleting existing media files
    delete_image_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of image IDs to delete",
    )
    delete_video_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of video IDs to delete",
    )
    delete_audio_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of audio IDs to delete",
    )
    delete_document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of document IDs to delete",
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
            "delete_image_ids",
            "delete_video_ids",
            "delete_audio_ids",
            "delete_document_ids",
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

    def update(self, instance, validated_data):
        # Extract media files and deletion IDs from validated data
        image_files = validated_data.pop("image_files", [])
        video_files = validated_data.pop("video_files", [])
        audio_files = validated_data.pop("audio_files", [])
        document_files = validated_data.pop("document_files", [])
        delete_image_ids = validated_data.pop("delete_image_ids", [])
        delete_video_ids = validated_data.pop("delete_video_ids", [])
        delete_audio_ids = validated_data.pop("delete_audio_ids", [])
        delete_document_ids = validated_data.pop("delete_document_ids", [])

        with transaction.atomic():
            # Update basic fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # Delete existing media files
            if delete_image_ids:
                CommentImage.objects.filter(
                    comment=instance, id__in=delete_image_ids
                ).delete()

            if delete_video_ids:
                CommentVideo.objects.filter(
                    comment=instance, id__in=delete_video_ids
                ).delete()

            if delete_audio_ids:
                CommentAudio.objects.filter(
                    comment=instance, id__in=delete_audio_ids
                ).delete()

            if delete_document_ids:
                CommentDocument.objects.filter(
                    comment=instance, id__in=delete_document_ids
                ).delete()

            # Add new media files
            for image in image_files:
                CommentImage.objects.create(comment=instance, image=image)

            for video in video_files:
                CommentVideo.objects.create(comment=instance, video=video)

            for audio in audio_files:
                CommentAudio.objects.create(comment=instance, audio=audio)

            for document in document_files:
                CommentDocument.objects.create(comment=instance, document=document)

        return instance


"""'
About the tag update:
Flexible Tag Management: 
Support for both selective removal (via remove_tag_ids) and complete ENTIRE replacement using set (via (if given) tag_ids or (else) tag_objects).
"""


class PostSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    comments = CommentSerializer(many=True, read_only=True)

    # Related media files (read-only)
    images = PostImageSerializer(many=True, read_only=True)
    videos = PostVideoSerializer(many=True, read_only=True)
    audios = PostAudioSerializer(many=True, read_only=True)
    documents = PostDocumentSerializer(many=True, read_only=True)

    # Tags with flexible handling
    # to read
    tags = TagSerializer(many=True, read_only=True)
    # to write
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

    # Fields for deleting existing media files
    delete_image_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of image IDs to delete",
    )
    delete_video_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of video IDs to delete",
    )
    delete_audio_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of audio IDs to delete",
    )
    delete_document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of document IDs to delete",
    )

    # Fields for tag deletion
    remove_tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of tag IDs to remove from the post",
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
            "delete_image_ids",
            "delete_video_ids",
            "delete_audio_ids",
            "delete_document_ids",
            "remove_tag_ids",
        ]

    def create(self, validated_data):
        # Extract media files and tags from validated data
        # popping because these fields are not part of the Post model
        # we need to add them to their respective separately
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
            elif tag_objects:  # if a list of tag objects is provided
                # Create/get tags from objects
                tags_to_add = []
                for tag_data in tag_objects:
                    tag, created = (
                        # tag is the variable name for the Tag object we are creating or getting. created is a boolean that tells us if the tag was created (T) or already existed (F).
                        Tag.objects.get_or_create(
                            name=tag_data["name"],
                            # The LHS name is the field in the Tag model. We are trying to get_or_create based on that field. The provided object has a "name" key. So tag_data["name"] in the RHS gives us the value to search for in the LHS field.
                            # so we created a new tag row if it didn't exist
                            # and now we will use defaults to set the other fields of the created tag row if needed/provided. defaults is only used if the tag was created, otherwise it is ignored.
                            defaults=tag_data,
                            # Use defaults to set other fields if needed (i.e. Tag model might have more fields than just name, this will set those fields as well if they are provided in tag_data)
                        )
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
        # Extract media files, tags, and deletion IDs from validated data
        image_files = validated_data.pop("image_files", [])
        video_files = validated_data.pop("video_files", [])
        audio_files = validated_data.pop("audio_files", [])
        document_files = validated_data.pop("document_files", [])
        tag_ids = validated_data.pop("tag_ids", None)
        tag_objects = validated_data.pop("tag_objects", None)
        remove_tag_ids = validated_data.pop("remove_tag_ids", [])
        delete_image_ids = validated_data.pop("delete_image_ids", [])
        delete_video_ids = validated_data.pop("delete_video_ids", [])
        delete_audio_ids = validated_data.pop("delete_audio_ids", [])
        delete_document_ids = validated_data.pop("delete_document_ids", [])

        with transaction.atomic():
            # Update basic fields
            for attr, value in validated_data.items():
                # validated_data is a dict of the received (and validated) data. update() handles both PUT and PATCH requests, so we need to update only the fields that are present in validated_data.
                setattr(instance, attr, value)
                # settattr REPLACES the value of the attribute attr in the instance with the value provided in validated_data.
            instance.save()

            # Handle tag removal first (before adding new ones)
            if remove_tag_ids:
                tags_to_remove = Tag.objects.filter(id__in=remove_tag_ids)
                instance.tags.remove(*tags_to_remove)

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

            # Delete existing media files
            if delete_image_ids:
                PostImage.objects.filter(
                    post=instance, id__in=delete_image_ids
                ).delete()

            if delete_video_ids:
                PostVideo.objects.filter(
                    post=instance, id__in=delete_video_ids
                ).delete()

            if delete_audio_ids:
                PostAudio.objects.filter(
                    post=instance, id__in=delete_audio_ids
                ).delete()

            if delete_document_ids:
                PostDocument.objects.filter(
                    post=instance, id__in=delete_document_ids
                ).delete()

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
