#!/usr/bin/env python3
# coding: utf-8

import evalcache
from zencad import *


@lazy
def instrument_metric_nut(drad, step, h):
    H = step * math.tan(deg(60))

    pseg = polysegment(
        points(
            [
                (drad + H / 2, 0, 0),
                (drad - H / 4, 0, -(3 / 8 * step)),
                (drad - H / 4, 0, -(5 / 8 * step)),
                (drad + H / 2, 0, -step),
            ]
        ),
        closed=True,
    )

    path = helix(r=drad, h=h, step=step)
    base = pipe_shell(spine=path, profiles=[pseg], frenet=True)
    return base


@lazy
def metric_nut(d, step, h):
    H = step * math.tan(deg(60))
    drad = d / 2 - 3 / 8 * H
    cil = cylinder(r=d / 2, h=h)
    instr = instrument_metric_nut(drad=drad, step=step, h=h + step)
    ret = cil - instr

    return ret


nut = metric_nut(8, 1.25, 50)

nut = (
    nut.up(15.3)
    + cylinder(r=8 / 2, h=10).up(5.3)
    + linear_extrude(ngon(r=7.1, n=6), (0, 0, 5.3))
)

fontpath = os.path.join(zencad.moduledir, "examples/fonts/mandarinc.ttf")
m = textshape("ZenCad", fontpath, 20)

w = 64.68
h = 13.5
m = m.extrude(7) + box(w, h, 1.5)

base = rectangle(w, h, wire=True)
base2 = rectangle(w + 5 * 2, h + 5 * 2, wire=True).back(5).left(5).down(10)

trans = up(10) * forw(5) * right(5)
base = loft([base, base2])
base = base.transform(trans)

nut1 = nut.rotateY(deg(90)).back(5).right((w + 5 * 2 - 65.3) / 2).up(11)
nut2 = nut.rotateX(deg(90)).right(w / 2 + 5).forw(30).up(11)

# nut = nut1
m = m.transform(trans)
base = base + nut1.forw(5 + h / 2 + 5)
m3 = m.forw(h * 1.5)
m = m - base
m2 = m.rotateX(deg(180)).up(20)

try:
    scn = zencad.Scene()
except:
    print("Display missing?")
    sys.exit(0)

view = scn.viewer.create_view()
view.set_triedron(False)
#view.set_background(pyservoce.color(0,0,0.6))
scn.viewer.set_triedron_axes(False)

scn.add(base.unlazy())

alpha = 0.3
scn.add(m.unlazy(), Color(0.6, 1, 1,alpha))
scn.add(m2.unlazy(), Color(1, 0.6, 1,0))
scn.add(m3.unlazy(), Color(1, 1, 1,0))

show(scn, view=view)
