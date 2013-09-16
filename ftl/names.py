import re


shared_order = 0

def give(trunk=None):
    """ Create unique name for a variable. """
    global shared_order
    if trunk is not None:
        m = re.match(r"N_(.*?)_\d+\Z", str(trunk))
        if m:
            trunk = m.group(1) + '_'
        else:
            # if str(trunk)[0:2] == 'N_' and str(trunk)[]
            trunk = str(trunk) + '_'
    s = 'N_{0}{1}'.format(trunk, shared_order)
    shared_order += 1
    return s
