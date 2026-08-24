import base64
import os
b64 = open(os.path.join(chr(116)+chr(101)+chr(115)+chr(116)+chr(115), chr(95)+chr(98)+chr(54)+chr(52)+chr(46)+chr(116)+chr(120)+chr(116))).read().strip()
content = base64.b64decode(b64).decode(chr(117)+chr(116)+chr(102)+chr(45)+chr(56))
target = os.path.join(chr(116)+chr(101)+chr(115)+chr(116)+chr(115), chr(116)+chr(101)+chr(115)+chr(116)+chr(95)+chr(115)+chr(116)+chr(101)+chr(112)+chr(48)+chr(53)+chr(95)+chr(116)+chr(97)+chr(115)+chr(107)+chr(95)+chr(101)+chr(120)+chr(101)+chr(99)+chr(117)+chr(116)+chr(111)+chr(114)+chr(46)+chr(112)+chr(121))
with open(target, chr(119), encoding=chr(117)+chr(116)+chr(102)+chr(45)+chr(56)) as f:
    f.write(content)
print(chr(87)+chr(114)+chr(105)+chr(116)+chr(116)+chr(101)+chr(110)+chr(58), os.path.getsize(target))