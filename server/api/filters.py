from django_filters import rest_framework as django_filter
from django.db.models import Q
from .models import (
    mUser,
    HashTag,
    Tweet,
    mSetting,
    hUserUpd,
    hTweetUpd,
    mAccessLog,
    Entry,
    Room,
    Message,
    ReadManagement,
    FollowRelationShip,
    RetweetRelationShip,
)
import logging
logger = logging.getLogger(__name__)

from django.shortcuts import get_object_or_404



class TweetFilter(django_filter.FilterSet):
    """
    ツイートを絞るフィルタークラス

        Parameters
        -----------------------------------------
        tweetListFlg : ページによってツイートを絞る
            0: リプライツイート除いた一覧
            1: リプライツイート含めた一覧
            2: 画像含めた一覧
            3: いいねしたツイート一覧
            4: ユーザー&フォローユーザーツイート一覧

        searchFlg : 検索文字によってツイートを絞る
            0 : トレンド
            1 : 新着順
            3 : 画像ありツイート
            ※2はユーザーリストでユーザーフィルターで絞る。

        searchText : 検索文字列
    """

    def __init__(self, *args, **kwargs):
        self.login_user = kwargs['data']['loginUser'] if 'loginUser' in kwargs['data'] else None
        self.target_user = kwargs['data']['targetUser'] if 'targetUser' in kwargs['data'] else None
        self.searchFlg = kwargs['data']['searchFlg'] if 'searchFlg' in kwargs['data'] else None
        super().__init__(*args, **kwargs)

    tweetListFlg = django_filter.NumberFilter(method='tweet_filter')
    searchText = django_filter.CharFilter(field_name='content', method='content_filter')
    deleted = django_filter.BooleanFilter(field_name='deleted', method='deleted_filter')


    class Meta:
        model = Tweet
        fields = ['deleted']

    # 検索文字からツイートを絞る
    def content_filter(self, queryset, name, value):
        logger.debug('=====CONTENT_FILTER=====')

        h_list = []
        q_list = []
        qs = list({i.strip() for i in value.split(',')})
        for q in qs:
            if q[0] == '#':
                h_list.append('Q(hashTag__title=q)')
            else:
                q_list.append('Q(content__contains=q)')
        query_str = '&'.join(q_list) + '|'.join(h_list)

        # ブロックリストにログインユーザーが入っている場合,
        # また、非公開の場合、省く
        q = Tweet.objects.filter(eval(query_str)).exclude(
            Q(author__msetting__block_list__username=self.login_user) |
            Q(author__msetting__isPrivate=True)
        )
        # TODO トレンド順
        if self.searchFlg == '0':
            logger.debug('=====================================トレンド============================================')
            q = q.order_by('-created_at')

        # 新着順
        elif self.searchFlg == '1':
            q = q.order_by('-created_at')

        # 画像ある該当ツイートで新着順
        elif self.searchFlg == '3':
            q = q.exclude(images__isnull=False).order_by('-created_at')

        logger.debug('検索結果 : ')
        logger.debug(q)
        return q


    # ページによってTweetを絞る
    def tweet_filter(self, queryset, name, value):
        logger.debug('=====TWEET_FILTER=====')
        res = queryset
        if self.target_user != None:

            # target_user = mUser.objects.get(username=self.target_user)
            target_user = get_object_or_404(mUser, username=self.target_user)

            # リプライツイート除いた一覧
            if value == 0:

                user_tweet = target_user.author.all().exclude(Q(isReply=True))
                user_retweet = Tweet.objects.filter(pk__in=target_user.retweet_user.all().values('retweet'))
                res = user_tweet.union(user_retweet).order_by('-created_at')

            # リプライツイート含めた一覧
            elif value == 1:

                user_tweet = target_user.author.all()
                user_retweet = Tweet.objects.filter(pk__in=target_user.retweet_user.all().values('retweet'))
                res = user_tweet.union(user_retweet).order_by('-created_at')

            # 画像含めた一覧
            elif value == 2:
                res = target_user.author.all().exclude( \
                    Q(images__isnull=False) | \
                        Q(isRetweet=True) | Q(isReply=True)).order_by('-created_at')

            # いいねしたツイート一覧
            elif value == 3:
                res = target_user.liked.all().order_by('-created_at')

            # ユーザー&フォローユーザーツイート一覧
            elif value == 4:
                mute_list = target_user.msetting.mute_list

                # 自分のツイート
                my_tweets = target_user.author.all()

                # フォローユーザーのツイート
                #   ミュートしたユーザーは省く
                followees_tweets = Tweet.objects.filter( \
                    author__in=target_user.followees.all()).exclude(Q(isRetweet=True) \
                        | Q(author__in=mute_list.all()))

                # フォローユーザーのリツイート
                #   リプライツイート単体は省く
                followees_retweets = Tweet.objects.filter( \
                    pk__in=RetweetRelationShip.objects.filter( \
                        retweet_user__in=target_user.followees.all())).exclude(isReply=True)

                # unionしたものが結果
                res = my_tweets.union(followees_tweets).union(followees_retweets).order_by('-created_at')

        logger.debug('--TWEET_FILTER_RESULT--')
        logger.debug(res)
        return res


    def deleted_filter(self, queryset, name, value):

        logger.debug('====DELETED_FILTER====')
        logger.debug(name)
        logger.debug(value)
        lookup = '__'.join([name, 'isnull'])
        res = queryset.filter(**{lookup: value})
        logger.debug('--result--')
        logger.debug(res)
        return res


    def get_username(self):

        return self.target_user if self.target_user != None else None



class MUserFilter(django_filter.FilterSet):
    """
    ユーザーを絞るフィルタークラス

        Parameters
        --------------------------------------------------------
        self.login_userを元にログインユーザー以外の該当ユーザーを絞る
    """

    searchText = django_filter.CharFilter(field_name='username', method='username_filter')

    class Meta:
        model = mUser
        fields = ['username']

    def __init__(self, *args, **kwargs):
        self.login_user = kwargs['data']['loginUser'] if 'loginUser' in kwargs['data'] else None
        super().__init__(*args, **kwargs)

    def username_filter(self, queryset, name, value):

        # TODO ログインユーザーがブロックされてたら検索結果に対象ユーザーをのせない

        # 同じ検索ワード, ハッシュタグは省く
        q_list = list({Q(username__contains=i.strip()) for i in value.split(',') if i.strip()[0] != '#'})
        return mUser.objects.filter(*q_list).exclude(Q(username=self.login_user))


class EntryFilter(django_filter.FilterSet):
    """
    記事一覧を絞るフィルタークラス
    """

    entryListFlg = django_filter.NumberFilter(method='entry_filter')

    class Meta:
        model = Entry
        fields = ['title']

    def entry_filter(self, queryset, name, value):
        logger.info('------Entry Filter------')
        res = queryset

        if value == 0:
            # 人気記事一覧
            res = Entry.objects.filter(is_public=False).order_by('-read_count')
        elif value == 1:
            # 新着記事一覧
            res = Entry.objects.filter(is_public=False).order_by('-created_at')

        logger.info(res)

        return res


class RoomFilter(django_filter.FilterSet):
    """
    部屋を絞るフィルタークラス
    """
    loginUser = django_filter.CharFilter(method='self_room')
    searchText = django_filter.CharFilter(field_name='users__username', method='content_filter')

    def __init__(self, *args, **kwargs):
        self.login_user = kwargs['data']['loginUser'] if 'loginUser' in kwargs['data'] else None
        super().__init__(*args, **kwargs)

    class Meta:
        model = Room
        fields = []

    def self_room(self, queryset, name, value):
        user = mUser.objects.get(username=self.login_user)
        queryset = user.room_set.all()
        return queryset

    # 検索文字からツイートを絞る
    def content_filter(self, queryset, name, value):

        q_list = []
        qs = list({i.strip() for i in value.split(',')})
        for q in qs:
            q_list.append('Q(users__username__contains=q)')

        query_str = '&'.join(q_list)
        # ログインユーザー以外の部屋を取得
        query_str += ' & ~Q(users__username="{0}")'.format(self.login_user)
        q = Room.objects.filter(eval(query_str))

        # ログインユーザーの部屋と検索結果の部屋を照合
        pk_list = []
        for i in q:
            for j in queryset:
                if i.id == j.id:
                    # ログインユーザーの部屋の中に検索結果の部屋が存在
                    pk_list.append(i.id)
                    break

        res = Room.objects.filter(pk__in=pk_list)
        logger.debug('検索結果 : ')
        logger.info(res)
        return res
