from users.user_vectorstore_utils import find_similar_users
from .serializers import UserSerializer


def get_recommended_peers(user, k=5):
    """
    Gets a list of recommended peers for a given user.
    """
    similar_users = find_similar_users(user, k=k)
    return UserSerializer(similar_users, many=True).data
