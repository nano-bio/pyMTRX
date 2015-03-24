from pyMTRX.scripts.notebook_slides import main as nb_slide

# Specify which scan directions to put onto the slides
# 0: Trace Up, 1: Retrace Up, 2: Trace Down, 3: Retrace Down
directions_to_use = [0, 1, 2, 3]

# Specify which imaging channels to put onto the slides
# This will accept all channels
scan_file_extentions = '[^.()]+_mtrx'
# Uncomment this to only accept Z images
#scan_file_extentions = 'Z_mtrx'

nb_slide('.', dir_filter=directions_to_use, fext=scan_file_extentions)
raw_input('Press Eneter to close')
