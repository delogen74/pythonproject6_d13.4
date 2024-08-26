from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from celery import shared_task

class DigestRun(models.Model):
    last_run = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DigestRun from {self.last_run}"

class Author(models.Model):
    authorUser = models.OneToOneField(User, on_delete=models.CASCADE)
    ratingAuthor = models.SmallIntegerField(default=0)

    def update_rating(self):
        post_rat = self.post_set.aggregate(postRating=Sum('rating'))
        p_rat = post_rat.get('postRating') or 0

        comment_rat = self.authorUser.comment_set.aggregate(commentRating=Sum('rating'))
        c_rat = comment_rat.get('commentRating') or 0

        self.ratingAuthor = p_rat * 3 + c_rat
        self.save()

    def __str__(self):
        return self.authorUser.username

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Subscriber(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriber_subscriptions')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subscriber_subscriptions')

    def __str__(self):
        return f'{self.user.username} subscribed to {self.category.name}'

class Post(models.Model):
    NEWS = 'NW'
    ARTICLE = 'AR'
    CATEGORY_CHOICES = [
        (NEWS, 'Новость'),
        (ARTICLE, 'Статья'),
    ]

    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    categoryType = models.CharField(max_length=2, choices=CATEGORY_CHOICES, default=NEWS)
    dateCreation = models.DateTimeField(auto_now_add=True)
    postCategory = models.ManyToManyField(Category, through='PostCategory')
    title = models.CharField(max_length=200)
    text = models.TextField()
    rating = models.SmallIntegerField(default=0)
    image = models.ImageField(upload_to='post_images/', null=True, blank=True)

    def save(self, *args, **kwargs):
        self.text = self.censor_vulgar_words(self.text)
        super().save(*args, **kwargs)

    def censor_vulgar_words(self, text):
        vulgar_words = ['пидор', 'сука', 'редиска']
        for word in vulgar_words:
            text = text.replace(word, '*' * len(word))
        return text

    def like(self):
        self.rating += 1
        self.save()

    def dislike(self):
        self.rating -= 1
        self.save()

    def preview(self):
        return self.text[:123] + '...'

    def __str__(self):
        return self.title

class PostCategory(models.Model):
    postThrough = models.ForeignKey(Post, on_delete=models.CASCADE)
    categoryThrough = models.ForeignKey(Category, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.postThrough.title} - {self.categoryThrough.name}'

class Comment(models.Model):
    commentPost = models.ForeignKey(Post, on_delete=models.CASCADE)
    commentUser = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    dateCreation = models.DateTimeField(auto_now_add=True)
    rating = models.SmallIntegerField(default=0)

    def save(self, *args, **kwargs):
        self.text = self.censor_vulgar_words(self.text)
        super().save(*args, **kwargs)

    def censor_vulgar_words(self, text):
        vulgar_words = ['пидор', 'сука', 'редиска']
        for word in vulgar_words:
            text = text.replace(word, '*' * len(word))
        return text

    def like(self):
        self.rating += 1
        self.save()

    def dislike(self):
        self.rating -= 1
        self.save()

    def __str__(self):
        return f'{self.commentUser.username} - {self.commentPost.title}'

@receiver(post_save, sender=Post)
def post_post_save(sender, instance, **kwargs):
    notify_subscribers.delay(instance.id)

@shared_task
def notify_subscribers(post_id):
    from .models import Post, Subscriber

    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return

    subscribers = Subscriber.objects.filter(category__in=post.postCategory.all()).values_list('user__email', flat=True).distinct()

    for email in subscribers:
        send_mail(
            subject=f'Новый пост: {post.title}',
            message=f'Опубликована новая статья: {post.title}\n\nЧитать здесь: http://127.0.0.1:8000/news/{post.id}/',
            from_email='autotechsupp74@yandex.ru',
            recipient_list=[email]
        )