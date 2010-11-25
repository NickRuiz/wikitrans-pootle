HUMAN = 'Human'
GOOGLE = 'GoogleWorker'
BING = 'BingWorker'
APERTIUM = 'ApertiumWorker'
LUCY = 'LucyWorker'
MECHANICAL_TURK = 'Mechanical Turk'

TRANSLATORS = (
    (HUMAN, HUMAN),
    (GOOGLE, GOOGLE),
    (APERTIUM, APERTIUM),
    (MECHANICAL_TURK, MECHANICAL_TURK),
)

DEFAULT_TRANNY = GOOGLE

PENDING = 0
IN_PROGRESS = 1
FINISHED = 2
TRANSLATION_STATUSES = ( 
    (PENDING, 'Pending'),
    (IN_PROGRESS, 'In Progress'),
    (FINISHED, 'Finished'),
)
