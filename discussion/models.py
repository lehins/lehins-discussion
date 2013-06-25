import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.template.defaultfilters import date, time

from notification.models import send
from orderable.models import Orderable

__all__ = ["Discussion", "Post", "Comment"]

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

class Discussion(Orderable):
    user = models.ForeignKey(AUTH_USER_MODEL)
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    image = models.ImageField(
        upload_to='images/discussions', max_length=255, blank=True, null=True)
    description = models.TextField(default='', blank=True, null=True)
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    related_object = generic.GenericForeignKey('content_type', 'object_id')


    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('discussion', [self.slug])


class Post(models.Model):
    discussion = models.ForeignKey(Discussion)
    user = models.ForeignKey(AUTH_USER_MODEL)
    body = models.TextField()
    attachment = models.FileField(upload_to='uploads/posts', blank=True, null=True)
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-time',)

    def __unicode__(self):
        return 'Post by {user} at {time} on {date}'.format(
            user=self.user.get_full_name(),
            time=time(self.time),
            date=date(self.time),
        )

    @models.permalink
    def get_absolute_url(self):
        return ('discussion_post', [self.discussion.slug, str(self.id)])

    @property
    def attachment_filename(self):
        return self.attachment and os.path.basename(self.attachment.name)

    @property
    def prefix(self):
        return 'post-%d' % (self.pk or 0,)


class Comment(models.Model):
    post = models.ForeignKey(Post)
    user = models.ForeignKey(AUTH_USER_MODEL)
    body = models.TextField()
    attachment = models.FileField(upload_to='uploads/comments',
                                  blank=True, null=True)
    time = models.DateTimeField(auto_now_add=True)

    @property
    def attachment_filename(self):
        return self.attachment and os.path.basename(self.attachment.name)

    class Meta:
        ordering = ('time',)

    def __unicode__(self):
        return 'Comment by {user} at {time} on {date}'.format(
            user=self.user.get_full_name(),
            time=time(self.time),
            date=date(self.time),
        )

def notify_discussion_subscribers(
    discussion, instance, subscriptions, extra_context=None):
    """
        Notifies all users who have their notification settings set to True for given discussion
        instance parameter here is either Post or Comment
    """
    context = {'discussion': discussion}
    if extra_context:
        context.update(extra_context)
    for subscription in subscriptions:
        send(subscription[1], subscription[0], extra_context=context, 
             related_object=instance)
    

def post_notifications(sender, instance, created, **kwargs):
    related_object = instance.discussion.related_object
    if created and related_object:
        relevant_users = get_user_model().objects.exclude(id=instance.user.id)
        subscribtions = related_object.get_post_subscriptions(
            instance, relevant_users)
        notify_discussion_subscribers(instance.discussion, instance, subscribtions, 
                                      extra_context={'post': instance})
models.signals.post_save.connect(post_notifications, sender=Post)


def comment_notifications(sender, instance, created, **kwargs):
    related_object = instance.post.discussion.related_object
    if created and related_object:
        relevant_users = get_user_model().objects.filter(
            Q(comment__in=instance.post.comment_set.all()) |
            Q(post=instance.post)
            ).exclude(id=instance.user.id).distinct()
        subscribtions = related_object.get_comment_subscriptions(
            instance, relevant_users)
        notify_discussion_subscribers(
            instance.post.discussion, instance, subscribtions, 
            extra_context={'comment': instance})
models.signals.post_save.connect(comment_notifications, sender=Comment)
