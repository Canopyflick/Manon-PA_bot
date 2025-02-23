import random, logging

logger = logging.getLogger(__name__)

PA_options = [
    '🦄', '🐲', '🧌', '🧓', '💖', '👮‍♀',
    '🧜‍♀️', '🧚‍♀️'
]

PA = random.choice(PA_options)