from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^login/$', 'webui.views.login', name='webui-login'),
    url(r'^logout/$', 'webui.views.logout', name='webui-logout'),

    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/update/$', 'webui.views.collections.collection_update', name='webui-collection-update'),
    url(r'^collection/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/$', 'webui.views.collections.collection', name='webui-collection'),
    url(r'^collection/new/$', 'webui.views.collections.collection_new', name='webui-collection-new'),
    url(r'^collections/$', 'webui.views.collections.collections', name='webui-collections'),

    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/file/(?P<filenum>[\d]+)/$', 'webui.views.entities.entity_file', name='webui-entity-file'),
    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/add/$', 'webui.views.entities.entity_add', name='webui-entity-add'),
    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/update/$', 'webui.views.entities.entity_update', name='webui-entity-update'),
    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)-(?P<eid>[\d]+)/$', 'webui.views.entities.entity', name='webui-entity'),
    url(r'^entity/(?P<repo>[\w]+)-(?P<org>[\w]+)-(?P<cid>[\d]+)/new/$', 'webui.views.entities.entity_new', name='webui-entity-new'),

    url(r'^$', TemplateView.as_view(template_name="webui/index.html"), name='webui-index'),
)
