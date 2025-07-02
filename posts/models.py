from django.contrib.auth.models import User
from django.db import models
from .validators import (
    validate_document_file,
    validate_image_file,
    validate_video_file,
    validate_audio_file,
)


class Tag(models.Model):
    name = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(null=True, blank=True, max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    source_url = models.URLField(
        max_length=2048,
        unique=True,
        null=True,
        blank=True,
        help_text="The source URL of the opportunity to prevent duplicates. Can be used for other purposes as well.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post {self.pk}"


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to="post_images/",
        validators=[validate_image_file],
        help_text="Upload images (JPG, JPEG, PNG, GIF, BMP, WEBP, SVG, TIFF). Max size: 50MB",
    )
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for Post {self.post.pk}"


class PostVideo(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="videos")
    video = models.FileField(
        upload_to="post_videos/",
        validators=[validate_video_file],
        help_text="Upload videos (MP4, AVI, MOV, WMV, FLV, WEBM, MKV, M4V, 3GP, OGV). Max size: 50MB",
    )
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Video for Post {self.post.pk}"


class PostAudio(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="audios")
    audio = models.FileField(
        upload_to="post_audios/",
        validators=[validate_audio_file],
        help_text="Upload audio files (MP3, WAV, OGG, M4A, AAC, FLAC, WMA, OPUS, WEBM). Max size: 50MB",
    )
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audio for Post {self.post.pk}"


class PostDocument(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="documents")
    document = models.FileField(
        upload_to="post_documents/",
        validators=[validate_document_file],
        help_text="Upload documents (PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX). Max size: 50MB",
    )
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for Post {self.post.pk}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on post {self.post.id}: {self.body[:30]}"


class CommentImage(models.Model):
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(
        upload_to="comment_images/",
        validators=[validate_image_file],
        help_text="Upload images (JPG, JPEG, PNG, GIF, BMP, WEBP, SVG, TIFF). Max size: 50MB",
    )
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for Comment {self.comment.pk}"


class CommentVideo(models.Model):
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name="videos"
    )
    video = models.FileField(
        upload_to="comment_videos/",
        validators=[validate_video_file],
        help_text="Upload videos (MP4, AVI, MOV, WMV, FLV, WEBM, MKV, M4V, 3GP, OGV). Max size: 50MB",
    )
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Video for Comment {self.comment.pk}"


class CommentAudio(models.Model):
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name="audios"
    )
    audio = models.FileField(
        upload_to="comment_audios/",
        validators=[validate_audio_file],
        help_text="Upload audio files (MP3, WAV, OGG, M4A, AAC, FLAC, WMA, OPUS, WEBM). Max size: 50MB",
    )
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Audio for Comment {self.comment.pk}"


class CommentDocument(models.Model):
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name="documents"
    )
    document = models.FileField(
        upload_to="comment_documents/",
        validators=[validate_document_file],
        help_text="Upload documents (PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX). Max size: 50MB",
    )
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for Comment {self.comment.pk}"


class Reply(models.Model):
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name="replies"
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="replies")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]  # Order by oldest first for replies in a thread
        verbose_name_plural = "Replies"

    def __str__(self):
        return f"Reply by {self.author.username} to comment id {self.comment.id}: {self.body[:30]}"


class PostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")  # User can like a post only once
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} likes Post {self.post.pk}"

    """
    Enhancement Note:
    If you'll often need to show like/view counts, you might want to denormalize those into fields like:
    like_count = models.PositiveIntegerField(default=0)
    and update them via signals or overridden save() logic — improves performance.
    """


class CommentLike(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comment_likes"
    )
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "comment")  # User can like a comment only once
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} likes Comment {self.comment.id}"


class PostView(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="post_views",
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="views")
    viewed_at = models.DateTimeField(auto_now_add=True)
    # session_key = models.CharField(max_length=40, null=True, blank=True) # Optional: for anonymous users
    # ip_address = models.GenericIPAddressField(null=True, blank=True) # Optional: for anonymous users

    class Meta:
        ordering = ["-viewed_at"]

    def __str__(self):
        user_identifier = self.user.username if self.user else "Anonymous"
        return f"{user_identifier} viewed {self.post.title}"


class PostClick(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="post_clicks",
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="clicks")
    clicked_at = models.DateTimeField(auto_now_add=True)
    # destination_url = models.URLField(null=True, blank=True) # Optional: if clicks can lead to different URLs

    class Meta:
        ordering = ["-clicked_at"]

    def __str__(self):
        user_identifier = self.user.username if self.user else "Anonymous"
        return f"{user_identifier} clicked on {self.post.title}"
