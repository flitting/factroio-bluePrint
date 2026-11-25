import json
from generate_clockwise import make,H
cases=[]
for rad,lane,span,ext,half in [(35,17,61,8,32),(35,17,61,12,32),(35,17,61,16,32),(35,17,77,16,32),(43,17,61,8,32),(43,17,61,16,32),(59,17,61,16,32),(75,17,77,16,48)]:cases.append(make(rad,lane,span,private=True,exit_extension=ext,bridge_half=half))
cases.append(make(75,17,61,False,private=True))
(H/'compact-cases.json').write_text(json.dumps(cases));print([c['id'] for c in cases])
