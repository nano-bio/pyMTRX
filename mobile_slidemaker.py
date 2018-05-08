import pyMTRX

# Specify which scan directions to put onto the slides
# 0: Trace Up, 1: Retrace Up, 2: Trace Down, 3: Retrace Down
directions_to_use = [0, 1, 2, 3]

# Specify which imaging channels to put onto the slides
# This will accept all channels
scan_file_extentions = '[^.()]+_mtrx'
# Uncomment this to only accept Z images
#scan_file_extentions = 'Z_mtrx'

pyMTRX.notebook_slides(
    '.', dir_filter=directions_to_use, fext=scan_file_extentions
)
input('Press Enter to close')
