#!/usr/bin/env python3

import logging
import sys
from .. import worker # pylint: disable=relative-beyond-top-level

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)s:%(levelname)s:%(message)s')
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)

worker.main()
