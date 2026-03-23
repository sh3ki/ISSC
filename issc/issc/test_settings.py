from .settings import *

# Avoid importing heavy live-feed URL modules during tests.
ROOT_URLCONF = 'main.tests_urls'
