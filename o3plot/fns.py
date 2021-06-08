import numpy as np
from .models import Results2D


def merge_o3res(o3rs, w_cols=1):

    o3res = Results2D(dynamic=True)
    o3res.x_disp = np.concatenate([o3r.x_disp.T for o3r in o3rs]).T
    o3res.y_disp = np.concatenate([o3r.y_disp.T for o3r in o3rs]).T
    o3res.selected_node_tags = np.concatenate([o3r.selected_node_tags for o3r in o3rs])
    o3res.coords = np.concatenate([o3r.coords for o3r in o3rs])
    o3res.dt = o3rs[0].dt
    o3res.ele2node_tags = {}
    for o3r in o3rs:
        o3res.ele2node_tags.update(o3r.ele2node_tags)

    if w_cols:
        o3res.ele_c = np.concatenate([i * np.ones(len(o3rs[i].ele2node_tags)) for i in range(len(o3rs))])
        assert len(o3res.ele_c) == len(o3res.ele2node_tags), (len(o3res.ele_c), len(o3res.ele2node_tags))
    return o3res


def reorder_node_tags_in_anticlockwise_direction(o3res, node_tags):
    x_coords = np.array(o3res.coords)[:, 0]
    y_coords = np.array(o3res.coords)[:, 1]
    node_tags = np.array(node_tags, dtype=int)
    x = x_coords[node_tags - 1]
    y = y_coords[node_tags - 1]
    xc = np.mean(x)
    yc = np.mean(y)
    angle = np.arctan2((y - yc), (x - xc))
    inds = np.argsort(angle)
    return np.array(node_tags)[inds[::-1]]


def renumber_nodes_and_eles(o3res):  # if selected nodes used
    empty_eles = []
    ele_node_strs = []
    eles_selected = []
    for ele in o3res.ele2node_tags:
        new_tags = []
        for tag in o3res.ele2node_tags[ele]:
            try:
                new_tags.append(np.where(tag == o3res.selected_node_tags)[0][0] + 1)
            except IndexError:
                continue
        o3res.ele2node_tags[ele] = reorder_node_tags_in_anticlockwise_direction(o3res, new_tags)
        # remove if empty
        if not len(new_tags):
            empty_eles.append(ele)
            eles_selected.append(0)
            continue
        else:
            eles_selected.append(1)
        # remove if already in
        ele_node_str = ' '.join(np.array(o3res.ele2node_tags[ele], dtype=str))
        if ele_node_str not in ele_node_strs:
            ele_node_strs.append(ele_node_str)
        else:
            empty_eles.append(ele)
    o3res.selected_node_tags = None
    for ele in empty_eles:
        del o3res.ele2node_tags[ele]  # TODO: remove eles from mat2eles
    new_ele2node_tags = {}
    i = 0
    for ele in o3res.ele2node_tags:
        new_ele2node_tags[i] = o3res.ele2node_tags[ele]
        i += 1
    o3res.ele2node_tags = new_ele2node_tags
    if o3res.ele_c is not None:
        o3res.ele_c = o3res.ele_c[np.array(eles_selected)]


