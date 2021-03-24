import os


class Results2D(object):
    coords = None
    time = None
    x_disp = None
    y_disp = None
    node_c = None
    ele_c = None
    used_r_starter = 0
    mat2ele_tags = None  # Assume 1-to-1 so if it uses a section then should be null
    sect2ele_tags = None  # Store position and tag - UNUSED
    mat2sect_tags = None  # UNUSED  # TODO: implement
    n_nodes_per_ele = [2, 4, 8]  # for 2D

    def __init__(self, cache_path='', dt=None, dynamic=False):
        self.cache_path = cache_path
        self._dt = dt
        self.dynamic = dynamic
        from numpy import savetxt, loadtxt
        self.savetxt = savetxt
        self.loadtxt = loadtxt
        self.ele2node_tags = {}
        self.meta_files = ['node_c', 'ele_c', 'mat2ele_tags', 'sect2ele_tags', 'mat2sect_tags']
        self.meta_fmt = [None, '%i', '%i', '%i']
        self.pseudo_dt = None  # use if recording steps of a static analysis


    def wipe_old_files(self):
        general = ['ele2node_tags', 'coords']
        for gen_file in general:
            try:
                os.remove(f'{self.cache_path}{gen_file}.txt')
            except FileNotFoundError:
                pass
        if not self.used_r_starter:
            try:
                os.remove(f'{self.cache_path}x_disp.txt')
            except FileNotFoundError:
                pass
            try:
                os.remove(f'{self.cache_path}y_disp.txt')
            except FileNotFoundError:
                pass

        for fname in self.meta_files:
            try:
                os.remove(f'{self.cache_path}{fname}.txt')
            except FileNotFoundError:
                pass

    def save_to_cache(self):
        self.wipe_old_files()
        self.savetxt(self.cache_path + 'coords.txt', self.coords)
        ostr = [f'{ele_tag} ' + ' '.join([str(x) for x in self.ele2node_tags[ele_tag]]) + '\n' for ele_tag in self.ele2node_tags]
        open(self.cache_path + 'ele2node_tags.txt', 'w').writelines(ostr)

        for i, fname in enumerate(self.meta_files):
            vals = getattr(self, fname)
            if vals is not None:
                self.savetxt(self.cache_path + f'{fname}.txt', vals, fmt=self.meta_fmt[i])
        if self.dynamic:
            if not self.used_r_starter:
                self.savetxt(self.cache_path + 'x_disp.txt', self.x_disp)
                self.savetxt(self.cache_path + 'y_disp.txt', self.y_disp)
                self.savetxt(self.cache_path + 'timer.txt', self.time)
            elif self.pseudo_dt:
                from numpy import arange
                x_disp = self.loadtxt(f'{self.cache_path}x_disp.txt', ndmin=2)
                self.time = arange(len(x_disp[:, 0])) * self.pseudo_dt
                self.savetxt(self.cache_path + 'timer.txt', self.time)

    def load_from_cache(self):
        self.coords = self.loadtxt(self.cache_path + 'coords.txt')
        self.ele2node_tags = {}
        lines = open(self.cache_path + 'ele2node_tags.txt').read().splitlines()
        for line in lines:
            parts = [int(x) for x in line.split()]
            self.ele2node_tags[parts[0]] = parts[1:]
        for fname in self.meta_files:
            try:
                data = self.loadtxt(self.cache_path + f'{fname}.txt')
                if len(data) == 0:
                    data = None
                setattr(self, fname, data)
            except OSError:
                pass

        if self.dynamic:
            self.x_disp = self.loadtxt(f'{self.cache_path}x_disp.txt')
            self.y_disp = self.loadtxt(f'{self.cache_path}y_disp.txt')
            self.time = self.loadtxt(f'{self.cache_path}timer.txt', ndmin=2)[:, 0]

    @property
    def dt(self):
        if self._dt is None:
            if self.time is not None:
                self._dt = (self.time[-1] - self.time[0]) / (len(self.time) - 1)
        return self._dt

    @dt.setter
    def dt(self, dt):
        self._dt = dt

    # def rezero_node_tags(self, osi):
    #     from numpy import array, arange, searchsorted, where
    #     node_tags = array(o3.get_node_tags(osi))
    #     new_node_tags = arange(1, len(node_tags) + 1)
    #     sidx = node_tags.argsort()
    #     k = node_tags[sidx]
    #     v = new_node_tags[sidx]
    #     for ele_tag in self.ele2node_tags:
    #         curr_tags = self.ele2node_tags[ele_tag]
    #         idx = searchsorted(k, curr_tags)
    #         assert max(idx) < len(k)
    #         mask = k[idx] == curr_tags
    #         self.ele2node_tags[ele_tag] = where(mask, v[idx], len(k))
