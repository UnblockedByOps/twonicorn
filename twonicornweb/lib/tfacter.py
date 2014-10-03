import os
import subprocess


class tFacter:

    def __init__(self):
        # need this for ct_*
        os.environ["FACTERLIB"] = "/var/lib/puppet/lib/facter"
        p = subprocess.Popen(['facter'], stdout=subprocess.PIPE)
        p.wait()
        self.facts = p.stdout.readlines()
        # strip removes the trailing \n
        self.facts = dict(k.split(' => ') for k in
                          [s.strip() for s in self.facts if ' => ' in s])

    def get_fact(self, fact):

        return self.facts[fact]
