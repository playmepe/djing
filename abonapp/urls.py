from django.conf.urls import url, include

import views


urlpatterns = [

    url(r'^$', views.grouplist, name='group_list'),
    url(r'^addgroup$', views.addgroup, name='add_group'),
    url(r'^delgroup', views.delgroup, name='del_group'),

    url(r'^(?P<gid>\d+)/', include('abonapp.urls_abon')),

    url(r'^log$', views.log_page, name='log'),

    url(r'^del$', views.delentity, name='del_abon'),

    url(r'^pay$', views.terminal_pay, name='terminal_pay'),

    url(r'^debtors$', views.debtors, name='debtors'),

    # Api's
    url(r'^api/abons$', views.abons),
    url(r'^api/abon_filter$', views.search_abon)
]
