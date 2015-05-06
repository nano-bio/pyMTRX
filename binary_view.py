import struct

fp = 'test_data/default_2013Jun21-111140_STM-STM_AtomManipulation_0001.mtrx'
data = []
with open(fp, 'rb') as f:
    for _ in range(2000):
        try:
            s = u'{:02x}'.format(ord(f.read(1)))
            data.append(s)
        except Exception:
            break

with open('bin_view.txt', 'w') as f:
    f.write( u' '.join(data) )


