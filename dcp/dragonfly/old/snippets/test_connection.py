from importlib import reload
import gc

from dragonfly import canon
from dragonfly import pegasus

pb = pegasus.PegasusPowerbox("/dev/ttyUSB1")
print("Connecting to powerbox")
pb.connect()

lens = canon.CanonEFLens()
print("Connecting to lens.")
lens.connect()