import re
import numpy as np
from urllib.parse import urlparse
import math
from collections import Counter

FEATURE_NAMES = [
    'url_length', 'domain_length', 'path_length', 'has_ip', 'tld_length',
    'has_https', 'num_subdomains', 'num_params', 'num_fragments',
    'digit_ratio', 'special_char_ratio', 'has_login', 'has_bank', 'has_pay',
    'suspicious_tld', 'typo_squatting', 'homograph', 'entropy'
]

def extract_features(url):
    parsed
