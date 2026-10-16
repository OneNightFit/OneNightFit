from django.contrib import admin
from inspo.models import Tag, Post, Bookmark, Board

# Register your models here.
admin.site.register([Tag, Post, Bookmark, Board])