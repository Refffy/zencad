# zencad
CAD system for righteous zen programmers

What is it?
-----------
ZenCad - it's a system for use oce geometry core in openscad's script style.
So, it's  openscad idea, python language and opencascade power in one.  

Install
-------
sudo apt install qt5-default  
sudo apt install liboce-*  
sudo apt install python3-pip  
python3 -m pip install zencad  

HelloWorld
----------
```python
#!/usr/bin/env python3.6
#coding: utf-8

import zencad.solid as solid
from zencad.widget import *

m = solid.box(10,10,10) + solid.sphere(5).translate(5,5,10)

display(m)
show()
```

![/docs/result.jpeg](/docs/result.jpeg)
![/docs/fullscreen.png](/docs/fullscreen.png)
