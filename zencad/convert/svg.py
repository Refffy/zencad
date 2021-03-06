#!/usr/bin/env python3

try:
	import svgwrite
except:
	pass

import evalcache
import re
import pyservoce
import math

import xml.etree.ElementTree as ET
import zencad.util

def color_convert(zclr):
	r,g,b,a = zclr.r, zclr.g, zclr.b, zclr.a
	r,g,b,a = ( x * 100 for x in (r,g,b,a))
	return svgwrite.rgb(r,g,b,'%')

def box_size(shape, mapping):
	box = shape.bbox()
	print("BBOX", box)

	if mapping:
		off = (box.xmin, -box.ymax)
	else:
		off = (0,0)

	print("OFF", off)

	return (
		str(box.xmax - box.xmin),
		str(box.ymax - box.ymin),
	), off
	

class SvgWriter:
	def __init__(self, fpath = None, size=None, off=None, **extras):
		if fpath is None:
			self.dwg =  svgwrite.Drawing(size=size, **extras)
		else:
			self.dwg =  svgwrite.Drawing(fpath, size=size, **extras)

		self.off_x = off[0]
		self.off_y = off[1]

	def proj(self, pnt):
		epsillon = 1e-5
		if abs(pnt.z) > epsillon:
			raise Exception("z coord is not zero") 
		return pnt.x - self.off_x, pnt.y - self.off_y

	def begin(self):
		pass

	def save(self):
		self.dwg.save()

	def add_edge_to_path(self):
		pass

	def push_edge(self, edge):
		self.push_wire(edge)

	def push_wire(self, wire):
		if wire.shapetype() == "wire":
			edges = wire.edges()
		else:
			edges = [wire]

		edges = zencad.sort_wire_edges(edges)

		if len(edges) > 1:
			edges = zencad.wire_edges_orientation(edges)
		else:
			edges = [( edges[0], False )]

		edges = list(edges)

		strt = edges[0][0].endpoints()[1 if edges[0][1] else 0]
		strt = self.proj(strt) 

		self.path.push(f"M {strt[0]} {strt[1]}")
		for e in edges:
			rev = e[1]
			e = e[0] 

			s, f = e.endpoints()
			s, f = self.proj(s), self.proj(f)

			if rev:
				s, f = f, s

			if e.curvetype() == "line":
				self.path.push(f"L {f[0]} {f[1]}")

			elif e.curvetype() == "circle":
				angle = e.range()[1] - e.range()[0]
				c,r,x,y = e.circle_parameters()
				sweep = 1 if (x.cross(y)).z > 0 else 0

				c = self.proj(c)
				
				if (abs(angle - math.pi * 2) < 1e-5):
					d = (f[0] - c[0], f[1] - c[1])
					self.path.push(f"A {r} {r} {0} {0} {sweep} {c[0] - d[0]} {c[1] - d[1]}")
					self.path.push(f"A {r} {r} {0} {0} {sweep} {f[0]} {f[1]}")

				else:
					large_arc = 1 if angle > math.pi else 0
					self.path.push(f"A {r} {r} {0} {large_arc} {sweep} {f[0]} {f[1]}")

			else: 
				raise Exception(f"svg:wire : curvetype is not supported: {e.curvetype()} ")

		print(self.path.tostring())

#		closed=True
#		if closed:
#			self.path.push("Z")

	def push_face(self, face):
		face = zencad.fix_face(face)
		wires = zencad.sort_wires_by_face_area(face.wires())
		for w in wires:
			self.push_wire(w)


	def push_shape(self, shp, color):
		shp = zencad.unify(shp)

		shp = zencad.util.restore_shapetype(shp)
		shp = shp.mirrorX()

		#scale_translate = "scale(1 -1)"

		if shp.shapetype() == "face":
			fill_opacity = 1
			self.path = self.dwg.path(stroke="", fill=color, fill_opacity=1)
			self.push_face(shp)

		elif shp.shapetype() == "edge":
			self.path = self.dwg.path(stroke=color, fill="", fill_opacity=0)
			self.push_edge(shp)

		elif shp.shapetype() == "wire":
			self.path = self.dwg.path(stroke=color, fill="", fill_opacity=0)
			self.push_wire(shp)

		else:
			raise Exception(f"shapetype is not supported: {shp.shapetype()} ")


		self.dwg.add(self.path)



class SvgReader:
	def __init__(self):
		pass

	def read_path_final_wb(self):
		if self.wb is not None:
			print("make_wire")
			self.wires.append(self.wb.doit())
			self.wb = None

	def read_path_M(self):
		self.read_path_final_wb()

		self.wb = zencad.wire_builder(start=(
			float(next(self.iter)),
			float(next(self.iter)))
		)

	def read_path_A(self):
		rx=float(next(self.iter))
		ry=float(next(self.iter)) 
		x_axis_rotation=float(next(self.iter))
		large_arc_flag=float(next(self.iter)) >0.5
		sweep_flag=float(next(self.iter)) >0.5
		x=float(next(self.iter)) 
		y=float(next(self.iter))

		zencad.disp(self.wb.current)
		zencad.disp(zencad.point3(x,y))

		if abs(rx-ry) < 1e-5:
			self.wb.plane_circle_arc(rx, zencad.util.deg2rad(x_axis_rotation), large_arc_flag, sweep_flag, x, y)

		else:
			self.wb.plane_eliptic_arc(rx, ry, zencad.util.deg2rad(x_axis_rotation), large_arc_flag, sweep_flag, x, y)

	def read_path_Z(self):
		self.wb.close()

	def read_path_L(self):
		x=float(next(self.iter)) 
		y=float(next(self.iter))

		self.wb.l(x,y)

	def read_path(self, el):
		d = el["d"]

		fill_opacity = None
		fill = None

		if "fill" in el: fill = el["fill"]
		if "fill_opacity" in el: fill_opacity = el["fill_opacity"]

		tokens = d.split()
		self.wb = None
		self.wires = []
		self.iter = iter(tokens)

		while 1:
			try:
				cmd = next(self.iter)
			except:
				self.read_path_final_wb()
				break

			if cmd == "M": self.read_path_M()
			elif cmd == "A": self.read_path_A()
			elif cmd == "L": self.read_path_L()
			elif cmd == "Z": self.read_path_Z()
			else:
				raise Exception("svgreader:path:undefined_command", cmd)

		if fill is not None:
			#zencad.disp(self.wires[0])
			#zencad.show()

			return zencad.make_face(self.wires)

		else:
			return zencad.union(self.wires)


	def read_string(self, svgstring):
		self.root = ET.fromstring(svgstring)
		self.shapes = []

		for a in self.root:
			shp =None
			if a.tag[-4:] == "path":
				shp = self.read_path(a.attrib)
				

			if shp is not None:
				if "transform" in a.attrib:
					s = a.attrib["transform"]
					f = re.findall(r"\w* *\(.*\)", s)

					trans = zencad.nulltrans()

					for f in f:
						sf = f
						f = re.search(r"\(.*\)", s).group(0)
						f = f[1:-1]

						if "," in f:
							vals = f.split(",")
						else:
							vals = f.split(" ")

						if sf.startswith("scale"):
							x = float(vals[0])
							y = float(vals[1])

							if abs(abs(x) - 1) < 1e-5 and abs(abs(y) - 1) < 1e-5:
								if abs(x + 1) < 1e-5 and abs(y + 1) < 1e-5:
									trans = trans * pyservoce.mirrorO()

								elif abs(x + 1) < 1e-5:
									trans = trans * pyservoce.mirrorY()

								elif abs(y + 1) < 1e-5:
									trans = trans * pyservoce.mirrorX()
								else:
									raise Exception("wrong mirror")
							else:
								trans = trans * pyservoce.scaleXYZ(x,y,1)
						else:
							raise Exception("unresolved trans", sf)


					shp = trans(shp)


				shp=shp.mirrorX() # svg coord system is reversed by Y	
				self.shapes.append(shp)



		return self.shapes



def shape_to_svg(fpath, shape, color, mapping):
	shape = evalcache.unlazy_if_need(shape)
	color = color_convert(color)
	size, off = box_size(shape, mapping)
	writer = SvgWriter(fpath=fpath, off=off, size=size)

	writer.begin()
	writer.push_shape(shape, color=color)

	writer.save()


def shape_to_svg_string(shape, color, mapping):
	shape = evalcache.unlazy_if_need(shape)
	color = color_convert(color)
	size, off = box_size(shape,mapping)
	writer = SvgWriter(size=size, off=off)

	writer.begin()
	writer.push_shape(shape, color=color)

	return writer.dwg.tostring()



def svg_to_shape(path):
	reader = SvgReader()
	return reader.read_string(open(path, "r").read())



if __name__ == "__main__":
	import zencad
	import zencad.gutil

	zencad.lazy.fastdo = True

	shp = \
	(
		zencad.rectangle(10,20) 
		+ zencad.rectangle(10,20,center=True)
		+ zencad.circle(r=10)
		#- zencad.rectangle(2)
		-zencad.circle(5)
	)

	#shp = zencad.rectangle(10,20, wire=True)
	#shp = zencad.rectangle(10,20,center=True) - zencad.rectangle(5,10,center=True)
	#shp = zencad.rectangle(10,20,center=True) - zencad.circle(3)

	#shp=zencad.circle(r=10, wire=True, angle=zencad.deg(-270)).move(10,10)
	#print("EP", shp.endpoints())

	clr = zencad.color(0.5,0,0.5)

	mapping = False

	shape_to_svg("test.svg", shp, color=clr, mapping=mapping)

	m = svg_to_shape("test.svg")
	zencad.hl(shp.up(4))
	zencad.disp(m)
	zencad.show()