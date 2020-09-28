# Shabnam Nazmi.
# Graduate research assistant at electrical and computer engineering department,
# North Carolina A&T State University, Greensboro, NC.
# snazmi@aggies.ncat.edu.
#
# ------------------------------------------------------------------------------

SEED_NUMBER = 10

DATA_DIR = "D:\Datasets"
DATA_HEADER = "mit-csail"
REPORT_PATH = "report"
NO_FEATURES = 256
NO_LABELS = 50
GET_MLD_PROP = True

REBOOT_MODEL = 1
MAX_ITERATION = 0
MAX_CLASSIFIER = 100
PROB_HASH = 0.85
TRACK_FREQ = 1000
AVG_COUNT = 1

PREDICTION_METHOD = 2  # 1: max prediction - 2: aggregated prediction
THRESHOLD = 1  # 1: score-based one-threshold - 2: rank-based rank-cut
THETA = 0.5
RANK_CUT = 1

K = 2  # number of label clusters
L_MIN = 2

DEMO = True

# ------------------------------------------------------------------------------
INIT_FITNESS = 0.01
FITNESS_RED = 0.1
NU = 1
THETA_SUB = 200
LOSS_SUB = 0.01
BETA = 0.1
ERROR = 1e-2
DELTA = 0.1
THETA_DEL = 20
DO_SUBSUMPTION = True

# GA parameters
SELECTION = 't'   # 'r': roulette wheel selection - 't': tournament selection
P_XOVER = 0.8
P_MUT = 0.001
THETA_GA = 50
