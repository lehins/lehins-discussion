import os

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import date, time
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from notification.models import NoticeType, create_notice_type, send
from orderable.models import Orderable


class Discussion(Orderable):
    user = models.ForeignKey(User)
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
    user = models.ForeignKey(User)
    body = models.TextField()
    attachment = models.FileField(upload_to='uploads/posts', blank=True, null=True)
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-time',)

    def __unicode__(self):
        return 'Post by {user} at {time} on {date}'.format(
            user=self.user,
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
    user = models.ForeignKey(User)
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
            user=self.user,
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
        send(subscription[1], subscription[0], context)
    

def post_notifications(sender, instance, created, **kwargs):
    related_object = instance.discussion.related_object
    if created and related_object:
        subscribtions = related_object.get_post_subscriptions(instance)
        notify_discussion_subscribers(instance.discussion, instance, subscribtions, 
                                      extra_context={'post': instance})
models.signals.post_save.connect(post_notifications, sender=Post)


def comment_notifications(sender, instance, created, **kwargs):
    related_object = instance.post.discussion.related_object
    if created and related_object:
        relevant_users = User.objects.filter(
            Q(comment__in=instance.post.comment_set.all()) |
            Q(post=instance.post)
            ).exclude(id=instance.user.id).distinct()
        subscribtions = related_object.get_comment_subscriptions(
            instance, relevant_users)
        notify_discussion_subscribers(
            instance.post.discussion, instance, subscribtions, 
            extra_context={'comment': instance})
models.signals.post_save.connect(comment_notifications, sender=Comment)
