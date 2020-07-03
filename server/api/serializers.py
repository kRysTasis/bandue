from rest_framework import serializers
from .models import (
    mUser,
    HashTag,
    Tweet,
    Reply,
    mSetting,
    hUserUpd,
    hTweetUpd,
    mAccessLog,
    Band,
    MemberShip,
    Entry,
    Room,
    Message,
    Age,
    ReadManagement,
)
from rest_framework.renderers import JSONRenderer

import logging
from django.templatetags.i18n import language
from idlelib.idle_test.test_colorizer import source
from django.db.models import Q

logging.basicConfig(
    level = logging.DEBUG,
    format = '''%(levelname)s %(asctime)s %(pathname)s:%(funcName)s:%(lineno)s
    %(message)s''')


logger = logging.getLogger(__name__)




class ProfileSubSerializer(serializers.ModelSerializer):

    class Meta:
        model = mUser
        fields = [
            'id',
            'username',
            'email',
            'address',
            'created_at',
            'header',
            'introduction',
            'icon',
        ]



class HashTagSerializer(serializers.ModelSerializer):

    class Meta:
        model = HashTag
        fields = [
            'id',
            'title',
            'created_at',
            'slug',
        ]



class ProfileSerializer(serializers.ModelSerializer):
    """
    プロフィールのシリアライザー

        Fields
        -------------------------------------
        followees : フォローしているユーザー一覧
        followers : フォローされているユーザー一覧
    """

    followees = ProfileSubSerializer(many=True)
    followers = serializers.SerializerMethodField()
    followees_count = serializers.IntegerField(source='followees.count')
    followers_count = serializers.SerializerMethodField()
    tweet = serializers.SerializerMethodField()
    entry = serializers.SerializerMethodField()
    setting = serializers.SerializerMethodField()

    class Meta:
        model = mUser
        fields = [
            'id',
            'username',
            'email',
            'address',
            'created_at',
            'header',
            'introduction',
            'icon',
            'followees',
            'followers',
            'followees_count',
            'followers_count',
            'tweet',
            'entry',
            'setting',
        ]


    def get_followers(self, obj):
        return ProfileSubSerializer(mUser.objects.filter(followees=obj), many=True).data

    def get_followers_count(self, obj):
        return len(self.get_followers(obj)) if self.get_followers(obj) != None else 0

    def get_tweet(self, obj):
        return TweetSerializer(Tweet.objects.filter(author=obj), many=True).data

    def get_entry(self, obj):
        return EntrySerializer(Entry.objects.filter(author=obj), many=True).data


    def get_setting(self, obj):
        setting = mSetting.objects.get(target=obj)
        logger.info(setting.target__username)
        return MSettingSerializer(mSetting.objects.get(target=obj)).data


class TweetSerializer(serializers.ModelSerializer):
    """
    ツイートのシリアライザー

        Fields
        --------------------------------------------------
        isLiked : 表示したユーザーが既にいいねしているかどうか
        isRetweet : リツイートかどうか
        isRetweeted : 表示したユーザーが既にリツイートしているかどうか
    """

    author = serializers.ReadOnlyField(source='author.username')
    author_pk = serializers.CharField(required=False)
    hashTag = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()
    liked_count = serializers.SerializerMethodField()
    isLiked = serializers.SerializerMethodField()
    isReplied = serializers.SerializerMethodField()
    reply = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()
    isRetweeted = serializers.SerializerMethodField()
    retweet = serializers.SerializerMethodField()
    retweet_count = serializers.SerializerMethodField()
    retweet_user = serializers.ReadOnlyField()
    userIcon = serializers.SerializerMethodField()


    def __init__(self, *args, **kwargs):
        self.login_user = kwargs['context']['view'].get_login_user() if 'context' in kwargs else None
        super().__init__(*args, **kwargs)

    class Meta:
        model = Tweet
        fields = [
            'id',
            'author',
            'author_pk',
            'content',
            'liked',
            'liked_count',
            'hashTag',
            'images',
            'created_at',
            'updated_at',
            'isLiked',
            'reply',
            'isReplied',
            'reply_count',
            'isRetweet',
            'isRetweeted',
            'retweet',
            'retweet_user',
            'retweet_count',
            'userIcon',
        ]

    def get_hashTag(self, obj):
        return HashTagSerializer(obj.hashTag.all(), many=True).data

    def get_liked(self, obj):
        return ProfileSubSerializer(obj.liked.all(), many=True).data

    def get_liked_count(self, obj):
        if obj.isRetweet == True:
            return obj.retweet.liked.count()
        return obj.liked.count()


    def get_isLiked(self, obj):
        isLiked = False
        if self.login_user != None:
            target_tweet = obj.retweet if obj.isRetweet else obj
            isLiked = target_tweet.liked.filter(username=self.login_user).exists()
        return isLiked


    def get_isReplied(self, obj):
        isReplied = True if len(obj.reply_set.all()) != 0 else False
        return isReplied


    def get_isRetweeted(self, obj):

        # TODO 計算量問題
        isRetweeted = False
        if self.login_user != None:
            target_tweet = obj.retweet if obj.isRetweet else obj

            for retweet in Tweet.objects.filter(retweet=target_tweet):
                if retweet.retweet_user == self.login_user:
                    isRetweeted = True
                    break

            # isRetweeted = target_tweet.retweet.filter(retweet_user=self.login_user).exists()

        return isRetweeted

    def get_reply(self, obj):
        return ReplySerializer(obj.reply_set.all(), many=True).data


    def get_reply_count(self, obj):
        return obj.reply_set.all().count()


    def get_retweet(self, obj):
        return TweetSerializer(Tweet.objects.filter(retweet=obj), many=True).data


    def get_retweet_count(self, obj):
        if obj.isRetweet == True:
            return len(Tweet.objects.filter(retweet=obj.retweet))
        return len(Tweet.objects.filter(retweet=obj))


    def get_userIcon(self, obj):
        return '/media/' + str(obj.author.icon)


    def create(self, validated_data):
        user = mUser.objects.get(pk=validated_data['author_pk'])
        content = validated_data['content']
        images = validated_data['images'] if 'images' in validated_data else None
        return Tweet.objects.create(author=user, content=content, images=images)


    def update(self, instance, validated_data):
        instance.content = validated_data['content']
        instance.save()
        return instance


class ReplySerializer(serializers.ModelSerializer):

    author = serializers.CharField(source='author.username')
    author_pk = serializers.CharField(source='author.pk')

    class Meta:
        model = Reply
        fields = [
            'id',
            'author',
            'author_pk',
            'target',
            'content',
            'created_at',
        ]

    def create(self, validated_data):
        user = mUser.objects.get(pk=validated_data['author_pk'])
        target = Tweet.objects.get(pk=validated_data['target_tweet'])
        content = validated_data['content']
        return Reply.objects.create(author=user, target=target, content=content)


# カスタムフィールド参考用
class SelectSerializer(serializers.Field):

    def to_internal_value(self, data):
        return data

    def get_attribute(self, instance):
        method = 'get_%s_display' % (self.field_name)
        disp_name = getattr(instance, method)()
        return disp_name

    def to_representation(self, value):
        return value


class EntrySerializer(serializers.ModelSerializer):

    author = serializers.ReadOnlyField(source='author.username')
    author_pk = serializers.CharField(required=False)
    # type = SelectSerializer()
    # prefecture = SelectSerializer()
    # day_week = SelectSerializer()
    # direction = SelectSerializer()
    # sex = SelectSerializer()
    # age = SelectSerializer()
    type_disp = serializers.SerializerMethodField()
    prefecture_disp = serializers.SerializerMethodField()
    day_week_disp = serializers.SerializerMethodField()
    direction_disp = serializers.SerializerMethodField()
    sex_disp = serializers.SerializerMethodField()
    age_disp = serializers.SerializerMethodField()
    age = serializers.ListField(write_only=True, required=False, child=serializers.IntegerField())
    is_read = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.login_user = kwargs['context']['view'].get_login_user() if 'context' in kwargs else None
        super().__init__(*args, **kwargs)

    class Meta:
        model = Entry
        fields = [
            'id',
            'title',
            'content',
            'author',
            'author_pk',
            'type',
            'type_disp',
            'prefecture',
            'prefecture_disp',
            'area',
            'day_week',
            'day_week_disp',
            'direction',
            'direction_disp',
            'part',
            'genre',
            'sex',
            'sex_disp',
            'age',
            'age_disp',
            'is_read',
        ]

    def get_type_disp(self, obj):
        return obj.get_type_display()

    def get_prefecture_disp(self, obj):
        return obj.get_prefecture_display()

    def get_day_week_disp(self, obj):
        return obj.get_day_week_display()

    def get_direction_disp(self, obj):
        return obj.get_direction_display()

    def get_sex_disp(self, obj):
        return obj.get_sex_display()

    def get_age_disp(self, obj):
        age = obj.age
        logger.info('----年齢一覧取得----')
        logger.info(obj.age.all())
        if len(obj.age.all()) != 0:
            age_list = [age.get_age_display() for age in obj.age.all()]
        return age_list

    def get_is_read(self, obj):
        target = mUser.objects.get(username=self.login_user)
        read_manage_cnt = ReadManagement.objects.filter(Q(entry=obj) & Q(target=target)).count()
        return False if read_manage_cnt == 0 else True # 既読されていたらTrueを返却

    def create(self, validated_data):
        entry = Entry.objects.create(
            author = mUser.objects.get(pk=validated_data['author_pk']),
            title = validated_data['title'],
            content = validated_data['content'],
            type = validated_data['type'],
            prefecture = validated_data['prefecture'],
            area = validated_data['area'],
            day_week = validated_data['day_week'],
            direction = validated_data['direction'],
            part = validated_data['part'],
            genre = validated_data['genre'],
            sex = validated_data['sex'],
        )
        if len(validated_data['age']) != 0:
            age_list = [Age.objects.get(age=age) for age in validated_data['age']]
            for age in age_list:
                entry.age.add(age)

        return entry


class MUserSerializer(serializers.ModelSerializer):

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = mUser
        fields = [
            'pk',
            'username',
            'email',
            'password',
        ]

    def create(self, validated_data):
        return mUser.objects.create_user(username=validated_data['username'], email=validated_data['email'], password=validated_data['password'])


class RoomSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    room_name = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.login_user = kwargs['context']['view'].get_login_user()
        super().__init__(*args, **kwargs)

    class Meta:
        model = Room
        fields = [
            'id',
            'name',
            'room_name',
            'users',
            'created_at',
        ]

    def get_room_name(self, obj):
        room_name = ''
        target_user = Room.objects.get(id=obj.id).users.exclude(username=self.login_user)
        for i in target_user:
            room_name += i.username
        return room_name

    def get_users(self, obj):
        users = Room.objects.get(id=obj.id).users.exclude(username=self.login_user)
        user_contents = ProfileSubSerializer(users, many=True).data
        return user_contents

    def create(self, validated_data):
        name = validated_data['name']
        room = Room.objects.create()
        room.users.add(mUser.objects.get(username=self.login_user))
        room.users.add(mUser.objects.get(username=name))
        return room

class MessageSerializer(serializers.ModelSerializer):

    sender = serializers.SerializerMethodField()
    receiver = serializers.SerializerMethodField()
    isMe = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.login_user = kwargs['context']['view'].get_login_user()
        super().__init__(*args, **kwargs)

    class Meta:
        model = Message
        fields = [
            'id',
            'content',
            'sender',
            'receiver',
            'image',
            'readed',
            'deleted',
            'isMe',
            'created_at',
        ]

    def get_sender(self, obj):
        sender_name = obj.sender.username
        return sender_name

    def get_receiver(self, obj):
        receiver_name = obj.receiver.username
        return receiver_name

    def get_isMe(self, obj):
        isMe = str(obj.sender.username) == str(self.login_user)
        return isMe


class MSettingSerializer(serializers.ModelSerializer):

    class Meta:
        model = mSetting
        fields = [
            'id',
            'target',
            'tweet_limit_level',
            'language',
            'isDark'
        ]
