import io
import json
import tempfile
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from PIL import Image

from .models import (
    Post,
    Comment,
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


class PostModelTest(TestCase):
    """Test Post model functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.tag1 = Tag.objects.create(name="technology")
        self.tag2 = Tag.objects.create(name="tutorial")

    def test_post_creation(self):
        """Test basic post creation"""
        post = Post.objects.create(
            author=self.user, title="Test Post", content="This is a test post"
        )
        self.assertEqual(post.title, "Test Post")
        self.assertEqual(post.content, "This is a test post")
        self.assertEqual(post.author, self.user)
        self.assertTrue(post.created_at)

    def test_post_string_representation(self):
        """Test post string representation"""
        post = Post.objects.create(
            author=self.user, title="Test Post", content="Test content"
        )
        self.assertEqual(str(post), f"Post {post.pk}")

    def test_post_tags_relationship(self):
        """Test many-to-many relationship with tags"""
        post = Post.objects.create(
            author=self.user, title="Test Post", content="Test content"
        )
        post.tags.add(self.tag1, self.tag2)

        self.assertEqual(post.tags.count(), 2)
        self.assertIn(self.tag1, post.tags.all())
        self.assertIn(self.tag2, post.tags.all())


class TagModelTest(TestCase):
    """Test Tag model functionality"""

    def test_tag_creation(self):
        """Test tag creation"""
        tag = Tag.objects.create(name="python")
        self.assertEqual(tag.name, "python")
        self.assertEqual(str(tag), "python")

    def test_tag_unique_constraint(self):
        """Test tag name uniqueness"""
        Tag.objects.create(name="python")
        with self.assertRaises(Exception):
            Tag.objects.create(name="python")


class PostAPITest(APITestCase):
    """Test Post API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )
        self.tag1 = Tag.objects.create(name="technology")
        self.tag2 = Tag.objects.create(name="tutorial")

        # Create test media files
        self.test_image = self.create_test_image()
        self.test_document = self.create_test_document()

    def create_test_image(self):
        """Create a test image file"""
        image = Image.new("RGB", (100, 100), color="red")
        image_file = io.BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        return SimpleUploadedFile(
            name="test_image.jpg",
            content=image_file.getvalue(),
            content_type="image/jpeg",
        )

    def create_test_document(self):
        """Create a test document file"""
        return SimpleUploadedFile(
            name="test_document.txt",
            content=b"This is a test document content",
            content_type="text/plain",
        )

    def test_post_list_unauthenticated(self):
        """Test listing posts without authentication"""
        Post.objects.create(
            author=self.user1, title="Public Post", content="This is a public post"
        )

        url = reverse("post-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_post_create_authenticated(self):
        """Test creating post with authentication"""
        self.client.force_authenticate(user=self.user1)

        data = {
            "title": "New Post",
            "content": "This is a new post",
            "tag_ids": [self.tag1.id, self.tag2.id],
        }

        url = reverse("post-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Post")
        self.assertEqual(response.data["content"], "This is a new post")
        self.assertEqual(response.data["author"], "user1")
        self.assertEqual(len(response.data["tags"]), 2)

    def test_post_create_unauthenticated(self):
        """Test creating post without authentication"""
        data = {"title": "New Post", "content": "This is a new post"}

        url = reverse("post-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_create_with_tag_objects(self):
        """Test creating post with new tag objects"""
        self.client.force_authenticate(user=self.user1)

        data = {
            "title": "Post with new tags",
            "content": "Content with new tags",
            "tag_objects": [{"name": "newtag1"}, {"name": "newtag2"}],
        }

        url = reverse("post-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["tags"]), 2)

        # Check that new tags were created
        self.assertTrue(Tag.objects.filter(name="newtag1").exists())
        self.assertTrue(Tag.objects.filter(name="newtag2").exists())

    def test_post_create_with_mixed_tags(self):
        """Test creating post with both tag_ids and tag_objects"""
        self.client.force_authenticate(user=self.user1)

        data = {
            "title": "Post with mixed tags",
            "content": "Content with mixed tags",
            "tag_ids": [self.tag1.id],
            "tag_objects": [{"name": "mixedtag"}],
        }

        url = reverse("post-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Currently only tag_ids are processed due to priority logic
        self.assertEqual(len(response.data["tags"]), 1)
        self.assertEqual(response.data["tags"][0]["name"], "technology")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_post_create_with_image_multipart(self):
        """Test creating post with image file using multipart/form-data"""
        self.client.force_authenticate(user=self.user1)

        data = {
            "title": "Post with Image",
            "content": "Content with image",
            "image_files": [self.create_test_image()],
        }

        url = reverse("post-list")
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["images"]), 1)

        # Check that PostImage was created
        post_id = response.data["id"]
        post = Post.objects.get(id=post_id)
        self.assertEqual(post.images.count(), 1)

    def test_post_update_by_author(self):
        """Test updating post by the author"""
        post = Post.objects.create(
            author=self.user1, title="Original Title", content="Original content"
        )

        self.client.force_authenticate(user=self.user1)

        data = {"title": "Updated Title", "content": "Updated content"}

        url = reverse("post-detail", kwargs={"pk": post.pk})
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Updated Title")
        self.assertEqual(response.data["content"], "Updated content")

    def test_post_update_by_non_author(self):
        """Test updating post by non-author (should fail)"""
        post = Post.objects.create(
            author=self.user1, title="Original Title", content="Original content"
        )

        self.client.force_authenticate(user=self.user2)

        data = {"title": "Hacked Title", "content": "Hacked content"}

        url = reverse("post-detail", kwargs={"pk": post.pk})
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_post_delete_by_author(self):
        """Test deleting post by the author"""
        post = Post.objects.create(
            author=self.user1, title="To Delete", content="This will be deleted"
        )

        self.client.force_authenticate(user=self.user1)

        url = reverse("post-detail", kwargs={"pk": post.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_post_search(self):
        """Test post search functionality"""
        Post.objects.create(
            author=self.user1, title="Python Programming", content="Learn Python basics"
        )
        Post.objects.create(
            author=self.user1,
            title="JavaScript Guide",
            content="JavaScript fundamentals",
        )

        url = reverse("post-list")
        response = self.client.get(url, {"search": "Python"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIn("Python", response.data["results"][0]["title"])

    def test_post_filter_by_author(self):
        """Test filtering posts by author"""
        Post.objects.create(
            author=self.user1, title="User1 Post", content="Content by user1"
        )
        Post.objects.create(
            author=self.user2, title="User2 Post", content="Content by user2"
        )

        url = reverse("post-list")
        response = self.client.get(url, {"author": "user1"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["author"], "user1")


class CommentAPITest(APITestCase):
    """Test Comment API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )
        self.post = Post.objects.create(
            author=self.user1, title="Test Post", content="Test content"
        )

    def test_comment_list_for_post(self):
        """Test listing comments for a specific post"""
        Comment.objects.create(post=self.post, author=self.user1, body="First comment")
        Comment.objects.create(post=self.post, author=self.user2, body="Second comment")

        url = reverse("post-comments-list", kwargs={"post_pk": self.post.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_comment_create_authenticated(self):
        """Test creating comment with authentication"""
        self.client.force_authenticate(user=self.user1)

        data = {"body": "This is a test comment"}

        url = reverse("post-comments-list", kwargs={"post_pk": self.post.pk})
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["body"], "This is a test comment")
        self.assertEqual(response.data["author"], "user1")

    def test_comment_create_unauthenticated(self):
        """Test creating comment without authentication"""
        data = {"body": "Unauthorized comment"}

        url = reverse("post-comments-list", kwargs={"post_pk": self.post.pk})
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_comment_create_with_media(self):
        """Test creating comment with media files"""
        self.client.force_authenticate(user=self.user1)

        # Create test image
        image = Image.new("RGB", (50, 50), color="blue")
        image_file = io.BytesIO()
        image.save(image_file, format="JPEG")
        image_file.seek(0)
        test_image = SimpleUploadedFile(
            name="comment_image.jpg",
            content=image_file.getvalue(),
            content_type="image/jpeg",
        )

        data = {"body": "Comment with image", "image_files": [test_image]}

        url = reverse("post-comments-list", kwargs={"post_pk": self.post.pk})
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["images"]), 1)

        # Check that CommentImage was created
        comment_id = response.data["id"]
        comment = Comment.objects.get(id=comment_id)
        self.assertEqual(comment.images.count(), 1)

    def test_comment_update_by_author(self):
        """Test updating comment by the author"""
        comment = Comment.objects.create(
            post=self.post, author=self.user1, body="Original comment"
        )

        self.client.force_authenticate(user=self.user1)

        data = {"body": "Updated comment"}

        url = reverse(
            "post-comments-detail", kwargs={"post_pk": self.post.pk, "pk": comment.pk}
        )
        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["body"], "Updated comment")

    def test_comment_delete_by_author(self):
        """Test deleting comment by the author"""
        comment = Comment.objects.create(
            post=self.post, author=self.user1, body="To be deleted"
        )

        self.client.force_authenticate(user=self.user1)

        url = reverse(
            "post-comments-detail", kwargs={"post_pk": self.post.pk, "pk": comment.pk}
        )
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())


class TagAPITest(APITestCase):
    """Test Tag API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.tag1 = Tag.objects.create(name="python")
        self.tag2 = Tag.objects.create(name="django")

    def test_tag_list(self):
        """Test listing all tags"""
        url = reverse("tag-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_tag_create_authenticated(self):
        """Test creating tag with authentication"""
        self.client.force_authenticate(user=self.user)

        data = {"name": "javascript"}

        url = reverse("tag-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "javascript")

    def test_tag_create_unauthenticated(self):
        """Test creating tag without authentication"""
        data = {"name": "react"}

        url = reverse("tag-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tag_search(self):
        """Test tag search functionality"""
        url = reverse("tag-list")
        response = self.client.get(url, {"search": "python"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "python")

    def test_tag_posts_action(self):
        """Test getting posts for a specific tag"""
        post = Post.objects.create(
            author=self.user, title="Python Tutorial", content="Learn Python"
        )
        post.tags.add(self.tag1)

        url = reverse("tag-posts", kwargs={"pk": self.tag1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Python Tutorial")


class MediaFilesTest(APITestCase):
    """Test media file handling"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def create_test_files(self):
        """Create various test files"""
        # Image
        image = Image.new("RGB", (100, 100), color="green")
        image_file = io.BytesIO()
        image.save(image_file, format="PNG")
        image_file.seek(0)
        test_image = SimpleUploadedFile(
            name="test.png", content=image_file.getvalue(), content_type="image/png"
        )

        # Document
        test_document = SimpleUploadedFile(
            name="test.txt", content=b"Test document content", content_type="text/plain"
        )

        return test_image, test_document

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_post_multiple_media_files(self):
        """Test creating post with multiple types of media files"""
        test_image, test_document = self.create_test_files()

        data = {
            "title": "Post with Multiple Media",
            "content": "Content with multiple media types",
            "image_files": [test_image],
            "document_files": [test_document],
        }

        url = reverse("post-list")
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["images"]), 1)
        self.assertEqual(len(response.data["documents"]), 1)

        # Verify database records
        post = Post.objects.get(id=response.data["id"])
        self.assertEqual(post.images.count(), 1)
        self.assertEqual(post.documents.count(), 1)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_comment_multiple_media_files(self):
        """Test creating comment with multiple media files"""
        post = Post.objects.create(
            author=self.user, title="Test Post", content="Test content"
        )

        test_image, test_document = self.create_test_files()

        data = {
            "body": "Comment with media",
            "image_files": [test_image],
            "document_files": [test_document],
        }

        url = reverse("post-comments-list", kwargs={"post_pk": post.pk})
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["images"]), 1)
        self.assertEqual(len(response.data["documents"]), 1)


class ErrorHandlingTest(APITestCase):
    """Test error handling scenarios"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_post_create_missing_required_field(self):
        """Test creating post without required content field"""
        self.client.force_authenticate(user=self.user)

        data = {
            "title": "Post without content"
            # Missing 'content' field
        }

        url = reverse("post-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_comment_create_for_nonexistent_post(self):
        """Test creating comment for non-existent post"""
        self.client.force_authenticate(user=self.user)

        data = {"body": "Comment on non-existent post"}

        url = reverse("post-comments-list", kwargs={"post_pk": 99999})
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tag_create_duplicate_name(self):
        """Test creating tag with duplicate name"""
        self.client.force_authenticate(user=self.user)

        Tag.objects.create(name="duplicate")

        data = {"name": "duplicate"}

        url = reverse("tag-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
