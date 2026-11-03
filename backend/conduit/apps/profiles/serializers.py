from django.core.validators import URLValidator
from django.templatetags.static import static
from rest_framework import serializers

from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    bio = serializers.CharField(allow_blank=True, required=False)
    image = serializers.CharField(allow_blank=True, required=False)
    following = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('username', 'bio', 'image', 'following',)
        read_only_fields = ('username',)

    def validate_image(self, value):
        if value == static('profiles/default-avatar.svg'):
            return ''
        if value:
            URLValidator()(value)
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['image'] = self.get_image(instance)
        return data

    def get_image(self, obj):
        if obj.image:
            return obj.image

        return static('profiles/default-avatar.svg')

    def get_following(self, instance):
        request = self.context.get('request', None)

        if request is None:
            return False

        if not request.user.is_authenticated():
            return False

        follower = request.user.profile
        followee = instance

        return follower.is_following(followee)
