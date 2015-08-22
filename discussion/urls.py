from django.conf.urls import patterns, include, url
from django.views.generic import RedirectView

from discussion.views import (DiscussionList, DiscussionView,
                              CreatePost, PostView, Search)

discussion_patterns = patterns('',
    url(r'^$',
        RedirectView.as_view(url='../', permanent=True)),
    url(r'^(?P<slug>[\w-]+)/$',
        DiscussionView.as_view(), name='discussion'),
    url(r'^(?P<discussion_slug>[\w-]+)/posts/$',
        RedirectView.as_view(url='../', permanent=True)),
    url(r'^(?P<discussion_slug>[\w-]+)/posts/add/$',
        CreatePost.as_view(), name='discussion_add_post'),
    url(r'^(?P<discussion_slug>[\w-]+)/posts/(?P<pk>[\d]+)/$',
        PostView.as_view(), name='discussion_post'),
)

urlpatterns = patterns('discussion.views',
    url(r'^$', DiscussionList.as_view(), name='discussion_index'),
    url(r'^search/$', Search.as_view(), name='discussion_search'),
    url(r'^discussions/', include(discussion_patterns))
)
